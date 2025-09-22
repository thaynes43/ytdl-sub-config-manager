"""Main entry point for ytdl-sub config manager."""

import sys

from .config.cli_config import CLIConfigManager
from .core.logging import setup_logging, get_logger
from .core.application import Application


def main() -> int:
    """Main entry point for the CLI."""
    try:
        # Parse command line arguments
        cli_manager = CLIConfigManager()
        args = cli_manager.parse_args()
        
        # Set up logging early
        setup_logging(level=args.log_level, format_type=args.log_format)
        logger = get_logger(__name__)
        
        logger.info("Starting ytdl-sub Config Manager")
        
        # Create and run application
        app = Application()
        return app.run(args)
            
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        # Set up basic logging if it wasn't set up yet
        try:
            logger = get_logger(__name__)
            if not logger.handlers:
                setup_logging()
                logger = get_logger(__name__)
        except:
            setup_logging()
            logger = get_logger(__name__)
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
