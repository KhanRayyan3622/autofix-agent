#!/usr/bin/env python3
"""
AutoTriage & AutoFix Agent - Test Issue Creator

This script creates test issues in a GitHub repository to demonstrate
the autonomous agent capabilities for the hackathon demo.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestIssueCreator:
    """Creates test issues to demonstrate agent capabilities."""
    
    def __init__(self):
        """Initialize the test issue creator."""
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.test_repo = os.environ.get('TEST_REPO', 'octocat/Hello-World')
        
        if not self.github_token:
            logger.error("GITHUB_TOKEN environment variable not set")
            sys.exit(1)
    
    def create_test_issues(self, repo: str = None) -> List[Dict[str, Any]]:
        """
        Create a set of test issues to demonstrate agent capabilities.
        
        Args:
            repo: Repository name in format 'owner/repo'
            
        Returns:
            List of created issues
        """
        repo = repo or self.test_repo
        
        # Define test issues with different complexity levels
        test_issues = [
            {
                'title': 'Fix typo in README.md',
                'body': '''There is a typo in the README.md file on line 15.

**Current text:**
```
This project demostrates the capabilities of our system.
```

**Should be:**
```
This project demonstrates the capabilities of our system.
```

This is a simple typo fix that should be straightforward to resolve automatically.''',
                'labels': ['bug', 'documentation', 'good first issue']
            },
            {
                'title': 'Add missing import statement',
                'body': '''The code is missing an import statement that's causing a NameError.

**Error:**
```
NameError: name 'json' is not defined
```

**File:** `src/utils.py` line 5
**Issue:** The `json` module is used but not imported.

**Expected fix:**
```python
import json
```

This should be added at the top of the file.''',
                'labels': ['bug', 'python', 'import']
            },
            {
                'title': 'Update version number in package.json',
                'body': '''The version number in package.json needs to be updated from 1.0.0 to 1.0.1.

**Current:**
```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "My awesome package"
}
```

**Should be:**
```json
{
  "name": "my-package", 
  "version": "1.0.1",
  "description": "My awesome package"
}
```

This is a simple version bump for a patch release.''',
                'labels': ['enhancement', 'version', 'package.json']
            },
            {
                'title': 'Fix broken link in documentation',
                'body': '''There's a broken link in the documentation that needs to be fixed.

**File:** `docs/getting-started.md` line 23
**Current link:** `https://example.com/old-link`
**Should be:** `https://example.com/new-link`

The old link returns a 404 error. The new link is the correct one.''',
                'labels': ['bug', 'documentation', 'link']
            },
            {
                'title': 'Add error handling for file operations',
                'body': '''The file operations in `src/file_handler.py` need better error handling.

**Current code:**
```python
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()
```

**Issue:** This will raise an exception if the file doesn't exist.

**Expected fix:**
```python
def read_file(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return None
```

This adds proper error handling for missing files.''',
                'labels': ['enhancement', 'python', 'error-handling']
            },
            {
                'title': 'Update dependencies to latest versions',
                'body': '''The dependencies in requirements.txt are outdated and should be updated.

**Current:**
```
requests==2.25.1
numpy==1.19.5
pandas==1.2.4
```

**Should be updated to:**
```
requests==2.31.0
numpy==1.24.3
pandas==2.0.3
```

This updates to the latest stable versions with security fixes.''',
                'labels': ['enhancement', 'dependencies', 'security']
            },
            {
                'title': 'Fix inconsistent indentation',
                'body': '''There's inconsistent indentation in the Python code that needs to be fixed.

**File:** `src/processor.py` lines 10-15
**Current:**
```python
def process_data(data):
    result = []
    for item in data:
        if item is not None:
    result.append(item)
    return result
```

**Issue:** Mixed tabs and spaces, inconsistent indentation.

**Expected fix:**
```python
def process_data(data):
    result = []
    for item in data:
        if item is not None:
            result.append(item)
    return result
```

This fixes the indentation to use consistent spaces.''',
                'labels': ['bug', 'python', 'formatting']
            },
            {
                'title': 'Add missing docstring',
                'body': '''The function `calculate_total` is missing a docstring.

**File:** `src/calculator.py` line 5
**Current:**
```python
def calculate_total(items):
    return sum(item.price for item in items)
```

**Expected fix:**
```python
def calculate_total(items):
    """
    Calculate the total price of all items.
    
    Args:
        items: List of items with price attribute
        
    Returns:
        float: Total price of all items
    """
    return sum(item.price for item in items)
```

This adds proper documentation for the function.''',
                'labels': ['enhancement', 'documentation', 'python']
            }
        ]
        
        created_issues = []
        
        for i, issue_data in enumerate(test_issues, 1):
            try:
                logger.info(f"Creating test issue {i}/{len(test_issues)}: {issue_data['title']}")
                
                # Create issue via GitHub API
                issue_result = self._create_github_issue(repo, issue_data)
                
                if issue_result.get('success'):
                    created_issues.append(issue_result['issue'])
                    logger.info(f"✅ Created issue #{issue_result['issue']['number']}: {issue_data['title']}")
                else:
                    logger.error(f"❌ Failed to create issue: {issue_result.get('error')}")
                
                # Add delay between issues to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error creating test issue {i}: {str(e)}")
        
        return created_issues
    
    def _create_github_issue(self, repo: str, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a GitHub issue via API.
        
        Args:
            repo: Repository name in format 'owner/repo'
            issue_data: Issue data
            
        Returns:
            Creation result
        """
        try:
            import requests
            
            url = f"https://api.github.com/repos/{repo}/issues"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'AutoTriage-AutoFix-Agent/1.0'
            }
            
            data = {
                'title': issue_data['title'],
                'body': issue_data['body'],
                'labels': issue_data.get('labels', [])
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 201:
                return {
                    'success': True,
                    'issue': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'GitHub API error {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create issue: {str(e)}'
            }
    
    def create_demo_issue(self, repo: str = None) -> Dict[str, Any]:
        """
        Create a single demo issue for the hackathon presentation.
        
        Args:
            repo: Repository name in format 'owner/repo'
            
        Returns:
            Created issue
        """
        repo = repo or self.test_repo
        
        demo_issue = {
            'title': '🤖 AutoFix Agent Demo - Fix typo in documentation',
            'body': '''# 🤖 AutoFix Agent Demo Issue

This is a demonstration issue for the **AutoTriage & AutoFix Agent** built for the AWS AI Agent Global Hackathon 2025.

## Issue Description

There is a typo in the main README.md file that needs to be fixed.

**Current text (line 12):**
```markdown
This project demostrates the power of autonomous AI agents.
```

**Should be:**
```markdown
This project demonstrates the power of autonomous AI agents.
```

## Expected Behavior

The AutoFix Agent should:
1. ✅ Detect this as a simple typo fix
2. ✅ Generate a minimal patch
3. ✅ Create a branch and apply the fix
4. ✅ Run tests to ensure no regressions
5. ✅ Create a pull request with explanation

## Agent Capabilities Demonstrated

- **Autonomous Reasoning**: Uses Bedrock AgentCore to analyze the issue
- **Code Generation**: Creates minimal, safe patches
- **GitHub Integration**: Creates branches and pull requests
- **Testing**: Runs automated tests via CodeBuild
- **Learning**: Stores patterns for future improvements

## Hackathon Submission

This issue is part of the **AutoTriage & AutoFix Agent** submission for the AWS AI Agent Global Hackathon 2025.

**Tech Stack:**
- Amazon Bedrock AgentCore (with primitives)
- Amazon Bedrock LLM (Claude 3.5 Sonnet)
- AWS Lambda + API Gateway
- AWS CodeBuild
- Amazon S3
- GitHub API

**Impact:**
- Reduces developer triage time by 60-80%
- Auto-fixes 40-60% of trivial issues
- Measurable ROI with clear KPIs

---
*This issue was created for demonstration purposes.*''',
            'labels': ['🤖', 'autofix-demo', 'hackathon-2025', 'good first issue', 'documentation']
        }
        
        logger.info("Creating demo issue for hackathon presentation...")
        
        result = self._create_github_issue(repo, demo_issue)
        
        if result.get('success'):
            issue = result['issue']
            logger.info(f"✅ Demo issue created successfully!")
            logger.info(f"   Issue #{issue['number']}: {issue['title']}")
            logger.info(f"   URL: {issue['html_url']}")
            return issue
        else:
            logger.error(f"❌ Failed to create demo issue: {result.get('error')}")
            return None
    
    def cleanup_test_issues(self, repo: str = None, issue_numbers: List[int] = None) -> Dict[str, Any]:
        """
        Clean up test issues by closing them.
        
        Args:
            repo: Repository name in format 'owner/repo'
            issue_numbers: List of issue numbers to close
            
        Returns:
            Cleanup result
        """
        repo = repo or self.test_repo
        
        if not issue_numbers:
            logger.info("No issue numbers provided for cleanup")
            return {'success': True, 'message': 'No cleanup needed'}
        
        try:
            import requests
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'AutoTriage-AutoFix-Agent/1.0'
            }
            
            closed_count = 0
            
            for issue_number in issue_numbers:
                try:
                    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
                    data = {'state': 'closed'}
                    
                    response = requests.patch(url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        closed_count += 1
                        logger.info(f"✅ Closed issue #{issue_number}")
                    else:
                        logger.warning(f"⚠️  Failed to close issue #{issue_number}: {response.status_code}")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error closing issue #{issue_number}: {str(e)}")
            
            return {
                'success': True,
                'closed_count': closed_count,
                'total_issues': len(issue_numbers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Cleanup failed: {str(e)}'
            }

def main():
    """Main script runner."""
    parser = argparse.ArgumentParser(description='Create test issues for AutoFix Agent demo')
    parser.add_argument('--repo', help='Repository name (owner/repo)')
    parser.add_argument('--demo', action='store_true', help='Create single demo issue')
    parser.add_argument('--cleanup', nargs='+', type=int, help='Close specific issue numbers')
    parser.add_argument('--all', action='store_true', help='Create all test issues')
    
    args = parser.parse_args()
    
    creator = TestIssueCreator()
    
    if args.demo:
        # Create single demo issue
        issue = creator.create_demo_issue(args.repo)
        if issue:
            print(f"\n🎉 Demo issue created successfully!")
            print(f"   Issue #{issue['number']}: {issue['title']}")
            print(f"   URL: {issue['html_url']}")
            print(f"\n📝 Next steps:")
            print(f"   1. Configure webhook to point to your API Gateway URL")
            print(f"   2. Watch the agent process this issue")
            print(f"   3. Review the generated pull request")
        else:
            print("❌ Failed to create demo issue")
            sys.exit(1)
    
    elif args.cleanup:
        # Clean up test issues
        result = creator.cleanup_test_issues(args.repo, args.cleanup)
        if result.get('success'):
            print(f"✅ Cleaned up {result['closed_count']}/{result['total_issues']} issues")
        else:
            print(f"❌ Cleanup failed: {result.get('error')}")
            sys.exit(1)
    
    elif args.all:
        # Create all test issues
        issues = creator.create_test_issues(args.repo)
        print(f"\n🎉 Created {len(issues)} test issues!")
        for issue in issues:
            print(f"   #{issue['number']}: {issue['title']}")
    
    else:
        # Default: create demo issue
        issue = creator.create_demo_issue(args.repo)
        if issue:
            print(f"\n🎉 Demo issue created successfully!")
            print(f"   Issue #{issue['number']}: {issue['title']}")
            print(f"   URL: {issue['html_url']}")
        else:
            print("❌ Failed to create demo issue")
            sys.exit(1)

if __name__ == '__main__':
    main()
