# Metrics Collection System - Overview

## Summary

The metrics collection system provides comprehensive tracking and reporting of statistics across all workflow stages of the ytdl-sub config manager. This system enables:

- **Detailed run tracking** - Capture metrics from each stage of the workflow
- **Historical analysis** - Store run snapshots for comparison across runs
- **Enhanced PR descriptions** - Generate detailed summaries for GitHub PRs
- **Debugging and monitoring** - Log summaries for operational insights

## Architecture

### Design Pattern

The metrics system follows the project's established patterns:

1. **Dataclasses** - All metrics are modeled as immutable dataclasses
2. **Dependency Injection** - Metrics collectors are passed to components
3. **Separation of Concerns** - Each stage has its own metrics dataclass
4. **Optional Integration** - Components work with or without metrics collection

### Core Components

```
src/core/metrics.py
├── DirectoryRepairMetrics       # Stage 1: Directory validation/repair
├── ExistingEpisodesMetrics      # Stage 2: Episode discovery
├── WebScrapingMetrics           # Stage 3: Web scraping
├── SubscriptionChangesMetrics   # Stage 4: Subscription updates
├── SubscriptionHistoryMetrics   # Stage 5: History tracking
├── RunSnapshot                  # Historical data point
└── RunMetrics                   # Complete run aggregator
```

### Enhanced Subscription History

```
src/io/subscription_history_manager.py
├── RunSnapshot                  # Snapshot dataclass
├── save_run_snapshot()          # Store snapshot in history file
├── get_run_snapshots()          # Retrieve historical snapshots
└── get_last_run_snapshot()      # Get most recent snapshot
```

### Subscription History JSON Format

```json
{
  "subscriptions": [...],
  "last_updated": "2025-10-03T09:47:27.123456",
  "run_snapshots": [
    {
      "run_timestamp": "2025-10-03T09:30:45.123456",
      "videos_on_disk": 184,
      "videos_in_subscriptions": 23,
      "new_videos_added": 15,
      "total_activities": 12
    }
  ]
}
```

**Note:** The system automatically keeps only the last 50 snapshots to prevent unbounded growth.

## Metrics by Stage

### 1. Directory Repair Stage

**Tracks:**
- Total episodes scanned
- Corrupted locations found/repaired
- Parent directories repaired
- Episode conflicts found/resolved
- Repair passes executed

**Summary Example:**
```
Validated 184 episodes - 5 corrupted locations repaired - 2 episode conflicts resolved
```

### 2. Existing Episodes Stage

**Tracks:**
- Total activities tracked
- Episodes on disk
- Subscriptions in YAML
- Existing class IDs count
- Per-activity episode stats (seasons, episodes)

**Summary Example:**
```
Found 12 activities - 184 episodes on disk - 23 subscriptions in YAML - 195 existing class IDs
```

### 3. Web Scraping Stage

**Tracks:**
- Total activities scraped
- Classes found/skipped/added
- Errors encountered
- Per-activity scraping results

**Summary Example:**
```
Scraped 3 activities - 50 classes found - 10 skipped - 40 added - 0 errors
```

### 4. Subscription Changes Stage

**Tracks:**
- Subscriptions removed (already-downloaded, stale)
- Subscriptions added (new)
- Directories updated
- Titles sanitized
- Conflicts resolved

**Summary Example:**
```
5 already-downloaded removed - 3 stale removed - 15 new added - 2 conflicts resolved
```

### 5. Subscription History Stage

**Tracks:**
- Total tracked subscriptions
- Subscriptions added/removed from history
- Stale subscriptions found
- History sync status

**Summary Example:**
```
Tracking 127 subscriptions - 15 added - 0 removed - 3 stale
```

## Output Formats

### Console Summary

```
Run Summary (20251003_094727)
============================================================

Directory Repair:
  Validated 184 episodes - 5 corrupted locations repaired

Existing Episodes:
  Found 12 activities - 184 episodes on disk - 23 subscriptions in YAML

Web Scraping:
  Scraped 3 activities - 50 classes found - 10 skipped - 40 added

Subscription Changes:
  5 already-downloaded removed - 15 new added

Subscription History:
  Tracking 127 subscriptions - 15 added

============================================================
```

### GitHub PR Description

```markdown
## Subscription Update Summary

**Run ID:** `20251003_094727`
**Timestamp:** 2025-10-03T09:47:27.123456

### Changes Made

- **15 new classes added**
  - 25 found, 10 skipped
  
  **Activity Breakdown:**
  - strength: 8 classes
  - yoga: 5 classes
  - cycling: 2 classes

- Removed 5 already-downloaded subscriptions
- Removed 3 stale subscriptions
- Resolved 2 path conflicts

### Current State

- **Episodes on disk:** 184
- **Subscriptions in YAML:** 38
- **Activities tracked:** 12

### Directory Repairs

Validated 184 episodes - 5 corrupted locations repaired

---

*This PR was created automatically by ytdl-sub config manager.*
```

### JSON Export

Complete metrics can be exported as JSON for programmatic analysis:

```json
{
  "run_id": "20251003_094727",
  "start_time": "2025-10-03T09:47:27.123456",
  "end_time": "2025-10-03T09:52:15.789012",
  "success": true,
  "directory_repair": {
    "total_episodes_scanned": 184,
    "corrupted_locations_repaired": 5,
    ...
  },
  "existing_episodes": {
    "total_activities": 12,
    ...
  },
  ...
}
```

## Integration

### Current Status

✅ **Scaffolding Complete** - All dataclasses and infrastructure implemented  
✅ **Tests Complete** - 41 tests covering all metrics components  
✅ **Documentation Complete** - Integration guide and overview created  
✅ **Subscription History Enhanced** - Run snapshots supported  
⏳ **Application Integration** - Ready for implementation (see integration guide)

### Next Steps

To complete the integration:

1. **Update GenericDirectoryValidator** - Add optional metrics parameter
2. **Update FileManager** - Track cleanup and modification operations
3. **Update Application.run_scrape_command** - Create and populate metrics
4. **Update PullRequestManager** - Use metrics in PR body generation

See `docs/metrics-integration.md` for detailed integration examples.

## Testing

### Test Coverage

- ✅ 41 passing tests
- ✅ 100% coverage of metrics dataclasses
- ✅ Integration test for complete workflow
- ✅ All serialization methods tested
- ✅ Summary generation tested

### Running Tests

```bash
# Run metrics tests only
python -m pytest tests/core/test_metrics.py -v

# Run with coverage
python -m pytest tests/core/test_metrics.py --cov=src/core/metrics --cov-report=term-missing
```

## Benefits

### For Developers

- **Debugging** - Detailed insights into each stage's operation
- **Testing** - Verify expected behavior with quantifiable metrics
- **Monitoring** - Track application performance over time

### For Users

- **Transparency** - Clear visibility into what changes were made
- **Historical Tracking** - Compare runs to understand trends
- **PR Review** - Rich context for reviewing automatic updates

### For Operations

- **Observability** - Structured data for monitoring systems
- **Alerting** - Detect anomalies (e.g., unusual error counts)
- **Analytics** - Analyze scraping patterns and success rates

## Design Decisions

### Why Dataclasses?

- **Immutability** - Prevents accidental modification
- **Type Safety** - Clear contracts for all metrics
- **Serialization** - Built-in conversion to dict/JSON
- **Testability** - Easy to construct and verify

### Why Optional Integration?

- **Backward Compatibility** - Existing code works without changes
- **Gradual Rollout** - Can integrate stage-by-stage
- **Flexibility** - Metrics can be disabled if needed

### Why Run Snapshots?

- **Historical Context** - Compare current run to previous runs
- **Trend Analysis** - Identify patterns over time
- **PR Diffs** - Show what changed since last run
- **Bounded Storage** - Automatic cleanup prevents unbounded growth

## Future Enhancements

Potential future additions:

1. **Metrics Export** - Send to monitoring systems (Prometheus, DataDog, etc.)
2. **Alerting** - Trigger notifications based on metric thresholds
3. **Dashboard** - Web UI for visualizing metrics over time
4. **Comparison Tools** - CLI tools to compare runs
5. **Regression Detection** - Automatic detection of performance degradation

## Related Documentation

- [`docs/metrics-integration.md`](./metrics-integration.md) - Integration guide with code examples
- [`src/core/metrics.py`](../src/core/metrics.py) - Source code with inline documentation
- [`tests/core/test_metrics.py`](../tests/core/test_metrics.py) - Comprehensive test suite
- [`.cursor/project-definition.mdc`](../.cursor/project-definition.mdc) - Updated project architecture

