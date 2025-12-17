"""
AWS tool for executing Athena queries using Bedrock for query generation.
"""
import json
import os
import urllib.parse
from typing import Dict
from strands import tool
import logging
import queryExecutor as queryExecutor, bedrockAPI as bedrockAPI

# Constants
# HTTP Response Headers
JSON_CONTENT_TYPE = {"Content-Type": "application/json"}

"""Generate prompt for case-related queries."""
def get_case_prompt(user_query: str) -> str:
    return (
    "You are an SQL expert familiar with AWS Athena. "
    "Using the database 'optira_database', which contains table 'case_metadata' (fields: account_id, caseId, timeCreated, severityCode, status, subject, "
    "categoryCode, serviceCode), generate an Athena SQL query matching the following natural language request: '"
    f"{user_query}'. Important rules: "
    "(1) Always use the SQL LIKE operator (not '=') with wildcards ('%') when filtering the field 'serviceCode'. "
    "(2) Use plain string literals for date conditions (e.g., 'YYYY-MM-DD') rather than TIMESTAMP literals. "
    "(3) Return only the SQL query without commentary. "
    "(4) When filtering for specific dates, use SUBSTRING(timeCreated, 1, 10) = 'YYYY-MM-DD' format. "
    "(5) Severity is either of the following: high, low, normal, urgent, critical. "
    "(6) Always use LOWER() function when matching serviceCode to ensure case-insensitive comparison. "
    "(7) If there is mention of UTC then (otherwise ignore this rule): you can use from_iso8601_timestamp. "
    "Keep it simple, dont use timezone function. DONT USE ANY MARKDOWN)"
)

"""Create a standardized error response."""
def create_error_response(status_code: int, error_message: str) -> Dict:

    return {
    "statusCode": status_code,
    "headers": JSON_CONTENT_TYPE,
    "body": json.dumps({"error": error_message})
}

@tool
def case_aggregation(query: str) -> Dict:
    user_query = query 
    
    if not user_query:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "No query provided in the event"})
        }

    user_query = urllib.parse.unquote(user_query)
    
    # Select prompt based on query type
    prompt = get_case_prompt(user_query)
  
    sql_query = bedrockAPI.invoke_bedrock_api(prompt)
   
    if not sql_query:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to generate SQL query from Bedrock"})
        }

    print("Generated SQL Query:", sql_query)
    athena_results = queryExecutor.execute_athena_query(sql_query)
    #print("Final Athena Query Results:", json.dumps(athena_results))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "generated_query": sql_query,
            "athena_results": athena_results
        })
    }   