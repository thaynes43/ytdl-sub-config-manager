"""Repository management for GitHub integration."""

import os
import shutil
import time
from pathlib import Path
from typing import Optional

import git
from github import Github

from .models import GitHubConfig, GitHubOperationResult, GitHubOperationStatus
from ..core.logging import get_logger


class RepositoryManager:
    """Manages Git repository operations."""
    
    def __init__(self, config: GitHubConfig):
        """Initialize the repository manager.
        
        Args:
            config: GitHub configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.repo: Optional[git.Repo] = None
    
    def bootstrap_repository(self) -> GitHubOperationResult:
        """Clone or pull the repository to get the latest version.
        
        Returns:
            Result of the bootstrap operation
        """
        try:
            repo_dir = Path(self.config.temp_repo_dir)
            
            if not repo_dir.exists():
                # Fresh clone
                self.logger.info(f"Cloning repository {self.config.repo_url} to {repo_dir}")
                self.repo = git.Repo.clone_from(self.config.authenticated_url, str(repo_dir))
                return GitHubOperationResult(
                    status=GitHubOperationStatus.SUCCESS,
                    message=f"Successfully cloned repository to {repo_dir}"
                )
            else:
                # Repository exists, pull latest changes
                self.logger.info(f"Pulling latest changes for {self.config.repo_url} in {repo_dir}")
                self.repo = git.Repo(str(repo_dir))
                
                # Ensure we're on the base branch
                self.repo.git.checkout(self.config.base_branch)
                
                # Pull latest changes
                origin = self.repo.remotes.origin
                origin.pull()
                
                return GitHubOperationResult(
                    status=GitHubOperationStatus.SUCCESS,
                    message=f"Successfully pulled latest changes to {repo_dir}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to bootstrap repository: {e}")
            return GitHubOperationResult(
                status=GitHubOperationStatus.FAILED,
                message=f"Repository bootstrap failed: {e}",
                error=e
            )
    
    def commit_and_push_changes(self, commit_message: Optional[str] = None) -> GitHubOperationResult:
        """Commit changes and push to a new branch.
        
        Args:
            commit_message: Custom commit message (optional)
            
        Returns:
            Result of the commit and push operation
        """
        if not self.repo:
            return GitHubOperationResult(
                status=GitHubOperationStatus.FAILED,
                message="Repository not initialized. Call bootstrap_repository() first."
            )
        
        try:
            # Check if there are any changes to commit
            if not self.repo.is_dirty() and not self.repo.untracked_files:
                self.logger.info("No changes detected in repository")
                return GitHubOperationResult(
                    status=GitHubOperationStatus.SKIPPED,
                    message="No changes to commit"
                )
            
            # Generate unique branch name
            timestamp = time.strftime("%Y%m%d%H%M%S")
            branch_name = f"{self.config.branch_prefix}-{timestamp}"
            
            # Create and checkout new branch
            self.logger.info(f"Creating branch: {branch_name}")
            self.repo.git.checkout('-b', branch_name)
            
            # Stage all changes
            self.repo.git.add('--all')
            
            # Configure git user
            self.repo.git.config('--local', 'user.email', self.config.commit_user_email)
            self.repo.git.config('--local', 'user.name', self.config.commit_user_name)
            
            # Commit changes
            if not commit_message:
                commit_message = f"Auto-update subscriptions {timestamp}"
            
            self.repo.git.commit('-m', commit_message)
            
            # Push new branch to origin
            origin = self.repo.remotes.origin
            origin.push(branch_name)
            
            self.logger.info(f"Successfully pushed branch {branch_name}")
            
            return GitHubOperationResult(
                status=GitHubOperationStatus.SUCCESS,
                message=f"Successfully created and pushed branch {branch_name}",
                branch_name=branch_name
            )
            
        except Exception as e:
            self.logger.error(f"Failed to commit and push changes: {e}")
            return GitHubOperationResult(
                status=GitHubOperationStatus.FAILED,
                message=f"Commit and push failed: {e}",
                error=e
            )
    
    def get_repository_path(self) -> Path:
        """Get the path to the cloned repository.
        
        Returns:
            Path to the repository directory
        """
        return Path(self.config.temp_repo_dir)
    
    def cleanup_repository(self) -> None:
        """Clean up the temporary repository directory."""
        repo_dir = Path(self.config.temp_repo_dir)
        if repo_dir.exists():
            # Check if cleanup is disabled for debugging
            if getattr(self.config, 'keep_repo_after_cleanup', False):
                self.logger.info(f"Repository cleanup disabled - keeping directory: {repo_dir}")
                return
            
            try:
                # Force close any open Git handles
                if self.repo:
                    self.repo.close()
                    self.repo = None
                
                # Wait a moment for file handles to be released
                import time
                time.sleep(1)
                
                # Try to remove with retries
                self._remove_directory_with_retries(repo_dir)
                
                # Final verification that cleanup was successful
                if repo_dir.exists():
                    self.logger.warning(f"Repository directory still exists after cleanup: {repo_dir}")
                    self.logger.info(f"Repository directory left at: {repo_dir} (for manual cleanup)")
                else:
                    self.logger.info(f"Successfully cleaned up repository directory: {repo_dir}")
            except Exception as e:
                # Check if directory was actually removed despite the exception
                if not repo_dir.exists():
                    self.logger.info(f"Repository directory successfully removed despite error: {e}")
                else:
                    self.logger.warning(f"Failed to cleanup repository directory: {e}")
                    self.logger.info(f"Repository directory left at: {repo_dir} (for manual cleanup)")
    
    def _remove_directory_with_retries(self, repo_dir: Path, max_retries: int = 3) -> None:
        """Remove directory with retries to handle Windows file locking issues."""
        import time
        
        for attempt in range(max_retries):
            try:
                shutil.rmtree(repo_dir)
                return  # Success
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    self.logger.debug(f"Cleanup attempt {attempt + 1} failed, retrying in 2 seconds: {e}")
                    time.sleep(2)
                else:
                    # Final attempt failed, try to remove individual files
                    self.logger.warning(f"Failed to remove directory after {max_retries} attempts, trying individual file removal")
                    self._force_remove_directory(repo_dir)
                    # Check if the directory was actually removed
                    if not repo_dir.exists():
                        return  # Success!
                    raise e
    
    def _force_remove_directory(self, repo_dir: Path) -> None:
        """Force remove directory by removing files individually."""
        try:
            # Remove .git directory first (often the source of locks)
            git_dir = repo_dir / '.git'
            if git_dir.exists():
                self._remove_git_directory(git_dir)
            
            # Remove remaining files
            for item in repo_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            
            # Remove the directory itself
            repo_dir.rmdir()
        except Exception as e:
            # Check if the directory was actually removed despite the error
            if not repo_dir.exists():
                self.logger.info(f"Directory successfully removed despite error: {e}")
                return
            self.logger.warning(f"Force removal also failed: {e}")
    
    def _remove_git_directory(self, git_dir: Path) -> None:
        """Remove .git directory with special handling for Windows."""
        try:
            # Try normal removal first
            shutil.rmtree(git_dir)
        except (PermissionError, OSError):
            # If that fails, try to remove files individually
            for root, dirs, files in os.walk(git_dir, topdown=False):
                for file in files:
                    try:
                        os.chmod(os.path.join(root, file), 0o777)
                        os.unlink(os.path.join(root, file))
                    except Exception:
                        pass  # Continue with other files
                
                for dir_name in dirs:
                    try:
                        os.rmdir(os.path.join(root, dir_name))
                    except Exception:
                        pass  # Continue with other directories
            
            # Finally try to remove the .git directory itself
            try:
                git_dir.rmdir()
            except Exception:
                # Check if it was actually removed
                if not git_dir.exists():
                    self.logger.debug(f"Git directory successfully removed despite error")
                    return
                pass


class PullRequestManager:
    """Manages GitHub pull request operations."""
    
    def __init__(self, config: GitHubConfig):
        """Initialize the pull request manager.
        
        Args:
            config: GitHub configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
    
    def create_pull_request(self, branch_name: str, 
                          pr_title: Optional[str] = None,
                          pr_body: Optional[str] = None) -> GitHubOperationResult:
        """Create a pull request for the given branch.
        
        Args:
            branch_name: Name of the branch to create PR from
            pr_title: Title for the pull request (optional)
            pr_body: Body content for the pull request (optional)
            
        Returns:
            Result of the pull request creation
        """
        try:
            # Initialize GitHub client
            github_client = Github(self.config.token)
            repo = github_client.get_repo(self.config.repo_name)
            
            # Generate default title and body if not provided
            if not pr_title:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                pr_title = f"Auto-update subscriptions {timestamp}"
            
            if not pr_body:
                pr_body = (
                    "This PR was created automatically by the ytdl-sub config manager.\n\n"
                    "## Changes\n"
                    "- Updated subscription files with new content\n"
                    "- Removed duplicate entries\n"
                    "- Maintained proper episode numbering\n\n"
                    "## Review Notes\n"
                    "Please verify the subscription updates before merging."
                )
            
            # Create pull request
            self.logger.info(f"Creating pull request from {branch_name} to {self.config.base_branch}")
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=self.config.base_branch
            )
            
            self.logger.info(f"Pull request created: {pr.html_url}")
            
            # Auto-merge if configured
            if self.config.auto_merge:
                merge_result = self._auto_merge_pull_request(pr)
                if merge_result.success:
                    return GitHubOperationResult(
                        status=GitHubOperationStatus.SUCCESS,
                        message=f"Pull request created and auto-merged: {pr.html_url}",
                        branch_name=branch_name,
                        pr_url=pr.html_url
                    )
                else:
                    # PR created but merge failed
                    return GitHubOperationResult(
                        status=GitHubOperationStatus.SUCCESS,
                        message=f"Pull request created but auto-merge failed: {pr.html_url}. {merge_result.message}",
                        branch_name=branch_name,
                        pr_url=pr.html_url
                    )
            
            return GitHubOperationResult(
                status=GitHubOperationStatus.SUCCESS,
                message=f"Pull request created successfully: {pr.html_url}",
                branch_name=branch_name,
                pr_url=pr.html_url
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {e}")
            return GitHubOperationResult(
                status=GitHubOperationStatus.FAILED,
                message=f"Pull request creation failed: {e}",
                branch_name=branch_name,
                error=e
            )
    
    def _auto_merge_pull_request(self, pr) -> GitHubOperationResult:
        """Attempt to auto-merge a pull request.
        
        Args:
            pr: GitHub pull request object
            
        Returns:
            Result of the merge operation
        """
        try:
            # Wait a moment for any CI checks to start
            time.sleep(5)
            
            # Check if PR is mergeable
            pr.update()  # Refresh PR state
            
            if not pr.mergeable:
                return GitHubOperationResult(
                    status=GitHubOperationStatus.FAILED,
                    message="Pull request is not mergeable (conflicts detected)"
                )
            
            # Merge the pull request
            merge_result = pr.merge(
                commit_title=f"Merge {pr.title}",
                commit_message="Auto-merged by ytdl-sub config manager",
                merge_method="merge"
            )
            
            if merge_result.merged:
                self.logger.info(f"Successfully auto-merged pull request: {pr.html_url}")
                return GitHubOperationResult(
                    status=GitHubOperationStatus.SUCCESS,
                    message="Pull request auto-merged successfully"
                )
            else:
                return GitHubOperationResult(
                    status=GitHubOperationStatus.FAILED,
                    message="Pull request merge was not successful"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to auto-merge pull request: {e}")
            return GitHubOperationResult(
                status=GitHubOperationStatus.FAILED,
                message=f"Auto-merge failed: {e}",
                error=e
            )
