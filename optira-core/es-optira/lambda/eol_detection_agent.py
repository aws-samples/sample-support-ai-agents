from strands import Agent, tool
from strands_tools import use_aws
from typing import Dict, List, Optional
from strands.models.bedrock import BedrockModel
import os, boto3
import logging
from trustedAdvisorTool import trusted_advisor_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ["BYPASS_TOOL_CONSENT"] = "true"
session = boto3.Session()
REGION_NAME = session.region_name 
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID'] 

bedrock_model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=REGION_NAME, temperature=0.1)


@tool
def check_aws_service_deprecation(service_name: str) -> Dict:
    """
    Check for deprecated or soon-to-be deprecated AWS service runtimes.
    
    Args:
        service_name: The AWS service name to check (e.g., 'lambda', 'rds', 'eks')
    
    Returns:
        Dict containing service deprecation information including service name, ARN, and runtime versions
    """
    logger.info(f"Checking deprecation status for AWS service: {service_name}")
    
    try:
        # Use the AWS tool to get service information  
        query = f"List all {service_name} functions/resources with their runtime versions. Identify deprecated or soon-to-be deprecated runtime versions. Include ARNs where available."
        
        # Since use_aws is a tool, we need to call it through the agent framework
        # For now, return a structured response indicating we need to use it as an agent tool
        return {
            "service_name": service_name,
            "service_arn": None,
            "runtime_versions": [],
            "deprecated_versions": [],
            "soon_deprecated_versions": [],
            "status": "requires_agent_tool_call",
            "message": f"Service {service_name} deprecation check requires use_aws tool call through agent"
        }
        

        
    except Exception as e:
        logger.error(f"Error checking deprecation for service {service_name}: {str(e)}")
        return {
            "service_name": service_name,
            "service_arn": None,
            "runtime_versions": [],
            "deprecated_versions": [],
            "soon_deprecated_versions": [],
            "status": "error",
            "error": str(e)
        }

def create_eol_detection_agent():
    """
    Enhanced EOL Detection Agent:
    1. Identifies deprecated and soon-to-be deprecated AWS service runtimes
    2. Provides comprehensive assessment with service ARNs and version details
    3. Integrates with Trusted Advisor for additional insights
    """
   
    SYSTEM_PROMPT = """
    You are an AWS End-of-Life (EOL) Detection Specialist focused on identifying deprecated 
    and soon-to-be deprecated AWS service runtimes across customer workloads. Your mission 
    is to proactively identify services that require attention to maintain security, 
    compliance, and operational excellence.

    Key Responsibilities:
    - Identify deprecated AWS service runtime versions
    - Flag services approaching end-of-life dates
    - Provide service ARNs and detailed version information
    - Recommend migration paths and timelines
    - Assess business impact and priority levels

    You have access to specialized tools for checking AWS service deprecation status.
    Always provide actionable recommendations with clear timelines and migration strategies.
    
    When checking services, be thorough and systematic in your analysis.
    """
    
    eol_agent = Agent(
        system_prompt=SYSTEM_PROMPT, 
        model=bedrock_model,
        tools=[trusted_advisor_recommendations, use_aws, check_aws_service_deprecation]
    )
    return eol_agent

@tool
def eol_detection(query: str = "") -> str:
    """
    Check for deprecated or soon-to-be deprecated AWS service runtimes and end-of-life versions.
    Use this tool when users ask about EOL, end-of-life, deprecated versions, or runtime deprecation.
    
    Args:
        query: The user's query about EOL/deprecation
    
    Returns:
        String containing EOL analysis results
    """
    logger.info(f"Starting EOL Detection for query: {query}")
    
    try:
        eol_agent = create_eol_detection_agent()
        response = eol_agent(f"Analyze AWS services for EOL/deprecation: {query}")
        logger.info("EOL detection analysis completed successfully")
        return f"EOL Analysis Results:\n{response}"
        
    except Exception as e:
        logger.error(f"Error during EOL detection: {str(e)}")
        return f"EOL Detection Error: {str(e)}"