"""Data models for GitHub integration."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GitHubOperationStatus(Enum):
    """Status of GitHub operations."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class GitHubConfig:
    """Configuration for GitHub operations."""
    
    repo_url: str
    token: str
    temp_repo_dir: str = "/tmp/peloton-scrape-repo"
    branch_prefix: str = "ytdl-sub-update"
    base_branch: str = "main"
    auto_merge: bool = False
    commit_user_name: str = "ytdl-sub Config Manager"
    commit_user_email: str = "noreply@haynesnetwork.com"
    keep_repo_after_cleanup: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.repo_url or not self.token:
            raise ValueError("Both repo_url and token are required for GitHub operations")
        
        # Normalize repo URL (remove https:// prefix if present)
        if self.repo_url.startswith("https://"):
            object.__setattr__(self, 'repo_url', self.repo_url[len("https://"):])
    
    @property
    def repo_name(self) -> str:
        """Extract repository name from URL."""
        return self.repo_url.removeprefix("github.com/")
    
    @property
    def authenticated_url(self) -> str:
        """Get the authenticated repository URL."""
        return f"https://{self.token}:x-oauth-basic@{self.repo_url}"


@dataclass(frozen=True)
class GitHubOperationResult:
    """Result of a GitHub operation."""
    
    status: GitHubOperationStatus
    message: str
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    error: Optional[Exception] = None
    
    @property
    def success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == GitHubOperationStatus.SUCCESS
