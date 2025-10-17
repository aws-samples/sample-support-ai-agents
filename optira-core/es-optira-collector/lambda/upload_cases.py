import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging
import boto3
from botocore.exceptions import ClientError

from utils import convert_time_to_month_year

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.Session()

def save_to_s3(cases_by_account, bucket_name):
    region = session.region_name
    s3 = session.client("s3", region_name=region)

    print(f"The Support cases are being uploaded to S3 bucket {bucket_name}...")
    for account_id, cases in cases_by_account.items():
        for case in cases:
            # Extracting case ID for filename
            case_id = case["case"]["displayId"]

            # Extracting creation time for partitioning in S3
            time_created = case["case"]["timeCreated"]
            # Convert the time_created in the format "2024-07-23T15:49:29.995Z" to "2024/07"
            creation_date = convert_time_to_month_year(iso_datetime=time_created)

            # Serialize case data to JSON with UTF-8 encoding
            case_json = json.dumps(case, ensure_ascii=False).encode("utf-8")

            file_key = f"support-cases/{account_id}/{creation_date}/{case_id}.json"
            s3.put_object(Bucket=bucket_name, Key=file_key, Body=case_json)

            print(f"Uploaded {file_key}")
    print("Support cases upload done!")


def get_support_cases(credentials):
    support_client = session.client(
        "support",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    cases = []
    paginator = support_client.get_paginator("describe_cases")
    for page in paginator.paginate(includeResolvedCases=True):
        cases.extend(page["cases"])
    return cases


def describe_cases(after_time, include_resolved):
    """
    Describe support cases over a period of time, optionally filtering
    by status.

    :param after_time: The start time to include for cases.
    :param before_time: The end time to include for cases.
    :param include_resolved: True to include resolved cases in the results,
        otherwise results are open cases.
    :return: The final status of the case.
    """
    cases = []
    try:
        support_client = session.client("support")
        paginator = support_client.get_paginator("describe_cases")
        for page in paginator.paginate(
            afterTime=after_time,
            includeResolvedCases=include_resolved,
            includeCommunications=True,
            language="en",
        ):
            cases += page["cases"]
    except ClientError as err:
        if err.response["Error"]["Code"] == "SubscriptionRequiredException":
            logger.info(
                "You must have a Business, Enterprise On-Ramp, or Enterprise Support "
                "plan to use the AWS Support API. \n\tPlease upgrade your subscription to run these "
                "examples."
            )
        else:
            logger.error(
                "Couldn't describe cases. Error Code: %s, Error Message: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
    return cases


def list_all_cases(days):
    include_resolved = True
    start_date = datetime.now(timezone.utc).date() - timedelta(days)
    start_time = str(start_date)
    all_cases = describe_cases(start_time, include_resolved)

    return all_cases


def create_support_case_context(case, account_id):
    display_id = case["displayId"]  # Use the correct key for the case ID
    time_created = case["timeCreated"]
    case_status = case["status"]
    service_code = case["serviceCode"]
    severity_code = case["severityCode"]

    # Create the context for search
    support_case_context = f"This is an AWS support case ID {display_id} in account ID {account_id}. The case was opened on {time_created}; It is a {case_status} case related to the {service_code} service with {severity_code} severity. The details are on the body fields of the JSON."

    return support_case_context


def get_organization_accounts():
    """Get all accounts in the organization"""
    org_client = session.client('organizations')
    accounts = []
    paginator = org_client.get_paginator('list_accounts')
    for page in paginator.paginate():
        accounts.extend(page['Accounts'])
    return [acc['Id'] for acc in accounts if acc['Status'] == 'ACTIVE']

def assume_role_in_account(account_id, role_name='OrganizationAccountAccessRole'):
    """Assume role in target account"""
    sts_client = session.client('sts')
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=f'SupportCaseCollection-{account_id}'
    )
    return response['Credentials']

def upload_all_cases_to_s3(bucket_name, past_no_of_days, account_id):
    cases_by_account = defaultdict(list)
    
    try:
        # Get all organization accounts
        org_accounts = get_organization_accounts()
        print(f"Found {len(org_accounts)} accounts in organization")
        
        for target_account_id in org_accounts:
            try:
                if target_account_id == account_id:
                    # Current account - use existing session
                    cases = list_all_cases(past_no_of_days)
                else:
                    # Cross-account - assume role
                    credentials = assume_role_in_account(target_account_id)
                    cases = get_support_cases(credentials)
                
                for case in cases:
                    case_dict = {
                        "account_id": target_account_id,
                        "case": case,
                        "support_case_context": create_support_case_context(
                            case, target_account_id
                        )
                    }
                    cases_by_account[target_account_id].append(case_dict)
                    
            except Exception as e:
                print(f"Failed to get cases from account {target_account_id}: {e}")
                continue
                
    except Exception as e:
        print(f"Failed to get organization accounts, falling back to single account: {e}")
        # Fallback to single account
        cases = list_all_cases(past_no_of_days)
        for case in cases:
            case_dict = {
                "account_id": account_id,
                "case": case,
                "support_case_context": create_support_case_context(
                    case, account_id
                )
            }
            cases_by_account[account_id].append(case_dict)

    save_to_s3(cases_by_account, bucket_name)

def upload_case_to_s3(bucket_name, account_id, case_id):
    """
    Upload a single support case to S3
    :param bucket_name: The S3 bucket name
    :param account_id: AWS account ID
    :param case_id: Support case display ID
    """

    support_client = session.client("support")

    # Get single case with displayId filter
    case_response = support_client.describe_cases(
        displayId=case_id,
        includeCommunications=True,
        language="en"
    )

    if not case_response['cases']:
        raise ValueError(f"No case found with display ID {case_id}")

    case = case_response['cases'][0]

    # Create the case dictionary
    cases_by_account = defaultdict(list)
    case_dict = {
        "account_id": account_id,
        "case": case,
        "support_case_context": create_support_case_context(
            case, account_id
        )
    }
    cases_by_account[account_id].append(case_dict)

    # Save to S3
    save_to_s3(cases_by_account, bucket_name)
    