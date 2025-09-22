# Test Coverage Plan for Dependency Injection System

## Current Status: 47% Coverage

### ✅ Well-Covered Components (>80%)
- `src/core/logging.py`: **91%**
- `src/core/models.py`: **97%** 
- `src/io/episode_parser.py`: **89%**
- `src/io/filesystem_parser.py`: **89%**
- `src/io/strategy_registry.py`: **90%**

### 🔶 Moderate Coverage (50-80%)
- `src/io/directory_validator.py`: **48%** (old - being deprecated)
- `src/io/file_manager.py`: **51%** (needs updating for DI)
- `src/io/media_source_strategy.py`: **75%**
- `src/io/peloton_strategy.py`: **59%** (old - being deprecated)

### 🚨 Low Coverage (<50%) - Priority for New Tests

#### New Dependency Injection Components
- `src/io/generic_directory_validator.py`: **44%** ⭐ **HIGH PRIORITY**
- `src/io/generic_episode_manager.py`: **38%** ⭐ **HIGH PRIORITY**
- `src/io/strategy_loader.py`: **64%** ⭐ **MEDIUM PRIORITY**

#### Peloton Domain Strategies
- `src/io/peloton/episodes_from_subscriptions.py`: **32%** ⭐ **HIGH PRIORITY**
- `src/io/peloton/repair_5050_strategy.py`: **34%** ⭐ **HIGH PRIORITY**
- `src/io/peloton/activity_based_path_strategy.py`: **60%** ⭐ **MEDIUM PRIORITY**
- `src/io/peloton/episodes_from_disk.py`: **73%** ⭐ **LOW PRIORITY**

### 📋 Test Fixes Needed

#### Immediate Fixes (Broken Tests)
1. **`test_directory_validator.py`** - Update to use `GenericDirectoryValidator` with DI
2. **`test_episode_parsing.py`** - Update `FileManager` tests for new constructor
3. **Integration tests** - Update to use new DI configuration

#### New Tests Needed
1. **`test_strategy_loader.py`** - Test dynamic class loading
2. **`test_generic_directory_validator.py`** - Test DI-based validation
3. **`test_generic_episode_manager.py`** - Test DI-based episode parsing
4. **`test_peloton_strategies.py`** - Test all Peloton domain strategies
5. **`test_dependency_injection_integration.py`** - End-to-end DI tests

### 🎯 Goal: 80% Coverage

#### Phase 1: Fix Broken Tests (Current: 10 failures)
- Update existing tests to work with DI system
- Estimated effort: 2-3 hours

#### Phase 2: Add Strategy Tests (Target: +15% coverage)
- Test each Peloton strategy in isolation
- Test strategy loading and instantiation
- Estimated effort: 3-4 hours

#### Phase 3: Add Integration Tests (Target: +10% coverage)
- Test full DI workflow
- Test configuration-driven strategy loading
- Test error handling and fallbacks
- Estimated effort: 2-3 hours

#### Phase 4: Add Edge Case Tests (Target: +8% coverage)
- Test invalid configurations
- Test missing strategies
- Test corrupted directory scenarios
- Estimated effort: 2-3 hours

### 📊 Expected Final Coverage: ~80%

The dependency injection system is **functionally working** as demonstrated by the successful test run, but needs comprehensive test coverage to ensure robustness and maintainability.
