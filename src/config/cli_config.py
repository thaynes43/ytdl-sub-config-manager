"""CLI-specific configuration management."""

import argparse
from typing import Optional, Dict, Any
from .. import __version__


class CLIConfigManager:
    """Manages CLI argument parsing and conversion to configuration."""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the CLI argument parser."""
        parser = argparse.ArgumentParser(
            description="ytdl-sub Config Manager - Peloton scraper for ytdl-sub subscriptions",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s scrape --source peloton --limit 25
  %(prog)s scrape --activities cycling,yoga --subs-file /path/to/subs.yaml
  %(prog)s scrape --config config.yaml --log-level DEBUG
  %(prog)s validate --media-dir /path/to/media --dry-run
            """
        )
        
        # Add version argument
        parser.add_argument(
            "--version",
            action="version",
            version=f"ytdl-sub Config Manager {__version__}"
        )
        
        # Global options
        parser.add_argument(
            "--config",
            type=str,
            help="Path to YAML configuration file"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set logging level (default: INFO)"
        )
        parser.add_argument(
            "--log-format",
            choices=["standard", "json"],
            default="standard",
            help="Set log format (default: standard)"
        )
        
        parser.add_argument(
            "--media-source",
            default="peloton",
            help="Media source strategy to use (default: peloton)"
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Scrape command
        self._add_scrape_command(subparsers)
        
        # Validate command
        self._add_validate_command(subparsers)
        
        return parser
    
    def _add_scrape_command(self, subparsers):
        """Add the scrape subcommand."""
        scrape_parser = subparsers.add_parser(
            "scrape",
            help="Run the scraping workflow"
        )
        
        # Peloton configuration
        peloton_group = scrape_parser.add_argument_group("Peloton Configuration")
        peloton_group.add_argument(
            "--source",
            choices=["peloton"],
            default="peloton",
            help="Source to scrape (currently only peloton supported)"
        )
        peloton_group.add_argument(
            "--username",
            type=str,
            help="Peloton username (overrides PELOTON_USERNAME env var)"
        )
        peloton_group.add_argument(
            "--password",
            type=str,
            help="Peloton password (overrides PELOTON_PASSWORD env var)"
        )
        peloton_group.add_argument(
            "--activities",
            type=str,
            help="Comma-separated list of activities to scrape (e.g., cycling,yoga)"
        )
        peloton_group.add_argument(
            "--limit",
            type=int,
            help="Maximum classes to scrape per activity (default: 25)"
        )
        peloton_group.add_argument(
            "--scrolls",
            type=int,
            help="Number of page scrolls to perform (default: 10)"
        )
        
        # File paths
        file_group = scrape_parser.add_argument_group("File Configuration")
        file_group.add_argument(
            "--media-dir",
            type=str,
            help="Path to media directory for inventory scanning"
        )
        file_group.add_argument(
            "--subs-file",
            type=str,
            help="Path to subscriptions YAML file"
        )
        
        # GitHub integration
        github_group = scrape_parser.add_argument_group("GitHub Integration")
        github_group.add_argument(
            "--github-repo",
            type=str,
            help="GitHub repository URL for PR creation"
        )
        github_group.add_argument(
            "--github-token",
            type=str,
            help="GitHub token for repository access"
        )
        
        # Runtime options
        runtime_group = scrape_parser.add_argument_group("Runtime Options")
        runtime_group.add_argument(
            "--container",
            action="store_true",
            help="Run in container mode (use system chromium)"
        )
        runtime_group.add_argument(
            "--no-container",
            action="store_true",
            help="Run in local mode (use webdriver-manager)"
        )
        runtime_group.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip directory structure validation and repair"
        )
    
    def _add_validate_command(self, subparsers):
        """Add the validate subcommand."""
        validate_parser = subparsers.add_parser(
            "validate",
            help="Validate and repair directory structure"
        )
        
        validate_parser.add_argument(
            "--media-dir",
            type=str,
            required=True,
            help="Path to media directory to validate"
        )
        validate_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes"
        )
    
    def parse_args(self, args: Optional[list] = None) -> argparse.Namespace:
        """Parse command line arguments."""
        parsed_args = self.parser.parse_args(args)
        
        # Validate arguments
        if not parsed_args.command:
            self.parser.error("No command specified. Use 'scrape' or 'validate'.")
        
        # Handle container/no-container conflict
        if parsed_args.command == "scrape":
            if hasattr(parsed_args, 'container') and hasattr(parsed_args, 'no_container'):
                if parsed_args.container and parsed_args.no_container:
                    self.parser.error("Cannot specify both --container and --no-container")
        
        return parsed_args
    
    def args_to_config_dict(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Convert parsed arguments to dictionary for config loading."""
        config_dict = {}
        
        # Map CLI args to config keys
        if hasattr(args, 'username') and args.username:
            config_dict['username'] = args.username
        if hasattr(args, 'password') and args.password:
            config_dict['password'] = args.password
        if hasattr(args, 'activities') and args.activities:
            config_dict['activities'] = args.activities
        if hasattr(args, 'limit') and args.limit:
            config_dict['limit'] = args.limit
        if hasattr(args, 'scrolls') and args.scrolls:
            config_dict['scrolls'] = args.scrolls
        if hasattr(args, 'media_dir') and args.media_dir:
            config_dict['media_dir'] = args.media_dir
        if hasattr(args, 'subs_file') and args.subs_file:
            config_dict['subs_file'] = args.subs_file
        if hasattr(args, 'github_repo') and args.github_repo:
            config_dict['github_repo'] = args.github_repo
        if hasattr(args, 'github_token') and args.github_token:
            config_dict['github_token'] = args.github_token
        
        # Handle container flag
        if hasattr(args, 'container') and args.container:
            config_dict['container'] = True
        elif hasattr(args, 'no_container') and args.no_container:
            config_dict['container'] = False
        
        # Handle validation flag
        if hasattr(args, 'skip_validation') and args.skip_validation:
            config_dict['skip_validation'] = True
        
        # Add global options
        if args.log_level:
            config_dict['log_level'] = args.log_level
        if args.log_format:
            config_dict['log_format'] = args.log_format
        
        return config_dict
