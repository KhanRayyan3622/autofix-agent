"""
AutoTriage & AutoFix Agent - Agent Orchestrator

This Lambda function orchestrates the Bedrock AgentCore workflow for autonomous
GitHub issue resolution, including reasoning, tool execution, and result reporting.
"""

import json
import os
import logging
import boto3
from typing import Dict, Any, List
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
codebuild_client = boto3.client('codebuild')

# Environment variables
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022')
S3_BUCKET = os.environ.get('S3_BUCKET')
CODEBUILD_PROJECT = os.environ.get('CODEBUILD_PROJECT')
MEMORY_TABLE_NAME = os.environ.get('MEMORY_TABLE')

# Initialize DynamoDB table
memory_table = dynamodb.Table(MEMORY_TABLE_NAME) if MEMORY_TABLE_NAME else None

def get_agent_memory(issue_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve agent memory for similar issues to improve reasoning.
    
    Args:
        issue_id: GitHub issue ID
        
    Returns:
        List of similar past issues and their resolutions
    """
    if not memory_table:
        return []
    
    try:
        response = memory_table.query(
            KeyConditionExpression='issue_id = :issue_id',
            ExpressionAttributeValues={':issue_id': issue_id},
            Limit=5,
            ScanIndexForward=False
        )
        return response.get('Items', [])
    except Exception as e:
        logger.warning(f"Failed to retrieve agent memory: {e}")
        return []

def store_agent_memory(issue_id: str, resolution: Dict[str, Any]) -> None:
    """
    Store agent resolution in memory for future learning.
    
    Args:
        issue_id: GitHub issue ID
        resolution: Resolution details to store
    """
    if not memory_table:
        return
    
    try:
        memory_table.put_item(
            Item={
                'issue_id': issue_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resolution': resolution,
                'ttl': int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 60 * 60)  # 30 days
            }
        )
    except Exception as e:
        logger.warning(f"Failed to store agent memory: {e}")

def build_agent_prompt(issue_context: Dict[str, Any], repo_context: Dict[str, Any], 
                      memory: List[Dict[str, Any]]) -> str:
    """
    Build the agent prompt for Bedrock LLM reasoning.
    
    Args:
        issue_context: GitHub issue context
        repo_context: Repository context
        memory: Agent memory from similar issues
        
    Returns:
        Formatted prompt for the LLM
    """
    memory_context = ""
    if memory:
        memory_context = "\n\nSimilar past issues and resolutions:\n"
        for item in memory[:3]:  # Limit to 3 similar issues
            memory_context += f"- {item.get('resolution', {}).get('summary', 'N/A')}\n"
    
    prompt = f"""You are an autonomous engineering agent specialized in GitHub issue resolution.

REPOSITORY CONTEXT:
- Repository: {repo_context.get('full_name', 'Unknown')}
- Language: {repo_context.get('language', 'Unknown')}
- Default Branch: {repo_context.get('default_branch', 'main')}
- Private: {repo_context.get('private', False)}

ISSUE TO RESOLVE:
- Title: {issue_context.get('title', 'No title')}
- Description: {issue_context.get('body', 'No description')}
- Labels: {', '.join(issue_context.get('labels', []))}
- Issue Number: #{issue_context.get('number', 'Unknown')}

{memory_context}

AVAILABLE TOOLS:
1. github_tool: Create branches, apply patches, open pull requests
2. codebuild_tool: Run automated tests
3. s3_tool: Store artifacts and logs

TASK:
Analyze this issue and determine if it can be automatically resolved. If yes, provide:
1. A minimal code patch (unified diff format)
2. Test cases to validate the fix
3. A clear explanation of the changes

CONSTRAINTS:
- Only suggest fixes for trivial, well-defined issues
- Prefer minimal, safe changes
- Always include tests
- Avoid breaking changes
- If uncertain, suggest human review

RESPONSE FORMAT (JSON):
{{
    "can_auto_fix": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Why this can/cannot be auto-fixed",
    "patch": "Unified diff patch (if applicable)",
    "test_cases": ["Test case 1", "Test case 2"],
    "explanation": "Clear explanation of changes",
    "estimated_time": "Estimated time to implement",
    "risk_level": "low/medium/high"
}}

If can_auto_fix is false, provide detailed reasoning and suggest next steps for human intervention."""

    return prompt

def call_bedrock_agent(prompt: str) -> Dict[str, Any]:
    """
    Call Bedrock LLM for agent reasoning.
    
    Args:
        prompt: Agent prompt
        
    Returns:
        Agent response as dictionary
    """
    try:
        # Prepare the request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Call Bedrock
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract content from Claude's response
        content = response_body.get('content', [])
        if content and len(content) > 0:
            text_content = content[0].get('text', '')
            
            # Try to parse JSON from the response
            try:
                # Look for JSON in the response
                import re
                json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # Fallback: return structured response
                    return {
                        "can_auto_fix": False,
                        "confidence": 0.0,
                        "reasoning": "Could not parse agent response",
                        "error": text_content
                    }
            except json.JSONDecodeError:
                return {
                    "can_auto_fix": False,
                    "confidence": 0.0,
                    "reasoning": "Invalid JSON response from agent",
                    "raw_response": text_content
                }
        else:
            return {
                "can_auto_fix": False,
                "confidence": 0.0,
                "reasoning": "Empty response from agent"
            }
            
    except Exception as e:
        logger.error(f"Error calling Bedrock: {e}")
        return {
            "can_auto_fix": False,
            "confidence": 0.0,
            "reasoning": f"Bedrock API error: {str(e)}"
        }

def execute_agent_actions(agent_response: Dict[str, Any], issue_context: Dict[str, Any], 
                         repo_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the actions determined by the agent.
    
    Args:
        agent_response: Agent's reasoning and actions
        issue_context: GitHub issue context
        repo_context: Repository context
        
    Returns:
        Execution results
    """
    results = {
        "success": False,
        "actions_taken": [],
        "errors": [],
        "artifacts": []
    }
    
    if not agent_response.get("can_auto_fix", False):
        logger.info("Agent determined issue cannot be auto-fixed")
        return results
    
    try:
        # Import tools
        from tools.github_tool import GitHubTool
        from tools.codebuild_tool import CodeBuildTool
        from tools.s3_tool import S3Tool
        
        # Initialize tools
        github_tool = GitHubTool()
        codebuild_tool = CodeBuildTool()
        s3_tool = S3Tool()
        
        # Create branch
        branch_name = f"autofix-{issue_context.get('number', 'unknown')}-{int(datetime.now().timestamp())}"
        branch_result = github_tool.create_branch(
            repo_context.get('full_name'),
            branch_name,
            repo_context.get('default_branch', 'main')
        )
        
        if branch_result.get('success'):
            results["actions_taken"].append(f"Created branch: {branch_name}")
        else:
            results["errors"].append(f"Failed to create branch: {branch_result.get('error')}")
            return results
        
        # Apply patch if provided
        if agent_response.get("patch"):
            patch_result = github_tool.apply_patch(
                repo_context.get('full_name'),
                branch_name,
                agent_response.get("patch"),
                f"AutoFix: {issue_context.get('title', 'Issue resolution')}"
            )
            
            if patch_result.get('success'):
                results["actions_taken"].append("Applied code patch")
            else:
                results["errors"].append(f"Failed to apply patch: {patch_result.get('error')}")
                return results
        
        # Run tests
        if CODEBUILD_PROJECT:
            test_result = codebuild_tool.run_tests(
                CODEBUILD_PROJECT,
                repo_context.get('full_name'),
                branch_name
            )
            
            if test_result.get('success'):
                results["actions_taken"].append("Triggered automated tests")
                results["test_build_id"] = test_result.get('build_id')
            else:
                results["errors"].append(f"Failed to run tests: {test_result.get('error')}")
        
        # Create pull request
        pr_result = github_tool.create_pull_request(
            repo_context.get('full_name'),
            branch_name,
            f"[AutoFix] {issue_context.get('title', 'Issue resolution')}",
            f"""## 🤖 AutoFix Agent Resolution

**Issue:** #{issue_context.get('number')}
**Confidence:** {agent_response.get('confidence', 0):.1%}
**Reasoning:** {agent_response.get('reasoning', 'N/A')}

### Changes Made
{agent_response.get('explanation', 'N/A')}

### Test Cases
{chr(10).join(f"- {case}" for case in agent_response.get('test_cases', []))}

### Risk Assessment
- **Level:** {agent_response.get('risk_level', 'unknown').title()}
- **Estimated Time:** {agent_response.get('estimated_time', 'N/A')}

---
*This PR was automatically generated by the AutoTriage & AutoFix Agent.*
""",
            repo_context.get('default_branch', 'main')
        )
        
        if pr_result.get('success'):
            results["actions_taken"].append("Created pull request")
            results["pr_url"] = pr_result.get('pr_url')
            results["success"] = True
        else:
            results["errors"].append(f"Failed to create PR: {pr_result.get('error')}")
        
        # Store artifacts in S3
        if S3_BUCKET:
            artifact_data = {
                "issue_context": issue_context,
                "agent_response": agent_response,
                "execution_results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            artifact_key = f"resolutions/{issue_context.get('id')}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            s3_result = s3_tool.store_artifact(S3_BUCKET, artifact_key, artifact_data)
            
            if s3_result.get('success'):
                results["artifacts"].append(f"s3://{S3_BUCKET}/{artifact_key}")
            else:
                results["errors"].append(f"Failed to store artifact: {s3_result.get('error')}")
        
    except Exception as e:
        logger.error(f"Error executing agent actions: {e}")
        results["errors"].append(f"Execution error: {str(e)}")
    
    return results

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for agent orchestration.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        dict: Processing results
    """
    try:
        # Extract event data
        issue_context = event.get('issue', {})
        repo_context = event.get('repository', {})
        action = event.get('action', '')
        
        logger.info(f"Processing issue #{issue_context.get('number')} in {repo_context.get('full_name')}")
        
        # Get agent memory for similar issues
        memory = get_agent_memory(str(issue_context.get('id', '')))
        
        # Build agent prompt
        prompt = build_agent_prompt(issue_context, repo_context, memory)
        
        # Call Bedrock agent
        logger.info("Calling Bedrock agent for reasoning...")
        agent_response = call_bedrock_agent(prompt)
        
        logger.info(f"Agent response: {agent_response.get('can_auto_fix', False)} "
                   f"(confidence: {agent_response.get('confidence', 0):.1%})")
        
        # Execute agent actions if auto-fix is possible
        execution_results = {}
        if agent_response.get('can_auto_fix', False):
            logger.info("Executing agent actions...")
            execution_results = execute_agent_actions(agent_response, issue_context, repo_context)
        else:
            logger.info("Agent determined issue cannot be auto-fixed")
            execution_results = {
                "success": False,
                "reason": agent_response.get('reasoning', 'Issue cannot be auto-fixed'),
                "confidence": agent_response.get('confidence', 0)
            }
        
        # Store resolution in memory
        resolution_data = {
            "issue_id": issue_context.get('id'),
            "issue_number": issue_context.get('number'),
            "can_auto_fix": agent_response.get('can_auto_fix', False),
            "confidence": agent_response.get('confidence', 0),
            "reasoning": agent_response.get('reasoning', ''),
            "execution_success": execution_results.get('success', False),
            "actions_taken": execution_results.get('actions_taken', []),
            "errors": execution_results.get('errors', [])
        }
        
        store_agent_memory(str(issue_context.get('id', '')), resolution_data)
        
        # Log results
        logger.info(f"Processing complete for issue #{issue_context.get('number')}: "
                   f"success={execution_results.get('success', False)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'issue_number': issue_context.get('number'),
                'repository': repo_context.get('full_name'),
                'agent_response': agent_response,
                'execution_results': execution_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in agent orchestrator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Agent orchestration failed',
                'message': str(e)
            })
        }
