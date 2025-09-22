"""Configuration management for ytdl-sub config manager."""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Config:
    """Immutable configuration object for the application."""
    
    # Required configuration
    peloton_username: str
    peloton_password: str
    media_dir: str
    
    # Conditional configuration
    subs_file: str
    github_repo_url: str = ""
    github_token: str = ""
    
    # Optional configuration with defaults
    peloton_class_limit_per_activity: int = 25
    peloton_activities: List[Activity] = field(default_factory=list)
    run_in_container: bool = True
    peloton_page_scrolls: int = 10
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "standard"
    
    # Internal paths
    temp_repo_dir: str = "/tmp/peloton-scrape-repo"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate required fields
        if not self.peloton_username:
            raise ValueError("PELOTON_USERNAME is required")
        if not self.peloton_password:
            raise ValueError("PELOTON_PASSWORD is required")
        if not self.media_dir:
            raise ValueError("MEDIA_DIR is required")
        
        # Validate conditional fields
        if self.github_repo_url and not self.github_token:
            raise ValueError("GITHUB_TOKEN is required when GITHUB_REPO_URL is set")
        
        # Validate numeric fields
        if self.peloton_class_limit_per_activity <= 0:
            raise ValueError("PELOTON_CLASS_LIMIT_PER_ACTIVITY must be positive")
        if self.peloton_page_scrolls <= 0:
            raise ValueError("PELOTON_PAGE_SCROLLS must be positive")
        
        # Set default activities if empty
        if not self.peloton_activities:
            object.__setattr__(self, 'peloton_activities', 
                             [a for a in Activity if a != Activity.ALL])
        
        # Normalize GitHub repo URL
        if self.github_repo_url.startswith("https://"):
            object.__setattr__(self, 'github_repo_url', 
                             self.github_repo_url[len("https://"):])
    
    def log_config(self) -> None:
        """Log the current configuration (without secrets)."""
        logger.info("Configuration loaded:")
        logger.info(f"  PELOTON_USERNAME: {self.peloton_username}")
        logger.info(f"  PELOTON_PASSWORD: {'*' * len(self.peloton_password)} ({len(self.peloton_password)} chars)")
        logger.info(f"  MEDIA_DIR: {self.media_dir}")
        logger.info(f"  SUBS_FILE: {self.subs_file}")
        logger.info(f"  GITHUB_REPO_URL: {self.github_repo_url}")
        logger.info(f"  GITHUB_TOKEN: {'*' * len(self.github_token)} ({len(self.github_token)} chars)")
        logger.info(f"  PELOTON_CLASS_LIMIT_PER_ACTIVITY: {self.peloton_class_limit_per_activity}")
        logger.info(f"  PELOTON_ACTIVITIES: {[a.value for a in self.peloton_activities]}")
        logger.info(f"  RUN_IN_CONTAINER: {self.run_in_container}")
        logger.info(f"  PELOTON_PAGE_SCROLLS: {self.peloton_page_scrolls}")
        logger.info(f"  LOG_LEVEL: {self.log_level}")
        logger.info(f"  LOG_FORMAT: {self.log_format}")


class ConfigLoader:
    """Loads configuration from multiple sources with precedence."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def load_config(self, 
                   config_file: Optional[str] = None,
                   cli_args: Optional[Dict[str, Any]] = None) -> Config:
        """Load configuration from all sources with precedence.
        
        Precedence order (highest to lowest):
        1. CLI arguments
        2. Environment variables
        3. YAML config file
        4. Defaults
        
        Args:
            config_file: Path to YAML config file
            cli_args: Dictionary of CLI arguments
            
        Returns:
            Immutable Config object
        """
        # Load .env file if it exists
        load_dotenv()
        
        # Start with defaults
        config_data = self._get_defaults()
        
        # Override with YAML config file
        if config_file:
            yaml_config = self._load_yaml_config(config_file)
            config_data.update(yaml_config)
        
        # Override with environment variables
        env_config = self._load_env_config()
        config_data.update(env_config)
        
        # Override with CLI arguments
        if cli_args:
            cli_config = self._process_cli_args(cli_args)
            config_data.update(cli_config)
        
        # Parse activities
        if isinstance(config_data.get('peloton_activities'), str):
            config_data['peloton_activities'] = ActivityData.parse_activities_from_env(
                config_data['peloton_activities']
            )
        
        return Config(**config_data)
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'peloton_username': '',
            'peloton_password': '',
            'media_dir': '',
            'subs_file': '/tmp/peloton-scrape-repo/kubernetes/main/apps/downloads/ytdl-sub/peloton/config/subscriptions.yaml',
            'github_repo_url': '',
            'github_token': '',
            'peloton_class_limit_per_activity': 25,
            'peloton_activities': [],
            'run_in_container': True,
            'peloton_page_scrolls': 10,
            'log_level': 'INFO',
            'log_format': 'standard',
            'temp_repo_dir': '/tmp/peloton-scrape-repo'
        }
    
    def _load_yaml_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(config_file)
        if not config_path.exists():
            self.logger.warning(f"Config file not found: {config_file}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f) or {}
            self.logger.info(f"Loaded configuration from: {config_file}")
            return self._normalize_keys(yaml_data)
        except Exception as e:
            self.logger.error(f"Error loading config file {config_file}: {e}")
            return {}
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mapping = {
            'PELOTON_USERNAME': 'peloton_username',
            'PELOTON_PASSWORD': 'peloton_password',
            'MEDIA_DIR': 'media_dir',
            'SUBS_FILE': 'subs_file',
            'GITHUB_REPO_URL': 'github_repo_url',
            'GITHUB_TOKEN': 'github_token',
            'PELOTON_CLASS_LIMIT_PER_ACTIVITY': 'peloton_class_limit_per_activity',
            'PELOTON_ACTIVITY': 'peloton_activities',
            'RUN_IN_CONTAINER': 'run_in_container',
            'PELOTON_PAGE_SCROLLS': 'peloton_page_scrolls',
            'LOG_LEVEL': 'log_level',
            'LOG_FORMAT': 'log_format'
        }
        
        config = {}
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if config_key in ['peloton_class_limit_per_activity', 'peloton_page_scrolls']:
                    try:
                        config[config_key] = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                elif config_key == 'run_in_container':
                    config[config_key] = value.strip().lower() in ('1', 'true', 'yes')
                else:
                    config[config_key] = value
        
        return config
    
    def _process_cli_args(self, cli_args: Dict[str, Any]) -> Dict[str, Any]:
        """Process CLI arguments into config format."""
        # Map CLI argument names to config keys
        cli_mapping = {
            'username': 'peloton_username',
            'password': 'peloton_password',
            'media_dir': 'media_dir',
            'subs_file': 'subs_file',
            'github_repo': 'github_repo_url',
            'github_token': 'github_token',
            'limit': 'peloton_class_limit_per_activity',
            'activities': 'peloton_activities',
            'container': 'run_in_container',
            'scrolls': 'peloton_page_scrolls',
            'log_level': 'log_level',
            'log_format': 'log_format'
        }
        
        config = {}
        for cli_key, config_key in cli_mapping.items():
            if cli_key in cli_args and cli_args[cli_key] is not None:
                config[config_key] = cli_args[cli_key]
        
        return config
    
    def _normalize_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize YAML keys to match config field names."""
        # Map YAML keys to config field names
        key_mapping = {
            'peloton-username': 'peloton_username',
            'peloton-password': 'peloton_password',
            'media-dir': 'media_dir',
            'subs-file': 'subs_file',
            'github-repo-url': 'github_repo_url',
            'github-token': 'github_token',
            'peloton-class-limit-per-activity': 'peloton_class_limit_per_activity',
            'peloton-activity': 'peloton_activities',
            'run-in-container': 'run_in_container',
            'peloton-page-scrolls': 'peloton_page_scrolls',
            'log-level': 'log_level',
            'log-format': 'log_format'
        }
        
        normalized = {}
        for key, value in data.items():
            # Use mapping if available, otherwise convert kebab-case to snake_case
            normalized_key = key_mapping.get(key, key.replace('-', '_').lower())
            normalized[normalized_key] = value
        return normalized
