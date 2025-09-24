"""Tests for GitHub repository manager."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.git_integration.models import GitHubConfig, GitHubOperationStatus
from src.git_integration.repository_manager import RepositoryManager, PullRequestManager


class TestRepositoryManager:
    """Test RepositoryManager class."""
    
    @pytest.fixture
    def github_config(self):
        """Create a test GitHubConfig."""
        return GitHubConfig(
            repo_url="github.com/test/repo",
            token="test-token",
            temp_repo_dir="/tmp/test-repo"
        )
    
    @pytest.fixture
    def repo_manager(self, github_config):
        """Create a RepositoryManager instance."""
        return RepositoryManager(github_config)
    
    def test_repository_manager_initialization(self, repo_manager, github_config):
        """Test RepositoryManager initialization."""
        assert repo_manager.config == github_config
        assert repo_manager.repo is None
        assert repo_manager.logger is not None
    
    @patch('src.git_integration.repository_manager.git.Repo.clone_from')
    @patch('src.git_integration.repository_manager.Path.exists')
    def test_bootstrap_repository_fresh_clone(self, mock_exists, mock_clone, repo_manager):
        """Test bootstrapping repository with fresh clone."""
        # Setup mocks
        mock_exists.return_value = False
        mock_repo = Mock()
        mock_clone.return_value = mock_repo
        
        # Execute
        result = repo_manager.bootstrap_repository()
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Successfully cloned repository" in result.message
        assert repo_manager.repo == mock_repo
        # Verify call was made with correct arguments (accounting for OS path differences)
        mock_clone.assert_called_once()
        call_args = mock_clone.call_args[0]
        assert call_args[0] == "https://test-token:x-oauth-basic@github.com/test/repo"
        assert str(Path(call_args[1])) == str(Path("/tmp/test-repo"))
    
    @patch('src.git_integration.repository_manager.git.Repo')
    @patch('src.git_integration.repository_manager.Path.exists')
    def test_bootstrap_repository_pull_existing(self, mock_exists, mock_repo_class, repo_manager):
        """Test bootstrapping repository with existing repo."""
        # Setup mocks
        mock_exists.return_value = True
        mock_repo = Mock()
        mock_repo.git = Mock()
        mock_repo.remotes.origin = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Execute
        result = repo_manager.bootstrap_repository()
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Successfully pulled latest changes" in result.message
        assert repo_manager.repo == mock_repo
        mock_repo.git.checkout.assert_called_once_with("main")
        mock_repo.remotes.origin.pull.assert_called_once()
    
    @patch('src.git_integration.repository_manager.Path.exists')
    def test_bootstrap_repository_failure(self, mock_exists, repo_manager):
        """Test bootstrap repository failure."""
        # Setup mocks
        mock_exists.side_effect = Exception("Test error")
        
        # Execute
        result = repo_manager.bootstrap_repository()
        
        # Verify
        assert result.status == GitHubOperationStatus.FAILED
        assert "Repository bootstrap failed" in result.message
        assert result.error is not None
    
    def test_commit_and_push_no_repo(self, repo_manager):
        """Test commit and push when repo is not initialized."""
        result = repo_manager.commit_and_push_changes()
        
        assert result.status == GitHubOperationStatus.FAILED
        assert "Repository not initialized" in result.message
    
    @patch('src.git_integration.repository_manager.time.strftime')
    def test_commit_and_push_no_changes(self, mock_strftime, repo_manager):
        """Test commit and push when there are no changes."""
        # Setup mocks
        mock_strftime.return_value = "20231225120000"
        mock_repo = Mock()
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        repo_manager.repo = mock_repo
        
        # Execute
        result = repo_manager.commit_and_push_changes()
        
        # Verify
        assert result.status == GitHubOperationStatus.SKIPPED
        assert "No changes to commit" in result.message
    
    @patch('src.git_integration.repository_manager.time.strftime')
    def test_commit_and_push_success(self, mock_strftime, repo_manager):
        """Test successful commit and push."""
        # Setup mocks
        mock_strftime.return_value = "20231225120000"
        mock_repo = Mock()
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = []
        mock_repo.git = Mock()
        mock_repo.remotes.origin = Mock()
        repo_manager.repo = mock_repo
        
        # Execute
        result = repo_manager.commit_and_push_changes("Custom commit message")
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Successfully created and pushed branch" in result.message
        assert result.branch_name == "ytdl-sub-update-20231225120000"
        
        # Verify git operations
        mock_repo.git.checkout.assert_called_once_with('-b', 'ytdl-sub-update-20231225120000')
        mock_repo.git.add.assert_called_once_with('--all')
        mock_repo.git.config.assert_any_call('--local', 'user.email', 'noreply@haynesnetwork.com')
        mock_repo.git.config.assert_any_call('--local', 'user.name', 'ytdl-sub Config Manager')
        mock_repo.git.commit.assert_called_once_with('-m', 'Custom commit message')
        mock_repo.remotes.origin.push.assert_called_once_with('ytdl-sub-update-20231225120000')
    
    @patch('src.git_integration.repository_manager.time.strftime')
    def test_commit_and_push_failure(self, mock_strftime, repo_manager):
        """Test commit and push failure."""
        # Setup mocks
        mock_strftime.return_value = "20231225120000"
        mock_repo = Mock()
        mock_repo.is_dirty.return_value = True
        mock_repo.git.checkout.side_effect = Exception("Git error")
        repo_manager.repo = mock_repo
        
        # Execute
        result = repo_manager.commit_and_push_changes()
        
        # Verify
        assert result.status == GitHubOperationStatus.FAILED
        assert "Commit and push failed" in result.message
        assert result.error is not None
    
    def test_get_repository_path(self, repo_manager):
        """Test getting repository path."""
        path = repo_manager.get_repository_path()
        assert path == Path("/tmp/test-repo")
    
    @patch('src.git_integration.repository_manager.shutil.rmtree')
    @patch('src.git_integration.repository_manager.Path.exists')
    @patch('src.git_integration.repository_manager.time.sleep')
    def test_cleanup_repository(self, mock_sleep, mock_exists, mock_rmtree, repo_manager):
        """Test repository cleanup."""
        mock_exists.return_value = True
        mock_rmtree.return_value = None  # Success case
        
        repo_manager.cleanup_repository()
        
        # Should call rmtree once (success on first try)
        mock_rmtree.assert_called_once_with(Path("/tmp/test-repo"))
        mock_sleep.assert_called_once_with(1)  # Initial wait
    
    @patch('src.git_integration.repository_manager.shutil.rmtree')
    @patch('src.git_integration.repository_manager.Path.exists')
    @patch('src.git_integration.repository_manager.time.sleep')
    def test_cleanup_repository_with_retries(self, mock_sleep, mock_exists, mock_rmtree, repo_manager):
        """Test repository cleanup with retry logic."""
        mock_exists.return_value = True
        
        # First two attempts fail, third succeeds
        mock_rmtree.side_effect = [PermissionError("Access denied"), PermissionError("Access denied"), None]
        
        repo_manager.cleanup_repository()
        
        # Should call rmtree 3 times (2 failures + 1 success)
        assert mock_rmtree.call_count == 3
        # Should sleep 1 + 2 + 2 seconds (initial + 2 retries)
        expected_sleep_calls = [1, 2, 2]
        actual_sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_sleep_calls == expected_sleep_calls
    


class TestPullRequestManager:
    """Test PullRequestManager class."""
    
    @pytest.fixture
    def github_config(self):
        """Create a test GitHubConfig."""
        return GitHubConfig(
            repo_url="github.com/test/repo",
            token="test-token"
        )
    
    @pytest.fixture
    def pr_manager(self, github_config):
        """Create a PullRequestManager instance."""
        return PullRequestManager(github_config)
    
    def test_pr_manager_initialization(self, pr_manager, github_config):
        """Test PullRequestManager initialization."""
        assert pr_manager.config == github_config
        assert pr_manager.logger is not None
    
    @patch('src.git_integration.repository_manager.Github')
    @patch('src.git_integration.repository_manager.time.strftime')
    def test_create_pull_request_success(self, mock_strftime, mock_github_class, pr_manager):
        """Test successful pull request creation."""
        # Setup mocks
        mock_strftime.return_value = "2023-12-25 12:00:00"
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_repo.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        # Execute
        result = pr_manager.create_pull_request("test-branch")
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Pull request created successfully" in result.message
        assert result.branch_name == "test-branch"
        assert result.pr_url == "https://github.com/test/repo/pull/123"
        
        mock_github_class.assert_called_once_with("test-token")
        mock_github.get_repo.assert_called_once_with("test/repo")
        mock_repo.create_pull.assert_called_once()
    
    @patch('src.git_integration.repository_manager.Github')
    def test_create_pull_request_with_custom_content(self, mock_github_class, pr_manager):
        """Test pull request creation with custom title and body."""
        # Setup mocks
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_repo.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        # Execute
        result = pr_manager.create_pull_request(
            "test-branch",
            pr_title="Custom Title",
            pr_body="Custom Body"
        )
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        mock_repo.create_pull.assert_called_once_with(
            title="Custom Title",
            body="Custom Body",
            head="test-branch",
            base="main"
        )
    
    @patch('src.git_integration.repository_manager.Github')
    def test_create_pull_request_failure(self, mock_github_class, pr_manager):
        """Test pull request creation failure."""
        # Setup mocks
        mock_github_class.side_effect = Exception("GitHub API error")
        
        # Execute
        result = pr_manager.create_pull_request("test-branch")
        
        # Verify
        assert result.status == GitHubOperationStatus.FAILED
        assert "Pull request creation failed" in result.message
        assert result.error is not None
        assert result.branch_name == "test-branch"
    
    @patch('src.git_integration.repository_manager.Github')
    @patch('src.git_integration.repository_manager.time.sleep')
    def test_create_pull_request_with_auto_merge_success(self, mock_sleep, mock_github_class, pr_manager):
        """Test pull request creation with successful auto-merge."""
        # Setup config with auto-merge enabled
        pr_manager.config = GitHubConfig(
            repo_url="github.com/test/repo",
            token="test-token",
            auto_merge=True
        )
        
        # Setup mocks
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_pr.mergeable = True
        mock_pr.merge.return_value.merged = True
        mock_repo.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        # Execute
        result = pr_manager.create_pull_request("test-branch")
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Pull request created and auto-merged" in result.message
        mock_pr.update.assert_called_once()
        mock_pr.merge.assert_called_once()
    
    @patch('src.git_integration.repository_manager.Github')
    @patch('src.git_integration.repository_manager.time.sleep')
    def test_create_pull_request_auto_merge_not_mergeable(self, mock_sleep, mock_github_class, pr_manager):
        """Test pull request creation when auto-merge fails due to conflicts."""
        # Setup config with auto-merge enabled
        pr_manager.config = GitHubConfig(
            repo_url="github.com/test/repo",
            token="test-token",
            auto_merge=True
        )
        
        # Setup mocks
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_pr.mergeable = False
        mock_repo.create_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        # Execute
        result = pr_manager.create_pull_request("test-branch")
        
        # Verify
        assert result.status == GitHubOperationStatus.SUCCESS
        assert "Pull request created but auto-merge failed" in result.message
        assert "not mergeable" in result.message
        mock_pr.update.assert_called_once()
        mock_pr.merge.assert_not_called()
