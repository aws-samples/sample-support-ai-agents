# Amazon Bedrock Knowledge Base Solution

A minimal solution for creating and testing Amazon Bedrock Knowledge Bases with S3 support case files.

## Files

- `bedrock_kb_core.py`: Core functionality for creating and managing knowledge bases
- `kb_cdk.py`: CDK stack for deploying the required infrastructure
- `test_kb.py`: Simple test script for validating the knowledge base

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- AWS CDK v2 installed (latest version)
- Node.js and npm (for CDK CLI)
- Required Python packages: boto3, requests, requests-aws4auth

> **Important**: Make sure your CDK CLI version is compatible with the CDK library used in the application. If you see a schema version mismatch error, update the CDK CLI to the latest version using `npm install -g aws-cdk@latest`.

## Setup

1. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install the required dependencies and update the CDK CLI:

```bash
pip3 install -r requirements.txt
npm install -g aws-cdk@latest  # Update CDK CLI to the latest version
```

3. Deploy the CDK stack with your existing S3 bucket name:

```bash
cdk bootstrap
# Edit cdk.json to set your bucket name
vim cdk.json  # or use any text editor
cdk deploy
```

Alternatively, you can specify the app command directly:

```bash
cdk deploy --app "python3 kb_cdk.py bedrock-kb-supportdatawest"
```

If you see any notices that you want to suppress, you can acknowledge them:

```bash
cdk acknowledge <id>
```

Note: This solution assumes you already have an S3 bucket created.

## Usage

### Creating a Knowledge Base

First, get the role ARN from the CDK stack outputs:

```bash
# Get the role ARN from CDK stack
ROLE_ARN=$(aws cloudformation describe-stacks --stack-name BedrockKnowledgeBaseStack --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseRoleArn`].OutputValue' --output text)
```

Then use the `bedrock_kb_core.py` script to create a complete knowledge base:

```bash
python3 bedrock_kb_core.py --region us-west-2 --bucket bedrock-kb-supportdatawest --prefix support-cases --role-arn $ROLE_ARN
```

This will:
1. Create an OpenSearch Serverless collection
2. Create a Bedrock Knowledge Base using the CDK-created role
3. Create a data source pointing to your S3 bucket
4. Start an ingestion job


### Testing the Knowledge Base

Use the `test_kb.py` script to test your knowledge base:

```bash

# Get details of a knowledge base
python test_kb.py --region us-west-2 --action get --kb-id T5LLHYCYRR

# Query a knowledge base
python test_kb.py --region us-west-2 --action query --kb-id T5LLHYCYRR --query-text "What information do you have about Enterprise Support cases?"

```

## Architecture

This solution uses the following AWS services:

- **Amazon Bedrock**: For knowledge base creation and querying
- **Amazon S3**: For storing support files (existing bucket)
- **Amazon OpenSearch Serverless**: For vector storage and search
- **AWS IAM**: For permissions management

## Cleanup

To delete the CDK stack:

```bash
cdk destroy
```

Note: This will not affect your existing S3 bucket or its contents.