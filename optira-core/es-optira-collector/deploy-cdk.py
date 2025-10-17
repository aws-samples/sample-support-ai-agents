#!/usr/bin/env python3
"""
CDK deployment script to replace deploy_lambda_function.py
"""
import os
import subprocess
import sys
import argparse

def deploy_support_collector(resource_bucket_name, support_data_bucket_name, lambda_role_name=None):
    """Deploy the Support Collector stack using CDK"""
    
    print(f"Deploying Support Collector with:")
    print(f"  Resource Bucket: {resource_bucket_name}")
    print(f"  Support Data Bucket: {support_data_bucket_name}")
    if lambda_role_name:
        print(f"  Lambda Role Name: {lambda_role_name}")
    
    # Set environment variables for CDK
    env = os.environ.copy()
    env['RESOURCE_BUCKET_NAME'] = resource_bucket_name
    env['SUPPORT_DATA_BUCKET_NAME'] = support_data_bucket_name
    if lambda_role_name:
        env['LAMBDA_ROLE_NAME'] = lambda_role_name
    
    try:
        # Install npm dependencies
        print("Installing npm dependencies...")
        subprocess.run(['npm', 'install'], check=True, env=env)
        
        # Bootstrap CDK (if needed)
        print("Bootstrapping CDK...")
        subprocess.run(['npx', 'cdk', 'bootstrap'], check=True, env=env)
        
        # Deploy the stack
        print("Deploying CDK stack...")
        subprocess.run(['npx', 'cdk', 'deploy', '--require-approval', 'never'], check=True, env=env)
        
        print("Support Collector stack deployed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deploy Support Collector Lambda using CDK')
    parser.add_argument('--resource_bucket_name', required=True, 
                       help='Name of the S3 bucket containing the Lambda package')
    parser.add_argument('--support_data_bucket_name', required=True, 
                       help='Name of the S3 bucket containing support data')
    parser.add_argument('--lambda_role_name', 
                       help='Optional custom name for the Lambda IAM role')
    
    args = parser.parse_args()
    
    deploy_support_collector(
        args.resource_bucket_name, 
        args.support_data_bucket_name,
        args.lambda_role_name
    )