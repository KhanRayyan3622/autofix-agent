"""
AutoTriage & AutoFix Agent - CodeBuild Tool

This module provides AWS CodeBuild integration for running automated tests
as part of the autonomous agent workflow.
"""

import os
import json
import logging
import boto3
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

class CodeBuildTool:
    """AWS CodeBuild integration tool for automated testing."""
    
    def __init__(self):
        """Initialize CodeBuild tool with AWS credentials."""
        self.client = boto3.client('codebuild')
        self.logs_client = boto3.client('logs')
        
    def start_build(self, project_name: str, source_version: str = None, 
                   environment_variables: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Start a CodeBuild project build.
        
        Args:
            project_name: Name of the CodeBuild project
            source_version: Git commit SHA or branch to build
            environment_variables: Environment variables for the build
            
        Returns:
            Build start result
        """
        try:
            # Prepare build parameters
            build_params = {
                'projectName': project_name
            }
            
            if source_version:
                build_params['sourceVersion'] = source_version
            
            if environment_variables:
                build_params['environmentVariablesOverride'] = [
                    {
                        'name': key,
                        'value': value,
                        'type': 'PLAINTEXT'
                    }
                    for key, value in environment_variables.items()
                ]
            
            # Start the build
            response = self.client.start_build(**build_params)
            
            build_id = response['build']['id']
            logger.info(f"Started CodeBuild project {project_name}: {build_id}")
            
            return {
                'success': True,
                'build_id': build_id,
                'build_arn': response['build']['arn'],
                'build_status': response['build']['buildStatus'],
                'start_time': response['build']['startTime'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting CodeBuild build: {e}")
            return {
                'success': False,
                'error': f'Failed to start build: {str(e)}'
            }
    
    def get_build_status(self, build_id: str) -> Dict[str, Any]:
        """
        Get the status of a CodeBuild build.
        
        Args:
            build_id: CodeBuild build ID
            
        Returns:
            Build status information
        """
        try:
            response = self.client.batch_get_builds(ids=[build_id])
            
            if not response['builds']:
                return {
                    'success': False,
                    'error': f'Build {build_id} not found'
                }
            
            build = response['builds'][0]
            
            return {
                'success': True,
                'build_id': build_id,
                'status': build['buildStatus'],
                'phase': build.get('currentPhase', 'UNKNOWN'),
                'start_time': build.get('startTime'),
                'end_time': build.get('endTime'),
                'duration': self._calculate_duration(build.get('startTime'), build.get('endTime')),
                'logs': build.get('logs', {}),
                'artifacts': build.get('artifacts', {}),
                'environment': build.get('environment', {}),
                'source': build.get('source', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting build status: {e}")
            return {
                'success': False,
                'error': f'Failed to get build status: {str(e)}'
            }
    
    def get_build_logs(self, build_id: str) -> Dict[str, Any]:
        """
        Get the logs for a CodeBuild build.
        
        Args:
            build_id: CodeBuild build ID
            
        Returns:
            Build logs
        """
        try:
            # Get build details first
            build_status = self.get_build_status(build_id)
            if not build_status.get('success'):
                return build_status
            
            logs_info = build_status.get('logs', {})
            log_group = logs_info.get('groupName')
            log_stream = logs_info.get('streamName')
            
            if not log_group or not log_stream:
                return {
                    'success': False,
                    'error': 'No logs available for this build'
                }
            
            # Get logs from CloudWatch
            response = self.logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                startFromHead=True
            )
            
            # Format log events
            log_events = []
            for event in response.get('events', []):
                log_events.append({
                    'timestamp': event['timestamp'],
                    'message': event['message'],
                    'ingestion_time': event.get('ingestionTime')
                })
            
            return {
                'success': True,
                'build_id': build_id,
                'log_group': log_group,
                'log_stream': log_stream,
                'events': log_events,
                'next_token': response.get('nextToken')
            }
            
        except Exception as e:
            logger.error(f"Error getting build logs: {e}")
            return {
                'success': False,
                'error': f'Failed to get build logs: {str(e)}'
            }
    
    def wait_for_build_completion(self, build_id: str, timeout_minutes: int = 30) -> Dict[str, Any]:
        """
        Wait for a CodeBuild build to complete.
        
        Args:
            build_id: CodeBuild build ID
            timeout_minutes: Maximum time to wait in minutes
            
        Returns:
            Final build result
        """
        import time
        
        start_time = datetime.now(timezone.utc)
        timeout_seconds = timeout_minutes * 60
        
        logger.info(f"Waiting for build {build_id} to complete (timeout: {timeout_minutes} minutes)")
        
        while True:
            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > timeout_seconds:
                return {
                    'success': False,
                    'error': f'Build timeout after {timeout_minutes} minutes',
                    'build_id': build_id,
                    'status': 'TIMEOUT'
                }
            
            # Get build status
            status_result = self.get_build_status(build_id)
            if not status_result.get('success'):
                return status_result
            
            status = status_result['status']
            phase = status_result.get('phase', 'UNKNOWN')
            
            logger.info(f"Build {build_id} status: {status} (phase: {phase})")
            
            # Check if build is complete
            if status in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMED_OUT']:
                return {
                    'success': status == 'SUCCEEDED',
                    'build_id': build_id,
                    'status': status,
                    'phase': phase,
                    'duration': status_result.get('duration'),
                    'start_time': status_result.get('start_time'),
                    'end_time': status_result.get('end_time')
                }
            
            # Wait before checking again
            time.sleep(10)
    
    def run_tests(self, project_name: str, repo_name: str, branch_name: str, 
                 commit_sha: str = None) -> Dict[str, Any]:
        """
        Run tests for a specific repository and branch.
        
        Args:
            project_name: CodeBuild project name
            repo_name: Repository name in format 'owner/repo'
            branch_name: Branch name to test
            commit_sha: Specific commit SHA to test
            
        Returns:
            Test execution result
        """
        try:
            # Prepare environment variables
            env_vars = {
                'GITHUB_REPO': repo_name,
                'GITHUB_BRANCH': branch_name,
                'TEST_BRANCH': branch_name
            }
            
            if commit_sha:
                env_vars['GITHUB_SHA'] = commit_sha
            
            # Start the build
            start_result = self.start_build(
                project_name=project_name,
                source_version=commit_sha or f'refs/heads/{branch_name}',
                environment_variables=env_vars
            )
            
            if not start_result.get('success'):
                return start_result
            
            build_id = start_result['build_id']
            logger.info(f"Started test build {build_id} for {repo_name}#{branch_name}")
            
            # Wait for completion
            completion_result = self.wait_for_build_completion(build_id)
            
            # Get logs for detailed results
            logs_result = self.get_build_logs(build_id)
            
            return {
                'success': completion_result.get('success', False),
                'build_id': build_id,
                'status': completion_result.get('status'),
                'duration': completion_result.get('duration'),
                'logs': logs_result.get('events', []) if logs_result.get('success') else [],
                'logs_error': logs_result.get('error') if not logs_result.get('success') else None
            }
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                'success': False,
                'error': f'Test execution failed: {str(e)}'
            }
    
    def get_build_artifacts(self, build_id: str) -> Dict[str, Any]:
        """
        Get artifacts from a completed build.
        
        Args:
            build_id: CodeBuild build ID
            
        Returns:
            Build artifacts information
        """
        try:
            build_status = self.get_build_status(build_id)
            if not build_status.get('success'):
                return build_status
            
            artifacts = build_status.get('artifacts', {})
            
            return {
                'success': True,
                'build_id': build_id,
                'artifacts': artifacts,
                'artifact_location': artifacts.get('location'),
                'artifact_identifier': artifacts.get('artifactIdentifier')
            }
            
        except Exception as e:
            logger.error(f"Error getting build artifacts: {e}")
            return {
                'success': False,
                'error': f'Failed to get artifacts: {str(e)}'
            }
    
    def _calculate_duration(self, start_time, end_time) -> Optional[str]:
        """
        Calculate build duration.
        
        Args:
            start_time: Build start time
            end_time: Build end time
            
        Returns:
            Duration string or None
        """
        if not start_time or not end_time:
            return None
        
        try:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            duration = end_time - start_time
            total_seconds = int(duration.total_seconds())
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            logger.warning(f"Error calculating duration: {e}")
            return None
    
    def list_builds(self, project_name: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        List recent builds for a project.
        
        Args:
            project_name: CodeBuild project name (optional)
            limit: Maximum number of builds to return
            
        Returns:
            List of builds
        """
        try:
            list_params = {
                'sortOrder': 'DESCENDING',
                'maxResults': min(limit, 100)
            }
            
            if project_name:
                list_params['projectName'] = project_name
            
            response = self.client.list_builds(**list_params)
            
            # Get detailed information for each build
            build_ids = response.get('ids', [])
            if not build_ids:
                return {
                    'success': True,
                    'builds': [],
                    'count': 0
                }
            
            builds_result = self.client.batch_get_builds(ids=build_ids)
            builds = builds_result.get('builds', [])
            
            # Format build information
            formatted_builds = []
            for build in builds:
                formatted_builds.append({
                    'id': build['id'],
                    'status': build['buildStatus'],
                    'phase': build.get('currentPhase', 'UNKNOWN'),
                    'start_time': build.get('startTime'),
                    'end_time': build.get('endTime'),
                    'duration': self._calculate_duration(build.get('startTime'), build.get('endTime')),
                    'project_name': build.get('projectName'),
                    'source_version': build.get('sourceVersion')
                })
            
            return {
                'success': True,
                'builds': formatted_builds,
                'count': len(formatted_builds)
            }
            
        except Exception as e:
            logger.error(f"Error listing builds: {e}")
            return {
                'success': False,
                'error': f'Failed to list builds: {str(e)}'
            }
