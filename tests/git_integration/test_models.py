"""Tests for GitHub models."""

import pytest
from src.git_integration.models import (
    GitHubConfig, 
    GitHubOperationResult, 
    GitHubOperationStatus
)


class TestGitHubConfig:
    """Test GitHubConfig model."""
    
    def test_github_config_creation(self):
        """Test creating a GitHubConfig instance."""
        config = GitHubConfig(
            repo_url="github.com/user/repo",
            token="test-token"
        )
        
        assert config.repo_url == "github.com/user/repo"
        assert config.token == "test-token"
        assert config.temp_repo_dir == "/tmp/peloton-scrape-repo"
        assert config.branch_prefix == "peloton-update"
        assert config.base_branch == "main"
        assert config.auto_merge is False
        assert config.commit_user_name == "Peloton Scraper Bot"
        assert config.commit_user_email == "noreply@haynesnetwork.com"
    
    def test_github_config_with_custom_values(self):
        """Test creating GitHubConfig with custom values."""
        config = GitHubConfig(
            repo_url="github.com/user/repo",
            token="test-token",
            temp_repo_dir="/custom/temp",
            branch_prefix="custom-branch",
            base_branch="develop",
            auto_merge=True,
            commit_user_name="Custom Bot",
            commit_user_email="custom@example.com"
        )
        
        assert config.temp_repo_dir == "/custom/temp"
        assert config.branch_prefix == "custom-branch"
        assert config.base_branch == "develop"
        assert config.auto_merge is True
        assert config.commit_user_name == "Custom Bot"
        assert config.commit_user_email == "custom@example.com"
    
    def test_github_config_missing_required_fields(self):
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="Both repo_url and token are required"):
            GitHubConfig(repo_url="", token="test-token")
        
        with pytest.raises(ValueError, match="Both repo_url and token are required"):
            GitHubConfig(repo_url="github.com/user/repo", token="")
    
    def test_github_config_normalizes_https_url(self):
        """Test that https:// prefix is removed from repo URL."""
        config = GitHubConfig(
            repo_url="https://github.com/user/repo",
            token="test-token"
        )
        
        assert config.repo_url == "github.com/user/repo"
    
    def test_repo_name_property(self):
        """Test the repo_name property."""
        config = GitHubConfig(
            repo_url="github.com/user/repo",
            token="test-token"
        )
        
        assert config.repo_name == "user/repo"
    
    def test_authenticated_url_property(self):
        """Test the authenticated_url property."""
        config = GitHubConfig(
            repo_url="github.com/user/repo",
            token="test-token"
        )
        
        expected_url = "https://test-token:x-oauth-basic@github.com/user/repo"
        assert config.authenticated_url == expected_url


class TestGitHubOperationResult:
    """Test GitHubOperationResult model."""
    
    def test_operation_result_creation(self):
        """Test creating a GitHubOperationResult."""
        result = GitHubOperationResult(
            status=GitHubOperationStatus.SUCCESS,
            message="Operation completed successfully"
        )
        
        assert result.status == GitHubOperationStatus.SUCCESS
        assert result.message == "Operation completed successfully"
        assert result.branch_name is None
        assert result.pr_url is None
        assert result.error is None
        assert result.success is True
    
    def test_operation_result_with_all_fields(self):
        """Test creating GitHubOperationResult with all fields."""
        test_error = Exception("Test error")
        result = GitHubOperationResult(
            status=GitHubOperationStatus.FAILED,
            message="Operation failed",
            branch_name="test-branch",
            pr_url="https://github.com/user/repo/pull/123",
            error=test_error
        )
        
        assert result.status == GitHubOperationStatus.FAILED
        assert result.message == "Operation failed"
        assert result.branch_name == "test-branch"
        assert result.pr_url == "https://github.com/user/repo/pull/123"
        assert result.error == test_error
        assert result.success is False
    
    def test_success_property(self):
        """Test the success property for different statuses."""
        success_result = GitHubOperationResult(
            status=GitHubOperationStatus.SUCCESS,
            message="Success"
        )
        assert success_result.success is True
        
        failed_result = GitHubOperationResult(
            status=GitHubOperationStatus.FAILED,
            message="Failed"
        )
        assert failed_result.success is False
        
        skipped_result = GitHubOperationResult(
            status=GitHubOperationStatus.SKIPPED,
            message="Skipped"
        )
        assert skipped_result.success is False


class TestGitHubOperationStatus:
    """Test GitHubOperationStatus enum."""
    
    def test_status_values(self):
        """Test that all status values are correct."""
        assert GitHubOperationStatus.SUCCESS.value == "success"
        assert GitHubOperationStatus.FAILED.value == "failed"
        assert GitHubOperationStatus.SKIPPED.value == "skipped"
