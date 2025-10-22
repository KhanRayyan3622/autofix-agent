#!/usr/bin/env python3
"""
AutoTriage & AutoFix Agent - Complete Setup Script

This script guides you through the complete setup and deployment process
for the AWS AI Agent Global Hackathon project.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print welcome banner."""
    print("=" * 80)
    print("🤖 AutoTriage & AutoFix Agent - Complete Setup")
    print("   AWS AI Agent Global Hackathon 2025")
    print("=" * 80)
    print()

def check_prerequisites():
    """Check if required tools are installed."""
    print("🔍 Checking prerequisites...")
    
    required_tools = {
        'aws': 'AWS CLI',
        'python3': 'Python 3',
        'git': 'Git'
    }
    
    missing_tools = []
    
    for tool, name in required_tools.items():
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"  ✅ {name} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  ❌ {name} is not installed")
            missing_tools.append(name)
    
    if missing_tools:
        print(f"\n❌ Missing required tools: {', '.join(missing_tools)}")
        print("Please install them before continuing.")
        return False
    
    print("✅ All prerequisites are installed!")
    return True

def check_aws_credentials():
    """Check AWS credentials configuration."""
    print("\n🔐 Checking AWS credentials...")
    
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        identity = json.loads(result.stdout)
        print(f"  ✅ AWS credentials configured")
        print(f"  📋 Account ID: {identity.get('Account')}")
        print(f"  👤 User ARN: {identity.get('Arn')}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ❌ AWS credentials not configured")
        print("\n📝 To configure AWS credentials:")
        print("  1. Run: aws configure")
        print("  2. Enter your Access Key ID")
        print("  3. Enter your Secret Access Key")
        print("  4. Choose your region (e.g., us-east-1)")
        print("  5. Choose output format (json)")
        return False

def setup_github_credentials():
    """Setup GitHub credentials."""
    print("\n🐙 Setting up GitHub credentials...")
    
    github_token = input("Enter your GitHub Personal Access Token: ").strip()
    if not github_token:
        print("❌ GitHub token is required")
        return False
    
    github_secret = input("Enter your GitHub webhook secret (or press Enter for 'autofix-secret'): ").strip()
    if not github_secret:
        github_secret = "autofix-secret"
    
    # Update parameters.json
    params_file = Path("infra/parameters.json")
    if params_file.exists():
        with open(params_file, 'r') as f:
            params = json.load(f)
        
        params['GitHubToken'] = github_token
        params['GitHubSecret'] = github_secret
        
        # Get GitHub repository info
        github_repo = input("Enter your GitHub repository (owner/repo, e.g., username/test-repo): ").strip()
        if github_repo and '/' in github_repo:
            owner, repo = github_repo.split('/', 1)
            params['GitHubOwner'] = owner
            params['GitHubRepo'] = repo
        else:
            params['GitHubOwner'] = 'testuser'
            params['GitHubRepo'] = 'test-repo'
        
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)
        
        print("✅ GitHub credentials saved to parameters.json")
        return True
    else:
        print("❌ parameters.json not found")
        return False

def check_bedrock_access():
    """Check Bedrock access."""
    print("\n🧠 Checking Bedrock access...")
    
    try:
        result = subprocess.run(['aws', 'bedrock', 'list-foundation-models'], 
                              capture_output=True, text=True, check=True)
        models = json.loads(result.stdout)
        
        claude_models = [m for m in models.get('modelSummaries', []) 
                        if 'claude' in m.get('modelId', '').lower()]
        
        if claude_models:
            print("  ✅ Bedrock access confirmed")
            print(f"  📋 Found {len(claude_models)} Claude models")
            return True
        else:
            print("  ⚠️  Bedrock access confirmed but no Claude models found")
            print("  💡 You may need to request access to Claude models")
            return True
            
    except subprocess.CalledProcessError as e:
        if "AccessDenied" in str(e):
            print("  ❌ Bedrock access denied")
            print("  💡 You may need to request access to Bedrock")
            return False
        else:
            print("  ⚠️  Could not check Bedrock access")
            return True

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def deploy_infrastructure():
    """Deploy AWS infrastructure."""
    print("\n🚀 Deploying AWS infrastructure...")
    
    try:
        # Make deploy script executable
        deploy_script = Path("infra/deploy.sh")
        if deploy_script.exists():
            os.chmod(deploy_script, 0o755)
        
        # Run deployment
        result = subprocess.run(['./infra/deploy.sh'], 
                              cwd=os.getcwd(), 
                              capture_output=True, 
                              text=True, 
                              check=True)
        
        print("✅ Infrastructure deployed successfully!")
        
        # Extract important URLs from output
        output_lines = result.stdout.split('\n')
        webhook_url = None
        dashboard_url = None
        
        for line in output_lines:
            if 'Webhook URL:' in line:
                webhook_url = line.split('Webhook URL:')[1].strip()
            elif 'Dashboard URL:' in line:
                dashboard_url = line.split('Dashboard URL:')[1].strip()
        
        if webhook_url:
            print(f"🌐 Webhook URL: {webhook_url}")
        if dashboard_url:
            print(f"📊 Dashboard URL: {dashboard_url}")
        
        return True, webhook_url, dashboard_url
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Infrastructure deployment failed: {e}")
        print(f"Error output: {e.stderr}")
        return False, None, None

def setup_github_webhook(webhook_url):
    """Setup GitHub webhook."""
    print(f"\n🔗 Setting up GitHub webhook...")
    print(f"Webhook URL: {webhook_url}")
    
    print("\n📝 Manual steps required:")
    print("1. Go to your GitHub repository")
    print("2. Click Settings → Webhooks")
    print("3. Click 'Add webhook'")
    print(f"4. Set Payload URL to: {webhook_url}")
    print("5. Set Content type to: application/json")
    print("6. Select 'Issues' events")
    print("7. Set Secret to the value in parameters.json")
    print("8. Click 'Add webhook'")
    
    input("\nPress Enter when you've completed the webhook setup...")

def test_deployment():
    """Test the deployment."""
    print("\n🧪 Testing deployment...")
    
    try:
        # Run test script
        result = subprocess.run([sys.executable, 'scripts/test_agent.py'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Tests passed successfully!")
        print("Test output:")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_demo_issue():
    """Create a demo issue."""
    print("\n🎬 Creating demo issue...")
    
    try:
        result = subprocess.run([sys.executable, 'scripts/create_test_issue.py', '--demo'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Demo issue created successfully!")
        print("Output:")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create demo issue: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup process."""
    print_banner()
    
    # Check prerequisites
    if not check_prerequisites():
        return False
    
    # Check AWS credentials
    if not check_aws_credentials():
        print("\n❌ Please configure AWS credentials and run this script again.")
        return False
    
    # Check Bedrock access
    if not check_bedrock_access():
        print("\n⚠️  Bedrock access issues detected. You may need to request access.")
        print("Continuing with deployment...")
    
    # Setup GitHub credentials
    if not setup_github_credentials():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Deploy infrastructure
    success, webhook_url, dashboard_url = deploy_infrastructure()
    if not success:
        return False
    
    # Setup GitHub webhook
    if webhook_url:
        setup_github_webhook(webhook_url)
    
    # Test deployment
    if not test_deployment():
        print("\n⚠️  Some tests failed, but deployment may still work.")
    
    # Create demo issue
    create_demo_issue()
    
    # Final instructions
    print("\n" + "=" * 80)
    print("🎉 SETUP COMPLETE!")
    print("=" * 80)
    print()
    print("📋 Next steps:")
    print("1. Record your demo video using the script in demo/demo_script.md")
    print("2. Submit to Devpost using the text in docs/submission_text.md")
    print("3. Monitor the dashboard for real-time metrics")
    print()
    
    if dashboard_url:
        print(f"🌐 Dashboard: {dashboard_url}")
    
    if webhook_url:
        print(f"🔗 Webhook: {webhook_url}")
    
    print("\n📚 Documentation:")
    print("- README.md: Complete project documentation")
    print("- demo/demo_script.md: 3-minute demo script")
    print("- docs/submission_text.md: Devpost submission text")
    print()
    print("🏆 Good luck with the hackathon!")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
