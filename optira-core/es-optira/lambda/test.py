from strands import Agent
from caseAggregationTool import case_aggregation
from knowledgeBaseTool import knowledge_insight

#def lambda_handler(event, context)-> dict:
def testinvoke()-> dict:
    print("hello")
    """
    AWS Lambda function handler that processes incoming events and invokes the insight agent.
    
    Parameters:
    - event: The event data passed to the Lambda function (dict)
    - context: Runtime information provided by AWS Lambda
    
    Returns:
    - dict: Response containing the agent's output
    """


    SYSTEM_PROMPT = "As a specialist, please identify relevant support cases based on the query and gather additional case information from the knowledge base." #os.environ['SYSTEM_PROMPT']
    try:
        query="can you provide Redshift case distribution based on severity? Go through Redshift critical issues and  give me TRAINING recommendations to educate the team."
        # OR Extract query from the event if testing lambda directly
        if not query:
            return 'No query provided in the event'
        # Format the query as expected by the agent
        formatted_query = f"""query:{query}?"""
        # create the agent with the requried tools
        agent = Agent(tools=[case_aggregation, knowledge_insight], system_prompt=SYSTEM_PROMPT)
        # Invoke the agent with the query
        result = agent(formatted_query)
        print(result)
    except Exception as e:
        # Handle any exceptions
        return  str(e)

if __name__ == "__main__":
    result = testinvoke()
    print(result)