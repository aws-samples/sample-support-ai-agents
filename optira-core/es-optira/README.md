# Optira Agent Lambda

CDK TypeScript project to deploy Agent Lambda functions with Bedrock integration.

## Prerequisites

- Node.js and npm
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS CLI configured with appropriate permissions
- Python 3.10+ (for Lambda functions)

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Bootstrap CDK (first time only):
   ```bash
   cdk bootstrap
   ```

## Deployment

```bash
cdk deploy
```

## Project Structure

- `bin/`: CDK app entry point
- `lib/`: CDK stack definitions
- `lambda/`: Lambda function source code
  - `lambda_function.py`: Main Lambda handler
  - `bedrockAPI.py`: Bedrock API integration
  - `knowledgeBaseTool.py`: Knowledge base operations
  - `caseAggregationTool.py`: Case aggregation logic
  - `eventAggregationTool.py`: Event aggregation logic
  - `queryExecutor.py`: Query execution utilities
- `requirements.txt`: Python dependencies for Lambda
- `cdk.json`: CDK configuration