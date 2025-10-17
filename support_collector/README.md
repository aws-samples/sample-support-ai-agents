# Optira - AWS Support Collection Deployment

This repository contains scripts and resources to automate the deployment of AWS Lambda functions in designated AWS accounts. The deployed resources collect and upload AWS Support data (AWS Support Cases, AWS Health Events, and Trusted Advisor Checks) to an Amazon S3 bucket in the Data Collection Central account. The collected data can be utilized with Amazon Bedrock to analyze and gain insights into your support cases.

## Prerequisites

- An AWS account for resources with the necessary permissions to create and manage resources (IAM roles, Lambda functions, CloudFormation stacks, etc.).
- A Support plan such as Business, Enterprise On-Ramp, or Enterprise Support to access the AWS Support API.
- You can utilize AWS CloudShell, as it comes pre-installed with the required libraries and tools. Alternatively, you can use a local machine with the AWS CLI installed and configured with valid credentials.
- An Amazon S3 bucket for data collection in a central AWS account
- An Amazon S3 bucket for resources for infrastructure deployment in the given AWS account

## Deployment dependencies

If you use your local machine to deploy the solution, the following dependencies will be required for deploying the Lambda:

```text
boto3==1.34.146
```

## Lambda Function Configuration

The default Lambda function configuration is set to:

- Memory: 128MB
- Ephemeral storage: 512MB

However, it is recommended to update these settings based on the volume of data you expect to collect. You can modify the Lambda function configuration in the `member_account_resources.yaml`

## Directory Structure

```bash
├── deploy_collector.sh
├── deploy_infrastructure.py
├── deploy_stackset.py
├── individual-account-deployments
│   ├── deploy_collector_lambda_member.sh
│   ├── deploy_lambda_function.py
│   └── member_account_resources.yaml
├── member_account_resources.yaml
└── support-collector-lambda
    ├── health_client.py
    ├── lambda_function.py
    ├── region_lookup.py
    ├── ta_checks_info.json
    ├── upload_cases.py
    ├── upload_health.py
    └── upload_ta.py
```

## Deployment Options

You can setup data pipeline by deploying resorces in each account: 
1. It creates Lambda package (that invokes AWS Support APIs on Case updates) 
2. Uploads the package to Resource S3 bucket
3. Invokes a CloudFormation to deploy the resources that includes tha lambda package and EventBridge. 
3. Once set up, the data pipeline enables synchronization mechanisms with Real-time Case Updates: Processes AWS Support cases through event-based triggers (CreateCase, AddCommunicationToCase, ResolveCase, ReopenCase).


### Deployment in Each Account via CloudFormation

Use this option if you do not wish to use AWS Organizations and want to target a few accounts. Note: You can leverage AWS CloudFormation StackSets to deploy across multiple linked or member accounts with a single operation.

#### Deployment Steps for a single account

1. In the member account, launch AWS CloudShell or open a terminal window on your local machine.
2. Get the code in your working directory 
3. Navigate to the `individual-account-deployments` directory:

    ```bash
    cd support_collector/individual-account-deployments
    ```

4. Run the `deploy_collector_lambda_member.sh` script:

    ```bash
    chmod +x deploy_collector_lambda_member.sh
    ./deploy_collector_lambda_member.sh
    ```

5. The script will prompt you to provide the input bucket name of your central Data Collection AWS account.
6. The script will perform the following tasks:
   - Create an IAM role `SupportInsightsLambdaRole-9c8794ee-f9e8` with the necessary permissions to access the AWS Support services.
   - Deploy the Lambda function with the created IAM role, using CloudFormation.
   - Set up an Amazon EventBridge to trigger the AWS Lambda function on case update events.
   - Run a one time sync to fetch historical support data and load to S3 data bucket.

#### Bucket Policy

As you store the data in a central bucket, you need to update the bucket policy of the S3 bucket to grant access to the specific AWS accounts. Replace the placeholders in the following bucket policy with your specific values:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<member_account_id>:role/SupportInsightsLambdaRole-9c8794ee-f9e8"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::<your-bucket-name>/*"
    }
  ]
}
```

Replace `<member_account_id>` with the actual AWS account ID of the AWS account, and `<your-bucket-name>` with the name of the S3 bucket in the Data Collection Central account. You can add multiple accounts. Please note 'SupportInsightsLambdaRole-9c8794ee-f9e' is going to be the name of the role created in the member accounts to grant permission to Lambda function.

## Data Collection Process

After the successful deployment, an Amazon EventBridge scheduler will trigger the AWS Lambda function on case update events. The Lambda function will collect and store the support data in the specified S3 bucket.

- The initial execution of the Lambda function will collect and store up to 180 days of historical data (support cases, health events, and Trusted Advisor checks). However, you can modify the number of days by updating the `ScheduleExpression` in the `EventBridgeRuleForHistoricalSupportData` resource in the `member_account_resources.yaml` CloudFormation template.
- Subsequent executions will collect and store data with real time updates.
- You have the flexibility to configure the Lambda function to collect one, two, or all three of the support cases, health events, and Trusted Advisor checks by modifying the input parameters in the `EventBridgeRuleForHistoricalSupportData` and `EventBridgeRuleForDailyRun` resources. You can also create separate EventBridge rules for each type of data (cases, health, and Trusted Advisor) if desired.

The user does not need to manually trigger the Lambda function, as the data collection process is automated and managed by the deployed resources.

## Optional - Testing the Lambda Function

You can test the Lambda function by invoking it with a custom payload. The payload should be a JSON object with the following properties:

- `past_no_of_days` (integer): The number of past days for which you want to retrieve support data.
- `bucket_name` (string): The name of the S3 bucket where the support data will be stored.
- `case` (boolean): Whether to include case data or not.
- `health` (boolean): Whether to include health data or not.
- `ta` (boolean): Whether to include Trusted Advisor data or not.

Example payload:

```json
{
  "past_no_of_days": 2,
  "bucket_name": "<DATA-COLLECTION-BUCKET>",
  "case": true,
  "health": false,
  "ta": false
}
```

In this example, the Lambda function will retrieve support data for the past 180 days, will include case data, but exclude health and Trusted Advisor data. The data will be stored in the `<DATA-COLLECTION-BUCKET>` S3 bucket.

To test the Lambda function:

1. Navigate to the AWS Lambda console.
2. Select the Lambda function you want to test.
3. Click the "Test" button.
4. Under "Configure test event", choose "Create new event".
5. Enter an event name (e.g., "TestEvent").
6. Replace the default JSON payload with the desired payload (e.g., the example payload above).
7. Click "Create".
8. Click "Test" to invoke the Lambda function with the provided payload.

The Lambda function will execute, and you can review the output and logs in the "Execution result" section.

Note: Make sure to replace `<DATA-COLLECTION-BUCKET>` with the actual name of your S3 bucket.

## Cleanup

To clean up the deployed resources, follow these steps:


1. Delete the member account CloudFormation stack (for option 2):
   - Navigate to the CloudFormation console in the member account.
   - Select the stack named `SupportInsightsLambdaStack`.
   - Delete the stack.

   Alternatively, you can use the CLI command:

   ```bash
   aws cloudformation delete-stack --stack-name SupportInsightsLambdaStack
   ```

    > **Warning:** Before proceeding with the next step, ensure that no critical data is present in the S3 bucket containing the support data. Deleting the S3 bucket will permanently remove all data stored in it.

2. Empty and delete the S3 bucket containing the support data.

## Disclaimer

The sample code provided in this solution is for educational purposes only. Users should thoroughly test and validate the solution before deploying it in a production environment.
