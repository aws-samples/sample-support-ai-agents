import json
import os
import time
import urllib.parse
from typing import Any, Dict, Optional
from strands import Agent, tool
import boto3
from botocore.exceptions import ClientError
import logging

# Constants
ATHENA_DATABASE = os.environ['ATHENA_DATABASE']
ATHENA_OUTPUT_S3 = os.environ['ATHENA_OUTPUT_S3']
MAX_QUERY_EXECUTION_TIME = 300  # 5 minutes timeout
POLL_INTERVAL = 1  # Initial polling interval in seconds
session = boto3.Session()
REGION_NAME = session.region_name 

def execute_athena_query(query: str) -> Dict:
    """Execute Athena query with exponential backoff polling."""
    athena = boto3.client('athena', region_name=REGION_NAME)
    try:
        response = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': ATHENA_DATABASE},
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT_S3}
        )
        query_execution_id = response['QueryExecutionId']
        
        start_time = time.time()
        poll_interval = POLL_INTERVAL

        while True:
            query_status = athena.get_query_execution(QueryExecutionId=query_execution_id)
            status = query_status['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
                
            if time.time() - start_time > MAX_QUERY_EXECUTION_TIME:
                athena.stop_query_execution(QueryExecutionId=query_execution_id)
                return {"error": f"Query execution timed out after {MAX_QUERY_EXECUTION_TIME} seconds"}
                
            time.sleep(min(poll_interval, 5))
            poll_interval *= 2

        if status == 'SUCCEEDED':
            return athena.get_query_results(QueryExecutionId=query_execution_id)
        
        if status == 'FAILED':
            state_change_reason = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
            return {"error": f"Query failed: {state_change_reason}"}
        
        return {"error": "Query was cancelled"}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return {"error": f"Athena error: {error_code} - {error_message}"}
    except Exception as e:
        return {"error": str(e)}