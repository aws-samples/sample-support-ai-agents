#!/bin/bash

# Optira Cognito Deployment Script
# Usage: ./deploy.sh [region]
# Default region: us-west-2

set -e

REGION=${1:-us-west-2}
STACK_NAME="optira-cognito"
TEMPLATE_FILE="cognito-stack.yaml"
ENV_FILE="../.env"

echo "🚀 Deploying Optira Cognito User Pool to region: $REGION"
echo "📁 Stack name: $STACK_NAME"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --region $REGION >/dev/null 2>&1; then
    echo "❌ AWS CLI not configured or no access to region $REGION"
    exit 1
fi

# Deploy CloudFormation stack
echo "📦 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_IAM \
    --no-fail-on-empty-changeset

# Get stack outputs
echo "📋 Getting stack outputs..."
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
    --output text)

echo "✅ Deployment completed!"
echo "🔑 User Pool ID: $USER_POOL_ID"
echo "🔑 Client ID: $CLIENT_ID"
echo "🌍 Region: $REGION"

# Create test user
echo "👤 Creating test user..."
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username testuser@example.com \
    --user-attributes Name=email,Value=testuser@example.com Name=email_verified,Value=true \
    --temporary-password "TestPassword123!" \
    --message-action SUPPRESS \
    --region $REGION

echo "✅ Test user created successfully!"

# Update .env file
echo "📝 Updating .env file..."
if [ -f "$ENV_FILE" ]; then
    # Create backup
    cp $ENV_FILE ${ENV_FILE}.backup
    
    # Update or add environment variables
    sed -i.tmp "s/^REACT_APP_COGNITO_USER_POOL_ID=.*/REACT_APP_COGNITO_USER_POOL_ID=$USER_POOL_ID/" $ENV_FILE
    sed -i.tmp "s/^REACT_APP_COGNITO_USER_POOL_WEB_CLIENT_ID=.*/REACT_APP_COGNITO_USER_POOL_WEB_CLIENT_ID=$CLIENT_ID/" $ENV_FILE
    sed -i.tmp "s/^REACT_APP_AWS_REGION=.*/REACT_APP_AWS_REGION=$REGION/" $ENV_FILE
    
    # Add variables if they don't exist
    if ! grep -q "REACT_APP_COGNITO_USER_POOL_ID" $ENV_FILE; then
        echo "REACT_APP_COGNITO_USER_POOL_ID=$USER_POOL_ID" >> $ENV_FILE
    fi
    if ! grep -q "REACT_APP_COGNITO_USER_POOL_WEB_CLIENT_ID" $ENV_FILE; then
        echo "REACT_APP_COGNITO_USER_POOL_WEB_CLIENT_ID=$CLIENT_ID" >> $ENV_FILE
    fi
    if ! grep -q "REACT_APP_AWS_REGION" $ENV_FILE; then
        echo "REACT_APP_AWS_REGION=$REGION" >> $ENV_FILE
    fi
    
    rm -f ${ENV_FILE}.tmp
    echo "✅ .env file updated successfully!"
else
    echo "⚠️  .env file not found, creating new one..."
    cat > $ENV_FILE << EOF
PORT=3000
REACT_APP_API_ENDPOINT=http://localhost:3001/api/chat
REACT_APP_COGNITO_USER_POOL_ID=$USER_POOL_ID
REACT_APP_COGNITO_USER_POOL_WEB_CLIENT_ID=$CLIENT_ID
REACT_APP_AWS_REGION=$REGION
EOF
    echo "✅ .env file created!"
fi

echo ""
echo "🎉 Deployment complete!"
echo "📋 Test user credentials:"
echo "   Username: testuser"
echo "   Password: TestPassword123!"
echo ""
echo "🔄 Next steps:"
echo "   1. Run 'npm run build' to rebuild with new configuration"
echo "   2. Run './start.sh' to start the application"
echo ""
echo "🗑️  To cleanup: aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
