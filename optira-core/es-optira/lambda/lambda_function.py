import json, os, uuid, boto3, re
from strands import Agent
from caseAggregationTool import case_aggregation
from knowledgeBaseTool import knowledge_insight


def validate_and_sanitize_input(query: str) -> str:
    """
    Validate and sanitize user input to prevent injection attacks.
    
    Parameters:
    - query: Raw user input string
    
    Returns:
    - str: Sanitized query string
    
    Raises:
    - ValueError: If input contains malicious patterns
    """
    if not isinstance(query, str):
        raise ValueError("Query must be a string")
    
    # Length validation
    if len(query) > 2000:
        raise ValueError("Query exceeds maximum length of 2000 characters")
    
    # Remove null bytes and control characters
    query = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', query)
    
    # Check for potential injection patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',               # JavaScript protocol
        r'on\w+\s*=',                # Event handlers
        r'\$\{.*?\}',                # Template literals
        r'eval\s*\(',                # eval function
        r'exec\s*\(',                # exec function
        r'__import__\s*\(',          # Python import
        r'subprocess\.',             # subprocess module
        r'os\.',                     # os module
        r'system\s*\(',              # system calls
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError(f"Query contains potentially malicious content")
    
    # Strip whitespace and return sanitized query
    return query.strip()

def lambda_handler(event, context)-> dict:
    """
    AWS Lambda function handler that processes incoming events and invokes the insight agent.
    
    Parameters:
    - event: The event data passed to the Lambda function (dict)
    - context: Runtime information provided by AWS Lambda
    
    Returns:
    - dict: Response containing the agent's output
    """

    SYSTEM_PROMPT = os.environ['SYSTEM_PROMPT']

    try:
        # Parse JSON body if using api post method, Check if body exists
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No body found in request'})
            }
        
        # Validate JSON structure
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Validate required fields
        if not isinstance(body, dict):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Request body must be a JSON object'})
            }
        
        raw_query = body.get('query', '')
        
        # Validate and sanitize input
        try:
            query = validate_and_sanitize_input(raw_query)
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid input: {str(e)}'})
            }

        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No query provided in the request'})
            }
        
        # Format the query as expected by the agent
        formatted_query = f"""query:{query}?"""
        # create the agent with the requried tools
        agent = Agent(tools=[case_aggregation, knowledge_insight],
                      system_prompt=SYSTEM_PROMPT)
        # Invoke the agent with the query
        result = agent(formatted_query)
        
        # Return the result
        return {
            'statusCode': 200,
            'body': f"result: {result}"
        }
    
    except Exception as e:
        # Handle any exceptions with proper error response
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error occurred'})
        }