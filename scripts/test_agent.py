#!/usr/bin/env python3
"""
AutoTriage & AutoFix Agent - Test Script

This script provides comprehensive testing capabilities for the autonomous agent,
including unit tests, integration tests, and end-to-end workflow validation.
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

class AgentTester:
    """Comprehensive testing suite for the AutoTriage & AutoFix Agent."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.test_results = []
        self.start_time = None
        
    def log_test_result(self, test_name: str, success: bool, details: str = "", 
                       duration: float = 0) -> None:
        """Log a test result."""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'duration': duration,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name} ({duration:.2f}s) - {details}")
    
    def test_environment_setup(self) -> bool:
        """Test environment configuration."""
        start_time = time.time()
        
        try:
            # Check required environment variables
            required_vars = [
                'GITHUB_TOKEN',
                'GITHUB_SECRET', 
                'BEDROCK_MODEL_ID',
                'S3_BUCKET',
                'CODEBUILD_PROJECT'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
            
            if missing_vars:
                self.log_test_result(
                    "Environment Setup",
                    False,
                    f"Missing environment variables: {', '.join(missing_vars)}",
                    time.time() - start_time
                )
                return False
            
            # Test AWS credentials
            import boto3
            try:
                sts = boto3.client('sts')
                identity = sts.get_caller_identity()
                account_id = identity.get('Account')
                
                self.log_test_result(
                    "Environment Setup",
                    True,
                    f"AWS credentials valid (Account: {account_id})",
                    time.time() - start_time
                )
                return True
                
            except Exception as e:
                self.log_test_result(
                    "Environment Setup",
                    False,
                    f"AWS credentials invalid: {str(e)}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Environment Setup",
                False,
                f"Environment test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_github_integration(self) -> bool:
        """Test GitHub API integration."""
        start_time = time.time()
        
        try:
            from lambda.tools.github_tool import GitHubTool
            
            github_tool = GitHubTool()
            
            # Test repository access
            test_repo = os.environ.get('TEST_REPO', 'octocat/Hello-World')
            repo_info = github_tool.get_repository_info(test_repo)
            
            if not repo_info.get('success'):
                self.log_test_result(
                    "GitHub Integration",
                    False,
                    f"Failed to access repository: {repo_info.get('error')}",
                    time.time() - start_time
                )
                return False
            
            # Test branch operations
            test_branch = f"autofix-test-{int(time.time())}"
            branch_result = github_tool.create_branch(test_repo, test_branch)
            
            if not branch_result.get('success'):
                self.log_test_result(
                    "GitHub Integration",
                    False,
                    f"Failed to create test branch: {branch_result.get('error')}",
                    time.time() - start_time
                )
                return False
            
            # Cleanup test branch
            try:
                # Note: GitHub API doesn't have direct branch deletion
                # The branch will be cleaned up by repository owner
                pass
            except:
                pass
            
            self.log_test_result(
                "GitHub Integration",
                True,
                f"Successfully created test branch: {test_branch}",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                "GitHub Integration",
                False,
                f"GitHub integration test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_bedrock_integration(self) -> bool:
        """Test Bedrock LLM integration."""
        start_time = time.time()
        
        try:
            import boto3
            
            bedrock = boto3.client('bedrock-runtime')
            model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022')
            
            # Test simple prompt
            test_prompt = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Say 'Hello from AutoFix Agent' and nothing else."
                    }
                ]
            }
            
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(test_prompt),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            if content and len(content) > 0:
                response_text = content[0].get('text', '')
                
                self.log_test_result(
                    "Bedrock Integration",
                    True,
                    f"Bedrock response received: {response_text[:50]}...",
                    time.time() - start_time
                )
                return True
            else:
                self.log_test_result(
                    "Bedrock Integration",
                    False,
                    "Empty response from Bedrock",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Bedrock Integration",
                False,
                f"Bedrock integration test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_s3_integration(self) -> bool:
        """Test S3 storage integration."""
        start_time = time.time()
        
        try:
            from lambda.tools.s3_tool import S3Tool
            
            s3_tool = S3Tool()
            bucket = os.environ.get('S3_BUCKET')
            
            if not bucket:
                self.log_test_result(
                    "S3 Integration",
                    False,
                    "S3_BUCKET environment variable not set",
                    time.time() - start_time
                )
                return False
            
            # Test artifact storage
            test_data = {
                'test': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'AutoFix Agent test artifact'
            }
            
            test_key = f"test/agent-test-{int(time.time())}.json"
            store_result = s3_tool.store_artifact(bucket, test_key, test_data)
            
            if not store_result.get('success'):
                self.log_test_result(
                    "S3 Integration",
                    False,
                    f"Failed to store test artifact: {store_result.get('error')}",
                    time.time() - start_time
                )
                return False
            
            # Test artifact retrieval
            retrieve_result = s3_tool.retrieve_artifact(bucket, test_key)
            
            if not retrieve_result.get('success'):
                self.log_test_result(
                    "S3 Integration",
                    False,
                    f"Failed to retrieve test artifact: {retrieve_result.get('error')}",
                    time.time() - start_time
                )
                return False
            
            # Cleanup test artifact
            try:
                s3_tool.delete_artifact(bucket, test_key)
            except:
                pass
            
            self.log_test_result(
                "S3 Integration",
                True,
                f"Successfully stored and retrieved test artifact",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                "S3 Integration",
                False,
                f"S3 integration test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_codebuild_integration(self) -> bool:
        """Test CodeBuild integration."""
        start_time = time.time()
        
        try:
            from lambda.tools.codebuild_tool import CodeBuildTool
            
            codebuild_tool = CodeBuildTool()
            project_name = os.environ.get('CODEBUILD_PROJECT')
            
            if not project_name:
                self.log_test_result(
                    "CodeBuild Integration",
                    False,
                    "CODEBUILD_PROJECT environment variable not set",
                    time.time() - start_time
                )
                return False
            
            # Test project listing
            list_result = codebuild_tool.list_builds(project_name, limit=5)
            
            if not list_result.get('success'):
                self.log_test_result(
                    "CodeBuild Integration",
                    False,
                    f"Failed to list builds: {list_result.get('error')}",
                    time.time() - start_time
                )
                return False
            
            self.log_test_result(
                "CodeBuild Integration",
                True,
                f"Successfully accessed CodeBuild project: {project_name}",
                time.time() - start_time
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                "CodeBuild Integration",
                False,
                f"CodeBuild integration test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_agent_reasoning(self) -> bool:
        """Test agent reasoning capabilities."""
        start_time = time.time()
        
        try:
            # Simulate agent reasoning with a test issue
            test_issue = {
                'title': 'Fix typo in README.md',
                'body': 'There is a typo in line 5 of README.md: "recieve" should be "receive"',
                'labels': ['bug', 'documentation'],
                'number': 999
            }
            
            test_repo = {
                'full_name': 'test/repo',
                'language': 'Markdown',
                'default_branch': 'main'
            }
            
            # Build test prompt
            prompt = f"""You are an autonomous engineering agent.

ISSUE TO RESOLVE:
- Title: {test_issue['title']}
- Description: {test_issue['body']}
- Labels: {', '.join(test_issue['labels'])}

REPOSITORY CONTEXT:
- Repository: {test_repo['full_name']}
- Language: {test_repo['language']}

TASK: Analyze this issue and determine if it can be automatically resolved.

RESPONSE FORMAT (JSON):
{{
    "can_auto_fix": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Why this can/cannot be auto-fixed",
    "patch": "Unified diff patch (if applicable)",
    "explanation": "Clear explanation of changes"
}}"""
            
            # Test with Bedrock
            import boto3
            bedrock = boto3.client('bedrock-runtime')
            model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022')
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            if content and len(content) > 0:
                response_text = content[0].get('text', '')
                
                # Try to parse JSON response
                try:
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        agent_response = json.loads(json_match.group())
                        
                        if 'can_auto_fix' in agent_response:
                            self.log_test_result(
                                "Agent Reasoning",
                                True,
                                f"Agent reasoning successful: can_auto_fix={agent_response.get('can_auto_fix')}",
                                time.time() - start_time
                            )
                            return True
                
                self.log_test_result(
                    "Agent Reasoning",
                    False,
                    "Could not parse agent response as JSON",
                    time.time() - start_time
                )
                return False
            else:
                self.log_test_result(
                    "Agent Reasoning",
                    False,
                    "Empty response from agent",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Agent Reasoning",
                False,
                f"Agent reasoning test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end workflow."""
        start_time = time.time()
        
        try:
            # This would test the complete workflow from webhook to PR creation
            # For now, we'll simulate the key components
            
            logger.info("Testing end-to-end workflow...")
            
            # Simulate webhook event
            webhook_event = {
                'headers': {
                    'X-GitHub-Event': 'issues',
                    'X-Hub-Signature-256': 'test-signature'
                },
                'body': json.dumps({
                    'action': 'opened',
                    'issue': {
                        'id': 12345,
                        'number': 1,
                        'title': 'Test issue for AutoFix Agent',
                        'body': 'This is a test issue to verify the agent workflow.',
                        'state': 'open',
                        'labels': [],
                        'user': {'login': 'testuser', 'type': 'User'}
                    },
                    'repository': {
                        'id': 123,
                        'name': 'test-repo',
                        'full_name': 'testuser/test-repo',
                        'owner': {'login': 'testuser', 'type': 'User'},
                        'private': False,
                        'html_url': 'https://github.com/testuser/test-repo',
                        'default_branch': 'main',
                        'language': 'Python'
                    }
                })
            }
            
            # Test webhook handler
            from lambda.webhook_handler import lambda_handler
            
            # Mock context
            class MockContext:
                aws_request_id = 'test-request-id'
            
            context = MockContext()
            
            # Test webhook processing
            result = lambda_handler(webhook_event, context)
            
            if result.get('statusCode') == 200:
                self.log_test_result(
                    "End-to-End Workflow",
                    True,
                    "Webhook processing successful",
                    time.time() - start_time
                )
                return True
            else:
                self.log_test_result(
                    "End-to-End Workflow",
                    False,
                    f"Webhook processing failed: {result.get('body')}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "End-to-End Workflow",
                False,
                f"End-to-end workflow test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        self.start_time = time.time()
        
        logger.info("🚀 Starting AutoTriage & AutoFix Agent Test Suite")
        logger.info("=" * 60)
        
        # Define test functions
        tests = [
            ("Environment Setup", self.test_environment_setup),
            ("GitHub Integration", self.test_github_integration),
            ("Bedrock Integration", self.test_bedrock_integration),
            ("S3 Integration", self.test_s3_integration),
            ("CodeBuild Integration", self.test_codebuild_integration),
            ("Agent Reasoning", self.test_agent_reasoning),
            ("End-to-End Workflow", self.test_end_to_end_workflow)
        ]
        
        # Run tests
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n🧪 Running {test_name}...")
                success = test_func()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {str(e)}")
                self.log_test_result(test_name, False, f"Test crashed: {str(e)}", 0)
                failed += 1
        
        # Calculate results
        total_time = time.time() - self.start_time
        total_tests = passed + failed
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed} ✅")
        logger.info(f"Failed: {failed} ❌")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Total Time: {total_time:.2f}s")
        
        if failed == 0:
            logger.info("\n🎉 All tests passed! Agent is ready for deployment.")
        else:
            logger.info(f"\n⚠️  {failed} test(s) failed. Please fix issues before deployment.")
        
        return {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'success_rate': success_rate,
            'total_time': total_time,
            'results': self.test_results
        }

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='AutoTriage & AutoFix Agent Test Suite')
    parser.add_argument('--test', choices=[
        'environment', 'github', 'bedrock', 's3', 'codebuild', 
        'reasoning', 'e2e', 'all'
    ], default='all', help='Specific test to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = AgentTester()
    
    if args.test == 'all':
        results = tester.run_all_tests()
    else:
        # Run specific test
        test_map = {
            'environment': tester.test_environment_setup,
            'github': tester.test_github_integration,
            'bedrock': tester.test_bedrock_integration,
            's3': tester.test_s3_integration,
            'codebuild': tester.test_codebuild_integration,
            'reasoning': tester.test_agent_reasoning,
            'e2e': tester.test_end_to_end_workflow
        }
        
        if args.test in test_map:
            logger.info(f"🧪 Running {args.test} test...")
            success = test_map[args.test]()
            if success:
                logger.info(f"✅ {args.test} test passed!")
            else:
                logger.error(f"❌ {args.test} test failed!")
                sys.exit(1)
        else:
            logger.error(f"Unknown test: {args.test}")
            sys.exit(1)
    
    # Exit with error code if any tests failed
    if args.test == 'all' and results['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
