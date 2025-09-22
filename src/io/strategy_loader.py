"""Strategy loader for dependency injection of configurable strategies."""

import importlib
from typing import Any, Dict, List, Type, TypeVar, Optional
from ..core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class StrategyLoader:
    """Loads and instantiates strategy classes from configuration."""
    
    def __init__(self):
        self._cache: Dict[str, Type] = {}
    
    def load_class(self, module_path: str) -> Type:
        """Load a class from a module path string.
        
        Args:
            module_path: Full path like "src.io.peloton.episode_parser:PelotonEpisodeParser"
            
        Returns:
            The loaded class
            
        Raises:
            ImportError: If the module or class cannot be loaded
        """
        if module_path in self._cache:
            return self._cache[module_path]
        
        try:
            # Split module path from class name
            if ':' not in module_path:
                raise ValueError(f"Invalid module path format. Expected 'module:class', got: {module_path}")
            
            module_name, class_name = module_path.split(':', 1)
            
            # Import the module
            module = importlib.import_module(module_name)
            
            # Get the class from the module
            if not hasattr(module, class_name):
                raise AttributeError(f"Module {module_name} has no class {class_name}")
            
            strategy_class = getattr(module, class_name)
            
            # Cache the loaded class
            self._cache[module_path] = strategy_class
            
            logger.debug(f"Loaded strategy class: {module_path}")
            return strategy_class
            
        except Exception as e:
            logger.error(f"Failed to load strategy class {module_path}: {e}")
            raise ImportError(f"Cannot load strategy class {module_path}") from e
    
    def instantiate_strategy(self, module_path: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Load and instantiate a strategy class.
        
        Args:
            module_path: Full path like "src.io.peloton.episode_parser:PelotonEpisodeParser"
            options: Optional dictionary of options to pass to constructor
            
        Returns:
            Instantiated strategy object
        """
        strategy_class = self.load_class(module_path)
        
        # Instantiate with options if provided
        if options:
            return strategy_class(**options)
        else:
            return strategy_class()
    
    def load_strategies(self, strategy_configs: List[str], options: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Load multiple strategy instances from a list of module paths.
        
        Args:
            strategy_configs: List of module paths
            options: Optional shared options for all strategies
            
        Returns:
            List of instantiated strategy objects
        """
        strategies = []
        
        for config in strategy_configs:
            try:
                strategy = self.instantiate_strategy(config, options)
                strategies.append(strategy)
                logger.info(f"Loaded strategy: {config}")
            except Exception as e:
                logger.error(f"Failed to load strategy {config}: {e}")
                # Continue loading other strategies rather than failing completely
                continue
        
        return strategies


# Global strategy loader instance
strategy_loader = StrategyLoader()
