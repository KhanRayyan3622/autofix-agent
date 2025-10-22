#!/bin/bash

# AutoTriage & AutoFix Agent - Deployment Script
# This script deploys the complete infrastructure using AWS SAM

set -e

echo "🚀 Starting AutoTriage & AutoFix Agent deployment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project root: $PROJECT_ROOT"

# Check if parameters file exists
PARAMS_FILE="$SCRIPT_DIR/parameters.json"
if [ ! -f "$PARAMS_FILE" ]; then
    echo "📝 Creating parameters.json file..."
    cat > "$PARAMS_FILE" << EOF
{
  "GitHubToken": "YOUR_GITHUB_TOKEN_HERE",
  "GitHubSecret": "YOUR_GITHUB_SECRET_HERE",
  "BedrockModelId": "anthropic.claude-3-5-sonnet-20241022",
  "ArtifactsBucketName": "autofix-agent-artifacts"
}
EOF
    echo "⚠️  Please edit $PARAMS_FILE with your actual values before deploying!"
    echo "   - GitHubToken: Your GitHub Personal Access Token"
    echo "   - GitHubSecret: Your GitHub webhook secret"
    exit 1
fi

# Validate parameters
echo "🔍 Validating parameters..."
if grep -q "YOUR_GITHUB_TOKEN_HERE" "$PARAMS_FILE"; then
    echo "❌ Please update GitHubToken in $PARAMS_FILE"
    exit 1
fi

if grep -q "YOUR_GITHUB_SECRET_HERE" "$PARAMS_FILE"; then
    echo "❌ Please update GitHubSecret in $PARAMS_FILE"
    exit 1
fi

# Build the SAM application
echo "🔨 Building SAM application..."
cd "$SCRIPT_DIR"
sam build --use-container

# Deploy the application
echo "🚀 Deploying to AWS..."

# Read parameters from JSON file and convert to SAM format
if [ -f "$PARAMS_FILE" ]; then
    echo "📋 Reading parameters from $PARAMS_FILE..."
    
    # Extract parameters using jq or python
    if command -v jq &> /dev/null; then
        GITHUB_TOKEN=$(jq -r '.GitHubToken' "$PARAMS_FILE")
        GITHUB_SECRET=$(jq -r '.GitHubSecret' "$PARAMS_FILE")
        BEDROCK_MODEL_ID=$(jq -r '.BedrockModelId' "$PARAMS_FILE")
        ARTIFACTS_BUCKET_NAME=$(jq -r '.ArtifactsBucketName' "$PARAMS_FILE")
        GITHUB_OWNER=$(jq -r '.GitHubOwner' "$PARAMS_FILE")
        GITHUB_REPO=$(jq -r '.GitHubRepo' "$PARAMS_FILE")
    else
        # Fallback to python if jq is not available
        GITHUB_TOKEN=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['GitHubToken'])")
        GITHUB_SECRET=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['GitHubSecret'])")
        BEDROCK_MODEL_ID=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['BedrockModelId'])")
        ARTIFACTS_BUCKET_NAME=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['ArtifactsBucketName'])")
        GITHUB_OWNER=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['GitHubOwner'])")
        GITHUB_REPO=$(python3 -c "import json; print(json.load(open('$PARAMS_FILE'))['GitHubRepo'])")
    fi
    
    echo "✅ Parameters loaded successfully"
else
    echo "❌ Parameters file not found: $PARAMS_FILE"
    exit 1
fi

sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name autofix-agent \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        GitHubToken="$GITHUB_TOKEN" \
        GitHubSecret="$GITHUB_SECRET" \
        BedrockModelId="$BEDROCK_MODEL_ID" \
        ArtifactsBucketName="$ARTIFACTS_BUCKET_NAME" \
        GitHubOwner="$GITHUB_OWNER" \
        GitHubRepo="$GITHUB_REPO" \
    --resolve-s3 \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

# Get outputs
echo "📋 Getting deployment outputs..."
WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name autofix-agent \
    --query 'Stacks[0].Outputs[?OutputKey==`WebhookURL`].OutputValue' \
    --output text)

DASHBOARD_URL=$(aws cloudformation describe-stacks \
    --stack-name autofix-agent \
    --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
    --output text)

ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name autofix-agent \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucket`].OutputValue' \
    --output text)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "======================"
echo "🌐 Webhook URL: $WEBHOOK_URL"
echo "📊 Dashboard URL: $DASHBOARD_URL"
echo "🗄️  Artifacts Bucket: $ARTIFACTS_BUCKET"
echo ""
echo "🔧 Next Steps:"
echo "=============="
echo "1. Configure GitHub webhook:"
echo "   - Go to your repository Settings → Webhooks"
echo "   - Add webhook URL: $WEBHOOK_URL"
echo "   - Select 'Issues' events"
echo "   - Set secret token (same as GitHubSecret in parameters.json)"
echo ""
echo "2. Test the agent:"
echo "   cd $PROJECT_ROOT"
echo "   python scripts/test_agent.py"
echo ""
echo "3. Create a test issue:"
echo "   python scripts/create_test_issue.py"
echo ""
echo "4. Monitor logs:"
echo "   aws logs tail /aws/lambda/autofix-agent-webhook-handler --follow"
echo "   aws logs tail /aws/lambda/autofix-agent-agent-orchestrator --follow"
echo ""
echo "🎉 Your AutoTriage & AutoFix Agent is ready!"
echo "   Visit the dashboard: $DASHBOARD_URL"
