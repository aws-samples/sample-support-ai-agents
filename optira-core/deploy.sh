#!/bin/bash

set -e

# Parse region parameter
REGION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Get default region if not specified
if [ -z "$REGION" ]; then
    REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "deploy.sh" ]; then
    print_error "Please run this script from the optira-core root directory"
    exit 1
fi

print_status "Starting Optira Core deployment..."
print_status "Target Region: $REGION"

# Check prerequisites
print_status "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    exit 1
fi

print_status "Prerequisites check passed"

# Clean npm cache and install global CDK CLI
print_status "Cleaning npm cache..."
# Fix npm permission issues automatically
if [ -d "$HOME/.npm" ]; then
    sudo chown -R $(id -u):$(id -g) "$HOME/.npm" 2>/dev/null || {
        print_status "Removing problematic npm cache..."
        sudo rm -rf "$HOME/.npm"
    }
fi
npm cache clean --force

print_status "Installing/updating AWS CDK CLI..."
# Install CDK globally but fix permissions immediately after
sudo npm install -g aws-cdk@latest
# Fix permissions that may have been created by sudo npm
if [ -d "$HOME/.npm" ]; then
    sudo chown -R $(id -u):$(id -g) "$HOME/.npm" 2>/dev/null || true
fi

# Create Python virtual environment
print_status "Creating Python virtual environment..."
# Fix CDK cache permission issues
if [ -d "$HOME/Library/Caches/com.amazonaws.jsii" ]; then
    sudo chown -R $(id -u):$(id -g) "$HOME/Library/Caches/com.amazonaws.jsii" 2>/dev/null || {
        print_status "Removing problematic CDK cache..."
        sudo rm -rf "$HOME/Library/Caches/com.amazonaws.jsii"
    }
fi
python3 -m venv .venv
source .venv/bin/activate

# Prompt for S3 bucket name and creation preference
read -p "Enter your S3 bucket name for Knowledge Base (or press Enter to skip): " S3_BUCKET

if [ -n "$S3_BUCKET" ]; then
    echo ""
    echo "S3 Bucket Options:"
    echo "1. Create new bucket (default)"
    echo "2. Use existing bucket"
    read -p "Choose option (1 or 2): " BUCKET_OPTION
    
    case $BUCKET_OPTION in
        2)
            CREATE_NEW_BUCKET="false"
            print_status "Will use existing S3 bucket: $S3_BUCKET"
            ;;
        *)
            CREATE_NEW_BUCKET="true"
            print_status "Will create new S3 bucket: $S3_BUCKET"
            ;;
    esac
else
    CREATE_NEW_BUCKET="true"
fi

# Prompt for WAF protection
echo ""
echo "AWS WAF Protection Options:"
echo "1. Disable WAF (default - no additional cost)"
echo "2. Enable WAF (provides DDoS protection - additional AWS charges apply)"
read -p "Choose option (1 or 2): " WAF_OPTION

case $WAF_OPTION in
    2)
        ENABLE_WAF="true"
        print_status "WAF protection will be enabled for API Gateway"
        ;;
    *)
        ENABLE_WAF="false"
        print_status "WAF protection will be disabled"
        ;;
esac
# -------------------------------------------------------------------------------------------
# Start Deploy es-optira-collector (Python CDK) 
print_status "Deploying es-optira-collector (data collector)..."
cd es-optira-collector

# Clean up any leftover packaging files with permission issues
print_status "Cleaning up packaging directory..."
sudo rm -rf packaging 2>/dev/null || true
sudo rm -rf cdk.out 2>/dev/null || true

print_status "Installing Node.js dependencies..."
npm install

print_status "Installing Python dependencies for Lambda..."
# Install Python dependencies for lambda with correct architecture
pip3 install -r requirements.txt \
    --python-version 3.12 \
    --platform manylinux2014_aarch64 \
    --target ./packaging/_dependencies \
    --only-binary=:all:

python3 ./bin/package_for_lambda.py

print_status "Bootstrapping CDK (if needed)..."
cdk bootstrap

print_status "Deploying es-optira-collector stack..."
export AWS_DEFAULT_REGION=$REGION
npx cdk deploy --parameters SupportDataBucket=$S3_BUCKET --parameters CreateNewBucket=$CREATE_NEW_BUCKET --parameters AthenaDatabaseName=optira_database --require-approval never --region $REGION

# END Deploy es-optira-collector 
# -------------------------------------------------------------------------------------------

cd ..

# -------------------------------------------------------------------------------------------
# Deploy es-optira-kb (Python CDK) 
print_status "Deploying es-optira-kb (Optira Knowledge Base Stack)..."
cd es-optira-kb

print_status "Installing Python dependencies for KB..."
pip3 install -r requirements.txt

print_status "Deploying es-optira-kb stack..."

# Check if stack exists and its state
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name OptiraKnowledgeBaseStack --query 'Stacks[0].StackStatus' --output text --region $REGION 2>/dev/null || echo "NOT_EXISTS")

if [ "$STACK_STATUS" = "CREATE_IN_PROGRESS" ] || [ "$STACK_STATUS" = "UPDATE_IN_PROGRESS" ]; then
    print_status "Stack is in progress, waiting for completion..."
    aws cloudformation wait stack-create-complete --stack-name OptiraKnowledgeBaseStack --region $REGION 2>/dev/null || \
    aws cloudformation wait stack-update-complete --stack-name OptiraKnowledgeBaseStack --region $REGION 2>/dev/null || {
        print_warning "Stack operation failed or timed out. Deleting and recreating..."
        aws cloudformation delete-stack --stack-name OptiraKnowledgeBaseStack --region $REGION
        aws cloudformation wait stack-delete-complete --stack-name OptiraKnowledgeBaseStack --region $REGION
    }
fi

cdk deploy --app "python3 kb_cdk.py $S3_BUCKET" --require-approval never --region $REGION

# Get stack outputs
print_status "es-optira-kb stack outputs:"
aws cloudformation describe-stacks --stack-name OptiraKnowledgeBaseStack --query 'Stacks[0].Outputs' --output table 2>/dev/null || print_warning "OptiraKnowledgeBaseStack outputs not available"

# Create Knowledge Base using bedrock_kb_core.py
print_status "Creating Knowledge Base..."
ROLE_ARN=$(aws cloudformation describe-stacks --stack-name OptiraKnowledgeBaseStack --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseRoleArn`].OutputValue' --output text 2>/dev/null)

if [ -z "$ROLE_ARN" ] || [ "$ROLE_ARN" = "None" ]; then
    print_warning "Could not retrieve Role ARN from OptiraKnowledgeBaseStack. Skipping Knowledge Base creation."
    print_warning "You can create it manually later using: python3 es-optira-kb/bedrock_kb_core.py --region $REGION --bucket YOUR_BUCKET --role-arn YOUR_ROLE_ARN"
else
    print_status "Retrieved Role ARN: $ROLE_ARN"
    
    # Verify the role exists before proceeding
    print_status "Verifying IAM role exists..."
    ROLE_NAME=$(echo $ROLE_ARN | cut -d'/' -f2)
    
    # Wait for role to be available (up to 60 seconds)
    for i in {1..12}; do
        if aws iam get-role --role-name "$ROLE_NAME" --region $REGION >/dev/null 2>&1; then
            print_status "IAM role verified and ready"
            break
        else
            print_status "Waiting for IAM role to be available... (attempt $i/12)"
            sleep 5
        fi
        
        if [ $i -eq 12 ]; then
            print_warning "IAM role not found after 60 seconds. Proceeding anyway..."
        fi
    done
    
    if [ -n "$S3_BUCKET" ]; then
        print_status "Creating Knowledge Base with bucket: $S3_BUCKET"
        #cd es-optira-kb
        
        # Try to create Knowledge Base, handle IAM permission errors
        if ! python3 bedrock_kb_core.py --region $REGION --bucket "$S3_BUCKET" --prefix support-cases --role-arn "$ROLE_ARN"; then
            print_warning "Knowledge Base creation failed, likely due to IAM permissions. Attempting to recreate..."
            
            # Delete the failed Knowledge Base stack and recreate
            print_status "Deleting OptiraKnowledgeBaseStack to fix IAM permissions..."
            cdk destroy OptiraKnowledgeBaseStack --force --region $REGION 2>/dev/null || true
            
            # Wait a moment for deletion
            sleep 10
            
            # Redeploy with updated permissions
            print_status "Redeploying Knowledge Base stack with updated IAM permissions..."
            cdk deploy --app "python3 kb_cdk.py $S3_BUCKET" --require-approval never --region $REGION
            
            # Get updated role ARN
            ROLE_ARN=$(aws cloudformation describe-stacks --stack-name OptiraKnowledgeBaseStack --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseRoleArn`].OutputValue' --output text --region $REGION 2>/dev/null)
            
            # Retry Knowledge Base creation
            print_status "Retrying Knowledge Base creation with updated permissions..."
            python3 bedrock_kb_core.py --region $REGION --bucket "$S3_BUCKET" --prefix support-cases --role-arn "$ROLE_ARN"
        fi
        
        #cd ..
        print_status "Knowledge Base creation completed!"
        
        # The Knowledge Base creation script already handles storing the KB ID in Secrets Manager
        print_status "Knowledge Base ID has been stored in Secrets Manager by bedrock_kb_core.py"
    else
        print_warning "Skipping Knowledge Base creation. You can create it manually later using:"
        echo "cd es-optira-kb && python3 bedrock_kb_core.py --region $REGION --bucket YOUR_BUCKET --prefix support-cases --role-arn $ROLE_ARN"
    fi
fi

# -------------------------------------------------------------------------------------------

cd ..

# -------------------------------------------------------------------------------------------
# Deploy es-optira-data-pipeline (TypeScript CDK with Lambda)
cd es-optira-data-pipeline

print_status "Installing Node.js dependencies..."
npm install

pip3 install -r requirements.txt \
    --python-version 3.12 \
    --platform manylinux2014_aarch64 \
    --target ./packaging/_dependencies \
    --only-binary=:all:

python3 ./bin/package_for_lambda.py

print_status "Bootstrapping CDK (if needed)..."
cdk bootstrap

print_status "Deploying es-optira-data-pipeline stack..."
export AWS_DEFAULT_REGION=$REGION
cdk deploy --require-approval never --parameters SupportDataBucket=$S3_BUCKET --parameters CreateNewBucket=$CREATE_NEW_BUCKET --region $REGION

# -------------------------------------------------------------------------------------------

cd ..

# -------------------------------------------------------------------------------------------
# Deploy es-optira (TypeScript CDK with Lambda)
print_status "Deploying es-optira (Agent Lambda Stack)..."
cd es-optira

print_status "Installing Node.js dependencies..."
npm install

print_status "Installing Python dependencies for Lambda..."
# Install Python dependencies for lambda with correct architecture
pip3 install -r requirements.txt \
    --python-version 3.12 \
    --platform manylinux2014_aarch64 \
    --target ./packaging/_dependencies \
    --only-binary=:all:
    
python3 ./bin/package_for_lambda.py

print_status "Bootstrapping CDK (if needed)..."
cdk bootstrap

print_status "Deploying es-optira stack..."
export AWS_DEFAULT_REGION=$REGION
cdk deploy --require-approval never --parameters SupportDataBucket=$S3_BUCKET --parameters CreateNewBucket=$CREATE_NEW_BUCKET --parameters EnableWAF=$ENABLE_WAF --region $REGION
# -------------------------------------------------------------------------------------------

cd ..

print_status "Both stacks deployed successfully!"

# Get stack outputs
print_status "Getting stack outputs..."

print_status "es-optira stack outputs:"
aws cloudformation describe-stacks --stack-name OptiraAgentLambdaStack --query 'Stacks[0].Outputs' --output table 2>/dev/null || print_warning "AgentLambdaStack outputs not available"


print_status "Deployment completed successfully!"
print_warning "Remember to deactivate the virtual environment when done: deactivate"

echo ""
print_status "Next steps:"
echo "1. Test the Agent Lambda function using the AWS Console or CLI"
echo "2. If Knowledge Base was created, test it using: cd es-optira-kb && python3 test_kb.py --region $REGION --action query --kb-id KB_ID --query-text 'Your question'"
echo "3. Upload support case files to your S3 bucket under the 'support-cases' prefix for the Knowledge Base to ingest"
echo ""
print_status "To clean up resources later, run:"
echo "cd es-optira && cdk destroy"
echo "cd ../es-optira-kb && cdk destroy"