"""Generic subscription management with GitHub integration."""

import os
from pathlib import Path
from typing import Optional

from .models import GitHubConfig, GitHubOperationResult, GitHubOperationStatus
from .repository_manager import RepositoryManager, PullRequestManager
from ..core.logging import get_logger


class SubscriptionManager:
    """Manages subscription files with GitHub integration."""
    
    def __init__(self, github_config: GitHubConfig, subs_file_path: str):
        """Initialize the subscription manager.
        
        Args:
            github_config: GitHub configuration
            subs_file_path: Absolute path to subscriptions file
        """
        self.github_config = github_config
        self.subs_file_path = subs_file_path
        self.logger = get_logger(__name__)
        
        self.repo_manager = RepositoryManager(github_config)
        self.pr_manager = PullRequestManager(github_config)
    
    def setup_repository(self) -> GitHubOperationResult:
        """Set up the repository for subscription management.
        
        Returns:
            Result of the repository setup operation
        """
        self.logger.info("Setting up repository for subscription management")
        return self.repo_manager.bootstrap_repository()
    
    def get_subscriptions_file_path(self) -> Path:
        """Get the full path to the subscriptions file.
        
        Returns:
            Path to the subscriptions file
        """
        return Path(self.subs_file_path)
    
    def validate_subscriptions_file(self) -> bool:
        """Validate that the subscriptions file exists and is accessible.
        
        Returns:
            True if the file exists and is readable, False otherwise
        """
        subs_file = self.get_subscriptions_file_path()
        
        if not subs_file.exists():
            self.logger.error(f"Subscriptions file not found: {subs_file}")
            return False
        
        if not subs_file.is_file():
            self.logger.error(f"Subscriptions path is not a file: {subs_file}")
            return False
        
        try:
            # Test if file is readable
            with open(subs_file, 'r') as f:
                f.read(1)  # Read just one character to test accessibility
            return True
        except Exception as e:
            self.logger.error(f"Cannot read subscriptions file {subs_file}: {e}")
            return False
    
    def finalize_subscription_updates(self, 
                                    commit_message: Optional[str] = None,
                                    pr_title: Optional[str] = None,
                                    pr_body: Optional[str] = None) -> GitHubOperationResult:
        """Finalize subscription updates by creating a PR.
        
        Args:
            commit_message: Custom commit message (optional)
            pr_title: Custom PR title (optional)
            pr_body: Custom PR body (optional)
            
        Returns:
            Result of the finalization operation
        """
        self.logger.info("Finalizing subscription updates")
        
        # Commit and push changes
        commit_result = self.repo_manager.commit_and_push_changes(commit_message)
        
        if not commit_result.success:
            return commit_result
        
        if commit_result.status == GitHubOperationStatus.SKIPPED:
            # No changes to commit
            return commit_result
        
        # Create pull request
        pr_result = self.pr_manager.create_pull_request(
            branch_name=commit_result.branch_name,
            pr_title=pr_title,
            pr_body=pr_body
        )
        
        return pr_result
    
    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.logger.info("Cleaning up subscription manager resources")
        self.repo_manager.cleanup_repository()
    
    @classmethod
    def create_from_config(cls, repo_url: str, token: str, 
                          subs_file_path: str,
                          auto_merge: bool = False,
                          temp_repo_dir: Optional[str] = None) -> 'SubscriptionManager':
        """Create a SubscriptionManager from configuration values.
        
        Args:
            repo_url: GitHub repository URL
            token: GitHub access token
            subs_file_path: Absolute path to subscriptions file
            auto_merge: Whether to auto-merge PRs (default: False)
            temp_repo_dir: Temporary directory for repo (optional)
            
        Returns:
            Configured SubscriptionManager instance
        """
        github_config = GitHubConfig(
            repo_url=repo_url,
            token=token,
            temp_repo_dir=temp_repo_dir or "/tmp/ytdl-sub-scrape-repo",
            auto_merge=auto_merge
        )
        
        return cls(github_config, subs_file_path)
