# Optira Core

An intelligent AWS support case analysis and insights platform powered by Amazon Bedrock and AWS Lambda.

## Overview

Optira Core is a comprehensive solution that collects, processes, and analyzes AWS support cases using AI-powered insights. The platform consists of multiple microservices that work together to provide intelligent recommendations and knowledge extraction from support data.

## Architecture

The project is organized into the following components:

- **es-optira**: Main agent Lambda function with AI-powered query processing
- **es-optira-collector**: Data collection service for AWS support cases
- **es-optira-data-pipeline**: Data processing and metadata extraction pipeline
- **es-optira-kb**: Knowledge Base management using Amazon Bedrock
- **es-optira-agentcore**: Core agent functionality and dependencies

## Prerequisites

- Node.js (v18 or later)
- Python 3.12
- AWS CLI configured with appropriate permissions
- AWS CDK CLI
- An S3 bucket for storing support case data

## Quick Start

1. **Navigate to the optira-core directory**:
   ```bash
   cd optira-core
   ```

2. **Deploy all services**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Follow the prompts** to enter your S3 bucket name for the Knowledge Base

   **S3 Bucket Options:**
   - **Option 1 (Default)**: Create new bucket - Choose this if you want the system to create a new S3 bucket
   - **Option 2**: Use existing bucket - Choose this if you have an existing S3 bucket you want to use

   The deployment script will ask you to choose between these options after you enter the bucket name.

4. **Increase API Gateway Integration Timeout**

   After deployment, increase the API Gateway integration timeout from 29 seconds to 120 seconds:

   1. Navigate to AWS Service Quotas console: https://us-east-1.console.aws.amazon.com/servicequotas/home/services/apigateway/quotas
   2. Search for and select "Maximum integration timeout in milliseconds"
   3. Click "Request increase at account level"
   4. Change the quota value from 29,000 milliseconds to 120,000 milliseconds
   5. Provide a justification (e.g., "Required for AI agent processing of complex analytical queries")
   6. Submit the request

   The quota increase is typically approved within a few minutes to 1 business day.

## Usage

### Query the Agent

Send POST requests to the deployed Lambda function:

```json
{
  "query": "What is total count of RDS issues?"
}
```

### API Gateway Access

You can also access the agent via API Gateway. The API Gateway URL is provided in the CDK deployment output, and you'll need to retrieve the API key value:

```bash
# Get the API key value using the API key ID from deployment output
aws apigateway get-api-key --api-key <API-KEY-ID> --include-value --region us-west-2

# Example API call
curl -X POST \
  'https://your-api-gateway-url.execute-api.us-west-2.amazonaws.com/prod/prompt' \
  -H 'x-api-key: YOUR_API_KEY_VALUE' \
  -H 'Content-Type: application/json' \
  -d '{"query": "how many support cases entered, give me a breakdown year by year?"}'
```

**Result:**
```
Perfect! Here's your year-by-year breakdown of support cases:
```

**Note:** Replace the API Gateway URL with the value from your CDK deployment output (`ApiUrl`), and use the API key ID from the deployment output (`ProdApiKeyId`) to retrieve the actual API key value.

### Test Knowledge Base

```bash
cd es-optira-kb
python3 test_kb.py --region us-west-2 --action query --kb-id YOUR_KB_ID --query-text "Your question"
```

## Features

- **AI-Powered Analysis**: Uses Amazon Bedrock for intelligent case analysis
- **Knowledge Base Integration**: Automated knowledge extraction from support cases
- **Case Aggregation**: Collects and processes AWS support case data
- **Event Processing**: Real-time processing of support events
- **Scalable Architecture**: Built on AWS Lambda for automatic scaling

## Configuration

Key environment variables:

- `SYSTEM_PROMPT`: AI agent system prompt configuration
- `SupportDataBucket`: S3 bucket for storing support data
- `AthenaDatabaseName`: Athena database name for queries

## Monitoring

All components include CloudWatch logging and monitoring. Check the AWS Console for:

- Lambda function logs
- CloudFormation stack status
- S3 bucket contents
- Bedrock Knowledge Base status

## Cleanup

To remove all deployed resources:

```bash
cd es-optira && cdk destroy
cd ../es-optira-kb && cdk destroy
cd ../es-optira-collector && cdk destroy
cd ../es-optira-data-pipeline && cdk destroy
```

## Manual Deployment

If you prefer to deploy components individually:

### 1. Data Collector
```bash
cd es-optira-collector
npm install
pip3 install -r requirements.txt
cdk deploy --parameters SupportDataBucket=your-bucket-name
```

### 2. Knowledge Base
```bash
cd es-optira-kb
pip3 install -r requirements.txt
cdk deploy --app "python3 kb_cdk.py your-bucket-name"
```

### 3. Data Pipeline
```bash
cd es-optira-data-pipeline
npm install
pip3 install -r requirements.txt
cdk deploy --parameters SupportDataBucket=your-bucket-name
```

### 4. Agent Lambda
```bash
cd es-optira
npm install
pip3 install -r requirements.txt
cdk deploy --parameters SupportDataBucket=your-bucket-name
```

## Support

For issues and questions:
- Check the CloudWatch logs for error details
- Review the CDK deployment outputs
- Ensure all prerequisites are met
- For any support assistance, reach out to your AWS Technical Account Managers (TAMs)

## License

This project is licensed under the MIT License.
