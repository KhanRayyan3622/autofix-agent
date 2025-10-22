"""
AutoTriage & AutoFix Agent - GitHub Tool

This module provides GitHub API integration for the autonomous agent,
including branch creation, patch application, and pull request management.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class GitHubTool:
    """GitHub API integration tool for autonomous agent operations."""
    
    def __init__(self):
        """Initialize GitHub tool with API credentials."""
        self.token = os.environ.get('GITHUB_TOKEN')
        self.api_base = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AutoTriage-AutoFix-Agent/1.0'
        }
        
        if not self.token:
            logger.error("GITHUB_TOKEN not configured")
            raise ValueError("GitHub token is required")
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated GitHub API request.
        
        Args:
            method: HTTP method
            url: API endpoint URL
            **kwargs: Additional request parameters
            
        Returns:
            API response as dictionary
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                logger.warning("GitHub API rate limit exceeded")
                return {
                    'success': False,
                    'error': 'GitHub API rate limit exceeded',
                    'retry_after': response.headers.get('X-RateLimit-Reset', 0)
                }
            
            # Handle other errors
            if response.status_code >= 400:
                logger.error(f"GitHub API error {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'GitHub API error: {response.status_code} - {response.text}'
                }
            
            return {
                'success': True,
                'data': response.json() if response.content else {},
                'status_code': response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """
        Get repository information.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            
        Returns:
            Repository information
        """
        url = f"{self.api_base}/repos/{repo_name}"
        return self._make_request('GET', url)
    
    def get_default_branch(self, repo_name: str) -> Optional[str]:
        """
        Get the default branch of a repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            
        Returns:
            Default branch name or None
        """
        result = self.get_repository_info(repo_name)
        if result.get('success'):
            return result['data'].get('default_branch', 'main')
        return None
    
    def get_branch_sha(self, repo_name: str, branch: str) -> Optional[str]:
        """
        Get the SHA of a specific branch.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            branch: Branch name
            
        Returns:
            Branch SHA or None
        """
        url = f"{self.api_base}/repos/{repo_name}/git/refs/heads/{branch}"
        result = self._make_request('GET', url)
        
        if result.get('success'):
            return result['data'].get('object', {}).get('sha')
        return None
    
    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = None) -> Dict[str, Any]:
        """
        Create a new branch from the base branch.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            branch_name: Name of the new branch
            base_branch: Base branch to create from (defaults to default branch)
            
        Returns:
            Creation result
        """
        try:
            # Get base branch if not provided
            if not base_branch:
                base_branch = self.get_default_branch(repo_name)
                if not base_branch:
                    return {
                        'success': False,
                        'error': 'Could not determine default branch'
                    }
            
            # Get base branch SHA
            base_sha = self.get_branch_sha(repo_name, base_branch)
            if not base_sha:
                return {
                    'success': False,
                    'error': f'Could not get SHA for base branch {base_branch}'
                }
            
            # Create new branch
            url = f"{self.api_base}/repos/{repo_name}/git/refs"
            data = {
                'ref': f'refs/heads/{branch_name}',
                'sha': base_sha
            }
            
            result = self._make_request('POST', url, json=data)
            
            if result.get('success'):
                logger.info(f"Created branch {branch_name} from {base_branch}")
                return {
                    'success': True,
                    'branch_name': branch_name,
                    'sha': result['data'].get('object', {}).get('sha')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return {
                'success': False,
                'error': f'Branch creation failed: {str(e)}'
            }
    
    def get_file_content(self, repo_name: str, file_path: str, branch: str = None) -> Dict[str, Any]:
        """
        Get the content of a file from the repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path to the file
            branch: Branch to read from (defaults to default branch)
            
        Returns:
            File content result
        """
        if not branch:
            branch = self.get_default_branch(repo_name)
        
        url = f"{self.api_base}/repos/{repo_name}/contents/{file_path}"
        params = {'ref': branch} if branch else {}
        
        result = self._make_request('GET', url, params=params)
        
        if result.get('success'):
            # Decode base64 content
            import base64
            content = result['data'].get('content', '')
            if content:
                try:
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    return {
                        'success': True,
                        'content': decoded_content,
                        'sha': result['data'].get('sha'),
                        'size': result['data'].get('size')
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Failed to decode file content: {str(e)}'
                    }
        
        return result
    
    def update_file(self, repo_name: str, file_path: str, content: str, 
                   commit_message: str, branch: str, sha: str = None) -> Dict[str, Any]:
        """
        Update a file in the repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path to the file
            content: New file content
            commit_message: Commit message
            branch: Branch to update
            sha: File SHA (required for updates)
            
        Returns:
            Update result
        """
        try:
            # Get file SHA if not provided
            if not sha:
                file_info = self.get_file_content(repo_name, file_path, branch)
                if not file_info.get('success'):
                    return {
                        'success': False,
                        'error': f'Could not get file SHA: {file_info.get("error")}'
                    }
                sha = file_info.get('sha')
            
            # Encode content
            import base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Update file
            url = f"{self.api_base}/repos/{repo_name}/contents/{file_path}"
            data = {
                'message': commit_message,
                'content': encoded_content,
                'sha': sha,
                'branch': branch
            }
            
            result = self._make_request('PUT', url, json=data)
            
            if result.get('success'):
                logger.info(f"Updated file {file_path} in branch {branch}")
                return {
                    'success': True,
                    'commit_sha': result['data'].get('commit', {}).get('sha'),
                    'file_sha': result['data'].get('content', {}).get('sha')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error updating file: {e}")
            return {
                'success': False,
                'error': f'File update failed: {str(e)}'
            }
    
    def create_file(self, repo_name: str, file_path: str, content: str, 
                   commit_message: str, branch: str) -> Dict[str, Any]:
        """
        Create a new file in the repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path to the new file
            content: File content
            commit_message: Commit message
            branch: Branch to create file in
            
        Returns:
            Creation result
        """
        try:
            # Encode content
            import base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Create file
            url = f"{self.api_base}/repos/{repo_name}/contents/{file_path}"
            data = {
                'message': commit_message,
                'content': encoded_content,
                'branch': branch
            }
            
            result = self._make_request('PUT', url, json=data)
            
            if result.get('success'):
                logger.info(f"Created file {file_path} in branch {branch}")
                return {
                    'success': True,
                    'commit_sha': result['data'].get('commit', {}).get('sha'),
                    'file_sha': result['data'].get('content', {}).get('sha')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return {
                'success': False,
                'error': f'File creation failed: {str(e)}'
            }
    
    def apply_patch(self, repo_name: str, branch: str, patch_content: str, 
                   commit_message: str) -> Dict[str, Any]:
        """
        Apply a patch to the repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            branch: Branch to apply patch to
            patch_content: Unified diff patch content
            commit_message: Commit message
            
        Returns:
            Patch application result
        """
        try:
            # Parse patch to extract file changes
            patch_files = self._parse_patch(patch_content)
            
            if not patch_files:
                return {
                    'success': False,
                    'error': 'No valid file changes found in patch'
                }
            
            results = []
            for file_path, file_content in patch_files.items():
                if file_content is None:
                    # File deletion
                    result = self._delete_file(repo_name, file_path, commit_message, branch)
                else:
                    # File creation or update
                    file_info = self.get_file_content(repo_name, file_path, branch)
                    if file_info.get('success'):
                        # Update existing file
                        result = self.update_file(
                            repo_name, file_path, file_content, 
                            commit_message, branch, file_info.get('sha')
                        )
                    else:
                        # Create new file
                        result = self.create_file(
                            repo_name, file_path, file_content, 
                            commit_message, branch
                        )
                
                results.append({
                    'file_path': file_path,
                    'success': result.get('success', False),
                    'error': result.get('error')
                })
            
            # Check if all operations succeeded
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            
            return {
                'success': success_count == total_count,
                'files_processed': total_count,
                'files_successful': success_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error applying patch: {e}")
            return {
                'success': False,
                'error': f'Patch application failed: {str(e)}'
            }
    
    def _parse_patch(self, patch_content: str) -> Dict[str, str]:
        """
        Parse unified diff patch to extract file changes.
        
        Args:
            patch_content: Unified diff patch content
            
        Returns:
            Dictionary mapping file paths to new content
        """
        files = {}
        current_file = None
        current_content = []
        in_hunk = False
        
        for line in patch_content.split('\n'):
            if line.startswith('--- a/'):
                # Start of file section
                current_file = line[6:]  # Remove '--- a/'
                current_content = []
                in_hunk = False
            elif line.startswith('+++ b/'):
                # File destination
                if current_file:
                    files[current_file] = None  # Will be updated with content
                in_hunk = True
            elif in_hunk and current_file:
                if line.startswith('+') and not line.startswith('+++'):
                    # Added line
                    current_content.append(line[1:])
                elif line.startswith(' ') or line.startswith('-'):
                    # Context or removed line
                    if line.startswith(' '):
                        current_content.append(line[1:])
                elif line.startswith('@@'):
                    # Hunk header - continue
                    continue
                else:
                    # End of hunk
                    if current_content:
                        files[current_file] = '\n'.join(current_content)
        
        return files
    
    def _delete_file(self, repo_name: str, file_path: str, commit_message: str, branch: str) -> Dict[str, Any]:
        """
        Delete a file from the repository.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path to the file to delete
            commit_message: Commit message
            branch: Branch to delete from
            
        Returns:
            Deletion result
        """
        try:
            # Get file SHA first
            file_info = self.get_file_content(repo_name, file_path, branch)
            if not file_info.get('success'):
                return {
                    'success': False,
                    'error': f'Could not get file SHA for deletion: {file_info.get("error")}'
                }
            
            # Delete file
            url = f"{self.api_base}/repos/{repo_name}/contents/{file_path}"
            data = {
                'message': commit_message,
                'sha': file_info.get('sha'),
                'branch': branch
            }
            
            result = self._make_request('DELETE', url, json=data)
            
            if result.get('success'):
                logger.info(f"Deleted file {file_path} from branch {branch}")
                return {
                    'success': True,
                    'commit_sha': result['data'].get('commit', {}).get('sha')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {
                'success': False,
                'error': f'File deletion failed: {str(e)}'
            }
    
    def create_pull_request(self, repo_name: str, head_branch: str, title: str, 
                          body: str, base_branch: str = None) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            head_branch: Source branch
            title: PR title
            body: PR description
            base_branch: Target branch (defaults to default branch)
            
        Returns:
            PR creation result
        """
        try:
            if not base_branch:
                base_branch = self.get_default_branch(repo_name)
            
            url = f"{self.api_base}/repos/{repo_name}/pulls"
            data = {
                'title': title,
                'body': body,
                'head': head_branch,
                'base': base_branch
            }
            
            result = self._make_request('POST', url, json=data)
            
            if result.get('success'):
                pr_data = result['data']
                logger.info(f"Created PR #{pr_data.get('number')}: {title}")
                return {
                    'success': True,
                    'pr_number': pr_data.get('number'),
                    'pr_url': pr_data.get('html_url'),
                    'pr_api_url': pr_data.get('url')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return {
                'success': False,
                'error': f'PR creation failed: {str(e)}'
            }
    
    def add_labels_to_issue(self, repo_name: str, issue_number: int, labels: list) -> Dict[str, Any]:
        """
        Add labels to an issue.
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            issue_number: Issue number
            labels: List of label names
            
        Returns:
            Label addition result
        """
        try:
            url = f"{self.api_base}/repos/{repo_name}/issues/{issue_number}/labels"
            data = {'labels': labels}
            
            result = self._make_request('POST', url, json=data)
            
            if result.get('success'):
                logger.info(f"Added labels {labels} to issue #{issue_number}")
                return {
                    'success': True,
                    'labels': result['data']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return {
                'success': False,
                'error': f'Label addition failed: {str(e)}'
            }
