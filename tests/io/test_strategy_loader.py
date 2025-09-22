"""Tests for StrategyLoader class."""

import pytest
from unittest.mock import patch, MagicMock
from src.io.strategy_loader import StrategyLoader, strategy_loader


class TestStrategyLoader:
    """Test the StrategyLoader class."""

    def test_strategy_loader_initialization(self):
        """Test StrategyLoader initialization."""
        loader = StrategyLoader()
        assert loader._cache == {}

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_success(self, mock_import_module):
        """Test successful class loading."""
        # Setup mock module with mock class
        mock_class = MagicMock()
        mock_module = MagicMock()
        mock_module.MockClass = mock_class
        mock_import_module.return_value = mock_module

        loader = StrategyLoader()
        result = loader.load_class("test.module:MockClass")

        assert result == mock_class
        mock_import_module.assert_called_once_with("test.module")
        # Should be cached
        assert loader._cache["test.module:MockClass"] == mock_class

    def test_load_class_from_cache(self):
        """Test loading class from cache."""
        loader = StrategyLoader()
        mock_class = MagicMock()
        loader._cache["cached.module:CachedClass"] = mock_class

        result = loader.load_class("cached.module:CachedClass")
        assert result == mock_class

    def test_load_class_invalid_format(self):
        """Test loading class with invalid module path format."""
        loader = StrategyLoader()
        
        with pytest.raises(ImportError, match="Cannot load strategy class"):
            loader.load_class("invalid_format_no_colon")

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_module_not_found(self, mock_import_module):
        """Test loading class when module is not found."""
        mock_import_module.side_effect = ModuleNotFoundError("No module named 'nonexistent'")

        loader = StrategyLoader()
        
        with pytest.raises(ImportError, match="Cannot load strategy class"):
            loader.load_class("nonexistent.module:SomeClass")

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_class_not_found(self, mock_import_module):
        """Test loading class when class doesn't exist in module."""
        mock_module = MagicMock()
        # Remove the attribute to simulate class not found
        del mock_module.NonExistentClass
        mock_import_module.return_value = mock_module

        loader = StrategyLoader()
        
        with pytest.raises(ImportError, match="Cannot load strategy class"):
            loader.load_class("test.module:NonExistentClass")

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_general_exception(self, mock_import_module):
        """Test loading class with general exception."""
        mock_import_module.side_effect = Exception("General error")

        loader = StrategyLoader()
        
        with pytest.raises(ImportError, match="Cannot load strategy class"):
            loader.load_class("test.module:SomeClass")

    @patch.object(StrategyLoader, 'load_class')
    def test_instantiate_strategy_no_options(self, mock_load_class):
        """Test instantiating strategy without options."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_load_class.return_value = mock_class

        loader = StrategyLoader()
        result = loader.instantiate_strategy("test.module:TestClass")

        assert result == mock_instance
        mock_load_class.assert_called_once_with("test.module:TestClass")
        mock_class.assert_called_once_with()

    @patch.object(StrategyLoader, 'load_class')
    def test_instantiate_strategy_with_options(self, mock_load_class):
        """Test instantiating strategy with options."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_load_class.return_value = mock_class

        loader = StrategyLoader()
        options = {"param1": "value1", "param2": "value2"}
        result = loader.instantiate_strategy("test.module:TestClass", options)

        assert result == mock_instance
        mock_load_class.assert_called_once_with("test.module:TestClass")
        mock_class.assert_called_once_with(**options)

    @patch.object(StrategyLoader, 'instantiate_strategy')
    def test_load_strategies_success(self, mock_instantiate_strategy):
        """Test loading multiple strategies successfully."""
        mock_strategy1 = MagicMock()
        mock_strategy2 = MagicMock()
        mock_instantiate_strategy.side_effect = [mock_strategy1, mock_strategy2]

        loader = StrategyLoader()
        strategy_configs = ["test.module:Strategy1", "test.module:Strategy2"]
        options = {"shared_option": "value"}
        
        result = loader.load_strategies(strategy_configs, options)

        assert result == [mock_strategy1, mock_strategy2]
        assert mock_instantiate_strategy.call_count == 2
        mock_instantiate_strategy.assert_any_call("test.module:Strategy1", options)
        mock_instantiate_strategy.assert_any_call("test.module:Strategy2", options)

    @patch.object(StrategyLoader, 'instantiate_strategy')
    def test_load_strategies_with_failure(self, mock_instantiate_strategy):
        """Test loading strategies with one failure (should continue)."""
        mock_strategy1 = MagicMock()
        mock_strategy3 = MagicMock()
        mock_instantiate_strategy.side_effect = [
            mock_strategy1,
            Exception("Failed to load strategy2"),
            mock_strategy3
        ]

        loader = StrategyLoader()
        strategy_configs = ["test.module:Strategy1", "test.module:Strategy2", "test.module:Strategy3"]
        
        result = loader.load_strategies(strategy_configs)

        # Should return only the successful strategies
        assert result == [mock_strategy1, mock_strategy3]
        assert mock_instantiate_strategy.call_count == 3

    @patch.object(StrategyLoader, 'instantiate_strategy')
    def test_load_strategies_empty_list(self, mock_instantiate_strategy):
        """Test loading strategies with empty list."""
        loader = StrategyLoader()
        
        result = loader.load_strategies([])

        assert result == []
        mock_instantiate_strategy.assert_not_called()

    def test_global_strategy_loader_instance(self):
        """Test that global strategy_loader instance exists."""
        assert strategy_loader is not None
        assert isinstance(strategy_loader, StrategyLoader)

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_with_nested_class_name(self, mock_import_module):
        """Test loading class with nested class names (containing dots)."""
        mock_class = MagicMock()
        mock_module = MagicMock()
        mock_module.NestedClass = mock_class
        mock_import_module.return_value = mock_module

        loader = StrategyLoader()
        result = loader.load_class("test.module:NestedClass")

        assert result == mock_class
        mock_import_module.assert_called_once_with("test.module")

    @patch('src.io.strategy_loader.importlib.import_module')
    def test_load_class_caching_behavior(self, mock_import_module):
        """Test that caching works correctly for repeated calls."""
        mock_class = MagicMock()
        mock_module = MagicMock()
        mock_module.TestClass = mock_class
        mock_import_module.return_value = mock_module

        loader = StrategyLoader()
        
        # First call should import module
        result1 = loader.load_class("test.module:TestClass")
        assert result1 == mock_class
        mock_import_module.assert_called_once_with("test.module")
        
        # Second call should use cache
        result2 = loader.load_class("test.module:TestClass")
        assert result2 == mock_class
        # Should still only have been called once (cached)
        mock_import_module.assert_called_once_with("test.module")
