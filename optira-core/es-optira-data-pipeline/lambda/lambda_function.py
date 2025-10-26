import json
import boto3
import csv
import os
from io import StringIO
from datetime import datetime
from botocore.exceptions import ClientError

S3_PREFIX = 'support-cases/'

def trigger_kb_ingestion():
    """Trigger knowledge base ingestion for new support case data"""
    try:
        # Get KB ID from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        bedrock_agent = boto3.client('bedrock-agent')
        
        secret_response = secrets_client.get_secret_value(SecretId='optira/knowledge-base-id')
        secret_data = json.loads(secret_response['SecretString'])
        kb_id = secret_data['knowledge_base_id']
        
        # Get data sources for the knowledge base
        data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
        
        if not data_sources['dataSourceSummaries']:
            return {'status': 'error', 'message': 'No data sources found'}
        
        # Start ingestion job for the first data source
        data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']
        
        ingestion_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        job_id = ingestion_response['ingestionJob']['ingestionJobId']
        print(f"Started KB ingestion job: {job_id}")
        
        return {
            'status': 'success', 
            'job_id': job_id,
            'kb_id': kb_id,
            'data_source_id': data_source_id
        }
        
    except Exception as e:
        print(f"KB ingestion trigger failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def process_batch(s3, bucket_name, resolved_records, active_records, files):
    """Process batches of records into separate files for resolved and active cases"""
    timestamp = datetime.now().strftime('%Y%m%d')
    
    # Process resolved cases
    if resolved_records:
        csv_buffer = StringIO()
        fieldnames = ['account_id', 'caseId', 'timeCreated', 'severityCode', 
                    'status', 'subject', 'categoryCode', 'serviceCode']
        
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for record in resolved_records:
            writer.writerow(record)
        
        resolved_key = 'metadata/metadata.csv'
        s3.put_object(
            Bucket=bucket_name,
            Key=resolved_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        files['resolved'] = resolved_key
        print(f"Exported {len(resolved_records)} resolved cases")

    # Process active cases - append to existing CSV
    if active_records:
        active_key = 'metadata/metadata.csv'
        fieldnames = ['account_id', 'caseId', 'timeCreated', 'severityCode', 
                    'status', 'subject', 'categoryCode', 'serviceCode']
        
        # Check if file exists and get existing content
        existing_content = ""
        file_exists = False
        try:
            response = s3.get_object(Bucket=bucket_name, Key=active_key)
            existing_content = response['Body'].read().decode('utf-8')
            file_exists = True
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise
        
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        
        # If file doesn't exist, write header
        if not file_exists:
            writer.writeheader()
        
        # Write new records
        for record in active_records:
            writer.writerow(record)
        
        # Combine existing content with new content
        final_content = existing_content + csv_buffer.getvalue()
        
        s3.put_object(
            Bucket=bucket_name,
            Key=active_key,
            Body=final_content,
            ContentType='text/csv'
        )
        files['active'] = active_key
        print(f"Appended {len(active_records)} active cases")

#  Description: "Lambda function to export historical support cases metadata into resolved and active CSV files"
def lambda_handler(event, context):
    try:
        # Get bucket name from environment variable
        bucket_name = os.environ['S3_BUCKET_NAME']
        if not bucket_name:
            raise ValueError("Bucket name not configured in environment variables")
            
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        # Test bucket access
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            raise Exception(f"Cannot access bucket {bucket_name}: {str(e)}")
                                            
        # Initialize counters and lists
        resolved_records = []
        active_records = []
        files_processed = 0
        output_files = {'resolved': None, 'active': None}
        batch_size = 10000  # Process 10000 records per batch
        
        # List all objects in the cases prefix with pagination
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=S3_PREFIX)
        
        # Process each JSON file
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            response = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                            file_content = response['Body'].read().decode('utf-8')
                            json_data = json.loads(file_content)
                            
                            case_data = json_data['case']
                            record = {
                                'account_id': json_data['account_id'],
                                'caseId': case_data['displayId'],
                                'timeCreated': case_data['timeCreated'],
                                'severityCode': case_data['severityCode'],
                                'status': case_data['status'],
                                'subject': case_data['subject'],
                                'categoryCode': case_data['categoryCode'],
                                'serviceCode': case_data['serviceCode']
                            }

                            # Separate resolved and active cases
                            if case_data['status'].lower() == 'resolved':
                                resolved_records.append(record)
                            else:
                                active_records.append(record)
                                
                            files_processed += 1
                            
                            # Process batch when reaching batch size
                            if len(resolved_records) + len(active_records) >= batch_size:
                                process_batch(s3, bucket_name, resolved_records, active_records, output_files)
                                resolved_records = []  # Clear records after processing
                                active_records = []
                                
                        except Exception as e:
                            print(f"Error processing file {obj['Key']}: {str(e)}")
                            continue
        
        # Process remaining records
        if resolved_records or active_records:
            process_batch(s3, bucket_name, resolved_records, active_records, output_files)
        
        if files_processed == 0:
            return {
                'statusCode': 200,
                'body': f'No files found to process in prefix {S3_PREFIX}'
            }
        
        # Trigger knowledge base ingestion after processing files
        kb_result = trigger_kb_ingestion()
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'CSV files created successfully',
                'resolved_cases_file': output_files['resolved'],
                'active_cases_file': output_files['active'],
                'files_processed': files_processed,
                'resolved_count': len(resolved_records),
                'active_count': len(active_records),
                'kb_ingestion': kb_result
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }