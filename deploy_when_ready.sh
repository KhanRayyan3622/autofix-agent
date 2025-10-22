#!/bin/bash

# AutoTriage & AutoFix Agent - Network Test & Deployment Script
# This script tests network connectivity and deploys when ready

echo "🔍 AutoTriage & AutoFix Agent - Network Test & Deployment"
echo "========================================================"

# Test network connectivity
echo "📡 Testing network connectivity..."

# Test GitHub connectivity
if ping -c 1 github.com > /dev/null 2>&1; then
    echo "✅ GitHub connectivity: OK"
    GITHUB_OK=true
else
    echo "❌ GitHub connectivity: FAILED"
    GITHUB_OK=false
fi

# Test AWS connectivity
if ping -c 1 cloudformation.us-east-1.amazonaws.com > /dev/null 2>&1; then
    echo "✅ AWS connectivity: OK"
    AWS_OK=true
else
    echo "❌ AWS connectivity: FAILED"
    AWS_OK=false
fi

echo ""
echo "📊 Network Status Summary:"
echo "GitHub: $([ "$GITHUB_OK" = true ] && echo "✅ Ready" || echo "❌ Not Ready")"
echo "AWS: $([ "$AWS_OK" = true ] && echo "✅ Ready" || echo "❌ Not Ready")"

if [ "$GITHUB_OK" = true ] && [ "$AWS_OK" = true ]; then
    echo ""
    echo "🚀 All systems ready! Starting deployment..."
    
    # Deploy to AWS
    echo "📦 Deploying to AWS..."
    cd /home/rio/agent
    ./infra/deploy.sh
    
    if [ $? -eq 0 ]; then
        echo "✅ AWS deployment successful!"
        
        # Push to GitHub
        echo "📤 Pushing to GitHub..."
        git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo "✅ GitHub push successful!"
            echo ""
            echo "🎉 DEPLOYMENT COMPLETE!"
            echo "Your AutoTriage & AutoFix Agent is now live!"
            echo ""
            echo "📋 Next steps:"
            echo "1. Check AWS Console for deployed resources"
            echo "2. Configure GitHub webhook with API Gateway URL"
            echo "3. Test the complete workflow"
            echo "4. Record your demo video"
            echo "5. Submit to AWS AI Agent Hackathon"
        else
            echo "❌ GitHub push failed"
        fi
    else
        echo "❌ AWS deployment failed"
    fi
else
    echo ""
    echo "⏳ Waiting for network connectivity..."
    echo "Please run this script again when network is available."
    echo ""
    echo "💡 You can also try:"
    echo "- Check your internet connection"
    echo "- Restart your network service"
    echo "- Try a different network"
fi

echo ""
echo "📚 For more information, see DEPLOYMENT_STATUS.md"
