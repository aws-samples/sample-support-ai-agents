#!/usr/bin/env python3
import boto3
import argparse
import logging
import json
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def list_knowledge_bases(region):
    """List all knowledge bases in the account"""
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    
    try:
        response = bedrock_agent.list_knowledge_bases()
        
        if not response.get('knowledgeBaseSummaries'):
            logger.info("No knowledge bases found")
            return []
        
        logger.info(f"Found {len(response['knowledgeBaseSummaries'])} knowledge bases:")
        for kb in response['knowledgeBaseSummaries']:
            logger.info(f"  ID: {kb['knowledgeBaseId']}, Name: {kb['name']}, Status: {kb['status']}")
        
        return response['knowledgeBaseSummaries']
    except ClientError as e:
        logger.error(f"Error listing knowledge bases: {e}")
        return []

def get_knowledge_base(kb_id, region):
    """Get details of a specific knowledge base"""
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    
    try:
        response = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
        
        kb = response['knowledgeBase']
        logger.info(f"Knowledge Base Details:")
        logger.info(f"  ID: {kb['knowledgeBaseId']}")
        logger.info(f"  Name: {kb['name']}")
        logger.info(f"  Description: {kb['description']}")
        logger.info(f"  Status: {kb['status']}")
        logger.info(f"  Created: {kb['createdAt']}")
        logger.info(f"  Updated: {kb['updatedAt']}")
        
        return kb
    except ClientError as e:
        logger.error(f"Error getting knowledge base details: {e}")
        return None

def list_data_sources(kb_id, region):
    """List data sources for a knowledge base"""
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    
    try:
        response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
        
        if not response.get('dataSourceSummaries'):
            logger.info(f"No data sources found for knowledge base {kb_id}")
            return []
        
        logger.info(f"Found {len(response['dataSourceSummaries'])} data sources:")
        for ds in response['dataSourceSummaries']:
            logger.info(f"  ID: {ds['dataSourceId']}, Name: {ds['name']}, Status: {ds['status']}")
        
        return response['dataSourceSummaries']
    except ClientError as e:
        logger.error(f"Error listing data sources: {e}")
        return []

def query_knowledge_base(kb_id, query_text, region, num_results=5):
    """Query a knowledge base"""
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
    
    try:
        logger.info(f"Querying knowledge base {kb_id} with: '{query_text}'")
        
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query_text
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results
                }
            }
        )
        
        logger.info(f"Retrieved {len(response['retrievalResults'])} results:")
        
        for i, result in enumerate(response['retrievalResults']):
            logger.info(f"Result {i+1}:")
            logger.info(f"  Content: {result['content']['text'][:200]}...")
            logger.info(f"  Score: {result['score']}")
            if 's3Location' in result['location']:
                logger.info(f"  Location: {result['location']['s3Location']['uri']}")
            logger.info("---")
        
        return response['retrievalResults']
    except ClientError as e:
        logger.error(f"Error querying knowledge base: {e}")
        return None

def upload_supportcase_file(file_path, bucket_name, prefix, region):
    """Upload a support case file to existing S3 bucket"""
    s3 = boto3.client('s3', region_name=region)
    
    try:
        # Verify bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            logger.error(f"S3 bucket {bucket_name} does not exist or you don't have access to it")
            return None
            
        import os
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        file_name = os.path.basename(file_path)
        s3_key = f"{prefix}/{file_name}"
        
        logger.info(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
        
        with open(file_path, 'rb') as file_data:
            s3.upload_fileobj(file_data, bucket_name, s3_key)
        
        logger.info(f"Upload complete")
        return f"s3://{bucket_name}/{s3_key}"
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test Amazon Bedrock Knowledge Base')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--action', type=str, required=True, 
                        choices=['list', 'get', 'datasources', 'query', 'upload'],
                        help='Action to perform')
    parser.add_argument('--kb-id', type=str, help='Knowledge Base ID')
    parser.add_argument('--query-text', type=str, default='What information do you have?', help='Query text')
    parser.add_argument('--file', type=str, help='Path to support case file to upload')
    parser.add_argument('--bucket', type=str, help='Existing S3 bucket name')
    parser.add_argument('--prefix', type=str, default='support-cases', help='S3 prefix')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        list_knowledge_bases(args.region)
    
    elif args.action == 'get':
        if not args.kb_id:
            logger.error("Knowledge Base ID is required for get action")
            return
        get_knowledge_base(args.kb_id, args.region)
    
    elif args.action == 'datasources':
        if not args.kb_id:
            logger.error("Knowledge Base ID is required for datasources action")
            return
        list_data_sources(args.kb_id, args.region)
    
    elif args.action == 'query':
        if not args.kb_id:
            logger.error("Knowledge Base ID is required for query action")
            return
        query_knowledge_base(args.kb_id, args.query_text, args.region)
    
    elif args.action == 'upload':
        if not args.file or not args.bucket:
            logger.error("File path and bucket name are required for upload action")
            return
        upload_supportcase_file(args.file, args.bucket, args.prefix, args.region)

if __name__ == "__main__":
    main()