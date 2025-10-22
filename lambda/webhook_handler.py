"""
AutoTriage & AutoFix Agent - GitHub Webhook Handler

This Lambda function receives GitHub webhook events and triggers the agent orchestrator
for autonomous issue resolution.
"""

import json
import hmac
import hashlib
import os
import logging
import boto3
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
lambda_client = boto3.client('lambda')

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature to ensure authenticity.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: GitHub webhook secret
        
    Returns:
        bool: True if signature is valid
    """
    if not signature or not secret:
        logger.warning("Missing signature or secret")
        return False
    
    # Remove 'sha256=' prefix if present
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures securely
    return hmac.compare_digest(signature, expected_signature)

def extract_issue_context(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant context from GitHub issue for agent processing.
    
    Args:
        issue_data: GitHub issue object from webhook
        
    Returns:
        dict: Structured issue context
    """
    return {
        'id': issue_data.get('id'),
        'number': issue_data.get('number'),
        'title': issue_data.get('title', ''),
        'body': issue_data.get('body', ''),
        'state': issue_data.get('state'),
        'labels': [label.get('name', '') for label in issue_data.get('labels', [])],
        'assignee': issue_data.get('assignee'),
        'created_at': issue_data.get('created_at'),
        'updated_at': issue_data.get('updated_at'),
        'user': {
            'login': issue_data.get('user', {}).get('login', ''),
            'type': issue_data.get('user', {}).get('type', '')
        }
    }

def extract_repository_context(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract repository context for agent processing.
    
    Args:
        repo_data: GitHub repository object from webhook
        
    Returns:
        dict: Structured repository context
    """
    return {
        'id': repo_data.get('id'),
        'name': repo_data.get('name'),
        'full_name': repo_data.get('full_name'),
        'owner': {
            'login': repo_data.get('owner', {}).get('login', ''),
            'type': repo_data.get('owner', {}).get('type', '')
        },
        'private': repo_data.get('private', False),
        'html_url': repo_data.get('html_url'),
        'clone_url': repo_data.get('clone_url'),
        'default_branch': repo_data.get('default_branch', 'main'),
        'language': repo_data.get('language'),
        'topics': repo_data.get('topics', [])
    }

def should_process_issue(issue_context: Dict[str, Any]) -> bool:
    """
    Determine if an issue should be processed by the agent.
    
    Args:
        issue_context: Extracted issue context
        
    Returns:
        bool: True if issue should be processed
    """
    # Skip if issue is already assigned to a human
    if issue_context.get('assignee'):
        logger.info(f"Issue #{issue_context.get('number')} already assigned, skipping")
        return False
    
    # Skip if issue is closed
    if issue_context.get('state') == 'closed':
        logger.info(f"Issue #{issue_context.get('number')} is closed, skipping")
        return False
    
    # Skip if issue has specific labels that indicate human intervention needed
    skip_labels = ['needs-review', 'complex', 'breaking-change', 'security']
    issue_labels = issue_context.get('labels', [])
    if any(label in issue_labels for label in skip_labels):
        logger.info(f"Issue #{issue_context.get('number')} has skip labels, skipping")
        return False
    
    # Process if issue is open and doesn't have skip labels
    return issue_context.get('state') == 'open'

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for GitHub webhook events.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        dict: HTTP response
    """
    try:
        # Extract request details
        headers = event.get('headers', {})
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        # Handle base64 encoded body
        if is_base64:
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        # Verify GitHub signature
        github_secret = os.environ.get('GITHUB_SECRET')
        signature = headers.get('X-Hub-Signature-256', '')
        
        if github_secret and not verify_github_signature(
            body.encode('utf-8') if isinstance(body, str) else body,
            signature,
            github_secret
        ):
            logger.warning("Invalid GitHub signature")
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # Parse webhook payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON'})
            }
        
        # Extract event information
        event_type = headers.get('X-GitHub-Event', '')
        action = payload.get('action', '')
        
        logger.info(f"Received GitHub event: {event_type}.{action}")
        
        # Only process issue events
        if event_type != 'issues':
            logger.info(f"Event type {event_type} not supported, skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Event type not supported'})
            }
        
        # Only process specific issue actions
        if action not in ['opened', 'reopened', 'edited']:
            logger.info(f"Issue action {action} not supported, skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Action not supported'})
            }
        
        # Extract issue and repository context
        issue_data = payload.get('issue', {})
        repo_data = payload.get('repository', {})
        
        if not issue_data or not repo_data:
            logger.error("Missing issue or repository data")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required data'})
            }
        
        issue_context = extract_issue_context(issue_data)
        repo_context = extract_repository_context(repo_data)
        
        # Check if issue should be processed
        if not should_process_issue(issue_context):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Issue not eligible for processing'})
            }
        
        # Prepare orchestrator payload
        orchestrator_payload = {
            'event_type': event_type,
            'action': action,
            'issue': issue_context,
            'repository': repo_context,
            'timestamp': context.aws_request_id
        }
        
        # Get orchestrator function name
        orchestrator_function = os.environ.get('ORCHESTRATOR_FUNCTION')
        if not orchestrator_function:
            logger.error("ORCHESTRATOR_FUNCTION not configured")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Configuration error'})
            }
        
        # Invoke agent orchestrator asynchronously
        logger.info(f"Invoking orchestrator for issue #{issue_context.get('number')}")
        
        response = lambda_client.invoke(
            FunctionName=orchestrator_function,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(orchestrator_payload)
        )
        
        logger.info(f"Orchestrator invoked successfully: {response.get('StatusCode')}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Issue queued for processing',
                'issue_number': issue_context.get('number'),
                'repository': repo_context.get('full_name')
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
