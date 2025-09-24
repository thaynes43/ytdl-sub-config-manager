"""Tests for generic subscription manager."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.git_integration.models import GitHubConfig, GitHubOperationStatus, GitHubOperationResult
from src.git_integration.subscription_manager import SubscriptionManager


class TestSubscriptionManager:
    """Test SubscriptionManager class."""
    
    @pytest.fixture
    def github_config(self):
        """Create a test GitHubConfig."""
        return GitHubConfig(
            repo_url="github.com/test/repo",
            token="test-token",
            temp_repo_dir="/tmp/test-repo"
        )
    
    @pytest.fixture
    def subscription_manager(self, github_config):
        """Create a SubscriptionManager instance."""
        return SubscriptionManager(github_config, "config/subscriptions.yaml")
    
    def test_subscription_manager_initialization(self, subscription_manager, github_config):
        """Test SubscriptionManager initialization."""
        assert subscription_manager.github_config == github_config
        assert subscription_manager.subs_file_path == "config/subscriptions.yaml"
        assert subscription_manager.logger is not None
        assert subscription_manager.repo_manager is not None
        assert subscription_manager.pr_manager is not None
    
    @patch('src.git_integration.subscription_manager.RepositoryManager')
    def test_setup_repository(self, mock_repo_manager_class, subscription_manager):
        """Test repository setup."""
        # Setup mocks
        mock_repo_manager = Mock()
        mock_result = GitHubOperationResult(
            status=GitHubOperationStatus.SUCCESS,
            message="Repository setup successful"
        )
        mock_repo_manager.bootstrap_repository.return_value = mock_result
        subscription_manager.repo_manager = mock_repo_manager
        
        # Execute
        result = subscription_manager.setup_repository()
        
        # Verify
        assert result == mock_result
        mock_repo_manager.bootstrap_repository.assert_called_once()
    
    def test_get_subscriptions_file_path(self, subscription_manager):
        """Test getting subscriptions file path."""
        # Execute
        path = subscription_manager.get_subscriptions_file_path()
        
        # Verify - should return the absolute path directly
        expected_path = Path("config/subscriptions.yaml")
        assert path == expected_path
    
    @patch('builtins.open')
    def test_validate_subscriptions_file_success(self, mock_open, subscription_manager):
        """Test successful subscriptions file validation."""
        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True):
            
            # Execute
            result = subscription_manager.validate_subscriptions_file()
            
            # Verify
            assert result is True
            mock_open.assert_called_once()
    
    def test_validate_subscriptions_file_not_exists(self, subscription_manager):
        """Test subscriptions file validation when file doesn't exist."""
        with patch.object(Path, 'exists', return_value=False):
            # Execute
            result = subscription_manager.validate_subscriptions_file()
            
            # Verify
            assert result is False
    
    def test_validate_subscriptions_file_not_file(self, subscription_manager):
        """Test subscriptions file validation when path is not a file."""
        
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=False):
            
            # Execute
            result = subscription_manager.validate_subscriptions_file()
            
            # Verify
            assert result is False
    
    @patch('builtins.open')
    def test_validate_subscriptions_file_read_error(self, mock_open, subscription_manager):
        """Test subscriptions file validation with read error."""
        # Mock file operations to raise exception
        mock_open.side_effect = Exception("Permission denied")
        
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True):
            
            # Execute
            result = subscription_manager.validate_subscriptions_file()
            
            # Verify
            assert result is False
    
    def test_finalize_subscription_updates_no_changes(self, subscription_manager):
        """Test finalization when there are no changes to commit."""
        # Setup mocks
        mock_repo_manager = Mock()
        mock_result = GitHubOperationResult(
            status=GitHubOperationStatus.SKIPPED,
            message="No changes to commit"
        )
        mock_repo_manager.commit_and_push_changes.return_value = mock_result
        subscription_manager.repo_manager = mock_repo_manager
        
        # Execute
        result = subscription_manager.finalize_subscription_updates()
        
        # Verify
        assert result == mock_result
        mock_repo_manager.commit_and_push_changes.assert_called_once()
    
    def test_finalize_subscription_updates_commit_failure(self, subscription_manager):
        """Test finalization when commit fails."""
        # Setup mocks
        mock_repo_manager = Mock()
        mock_result = GitHubOperationResult(
            status=GitHubOperationStatus.FAILED,
            message="Commit failed"
        )
        mock_repo_manager.commit_and_push_changes.return_value = mock_result
        subscription_manager.repo_manager = mock_repo_manager
        
        # Execute
        result = subscription_manager.finalize_subscription_updates()
        
        # Verify
        assert result == mock_result
        mock_repo_manager.commit_and_push_changes.assert_called_once()
    
    def test_finalize_subscription_updates_success(self, subscription_manager):
        """Test successful finalization with PR creation."""
        # Setup mocks
        mock_repo_manager = Mock()
        mock_commit_result = GitHubOperationResult(
            status=GitHubOperationStatus.SUCCESS,
            message="Changes committed",
            branch_name="test-branch"
        )
        mock_repo_manager.commit_and_push_changes.return_value = mock_commit_result
        subscription_manager.repo_manager = mock_repo_manager
        
        mock_pr_manager = Mock()
        mock_pr_result = GitHubOperationResult(
            status=GitHubOperationStatus.SUCCESS,
            message="PR created",
            pr_url="https://github.com/test/repo/pull/123"
        )
        mock_pr_manager.create_pull_request.return_value = mock_pr_result
        subscription_manager.pr_manager = mock_pr_manager
        
        # Execute
        result = subscription_manager.finalize_subscription_updates(
            commit_message="Custom commit",
            pr_title="Custom PR title",
            pr_body="Custom PR body"
        )
        
        # Verify
        assert result == mock_pr_result
        mock_repo_manager.commit_and_push_changes.assert_called_once_with("Custom commit")
        mock_pr_manager.create_pull_request.assert_called_once_with(
            branch_name="test-branch",
            pr_title="Custom PR title",
            pr_body="Custom PR body"
        )
    
    def test_cleanup(self, subscription_manager):
        """Test cleanup method."""
        # Setup mocks
        mock_repo_manager = Mock()
        subscription_manager.repo_manager = mock_repo_manager
        
        # Execute
        subscription_manager.cleanup()
        
        # Verify
        mock_repo_manager.cleanup_repository.assert_called_once()
    
    def test_create_from_config(self):
        """Test creating SubscriptionManager from config values."""
        manager = SubscriptionManager.create_from_config(
            repo_url="github.com/test/repo",
            token="test-token",
            subs_file_path="config/subscriptions.yaml",
            auto_merge=True,
            temp_repo_dir="/custom/temp"
        )
        
        assert manager.github_config.repo_url == "github.com/test/repo"
        assert manager.github_config.token == "test-token"
        assert manager.github_config.auto_merge is True
        assert manager.github_config.temp_repo_dir == "/custom/temp"
        assert manager.subs_file_path == "config/subscriptions.yaml"
    
    def test_create_from_config_defaults(self):
        """Test creating SubscriptionManager with default values."""
        manager = SubscriptionManager.create_from_config(
            repo_url="github.com/test/repo",
            token="test-token",
            subs_file_path="config/subscriptions.yaml"
        )
        
        assert manager.github_config.auto_merge is False
        assert manager.github_config.temp_repo_dir == "/tmp/ytdl-sub-scrape-repo"
    
    def test_create_from_config_with_different_media_types(self):
        """Test that the manager works with different subscription file paths."""
        # Test with different media type configurations
        peloton_manager = SubscriptionManager.create_from_config(
            repo_url="github.com/test/repo",
            token="test-token",
            subs_file_path="peloton/subscriptions.yaml"
        )
        
        youtube_manager = SubscriptionManager.create_from_config(
            repo_url="github.com/test/repo",
            token="test-token",
            subs_file_path="youtube/subscriptions.yaml"
        )
        
        spotify_manager = SubscriptionManager.create_from_config(
            repo_url="github.com/test/repo",
            token="test-token",
            subs_file_path="spotify/config.yaml"
        )
        
        # Verify they all work with different paths
        assert peloton_manager.subs_file_path == "peloton/subscriptions.yaml"
        assert youtube_manager.subs_file_path == "youtube/subscriptions.yaml"
        assert spotify_manager.subs_file_path == "spotify/config.yaml"
        
        # All should have the same GitHub config
        assert peloton_manager.github_config.repo_url == "github.com/test/repo"
        assert youtube_manager.github_config.repo_url == "github.com/test/repo"
        assert spotify_manager.github_config.repo_url == "github.com/test/repo"
