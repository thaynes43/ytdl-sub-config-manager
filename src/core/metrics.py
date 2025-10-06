"""Metrics collection system for tracking run statistics across all stages."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json

from .models import Activity
from .snapshot import RunSnapshot


@dataclass
class DirectoryRepairMetrics:
    """Metrics collected during directory repair stage."""
    
    total_episodes_scanned: int = 0
    corrupted_locations_found: int = 0
    corrupted_locations_repaired: int = 0
    corrupted_locations_failed: int = 0
    parent_directories_repaired: int = 0
    episode_conflicts_found: int = 0
    episode_conflicts_resolved: int = 0
    repair_passes_executed: int = 0
    repairs_by_strategy: Dict[str, int] = field(default_factory=dict)  # strategy_name -> count
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        if self.total_episodes_scanned == 0:
            return "No episodes found to validate"
        
        total_repairs = (self.corrupted_locations_repaired + 
                        self.parent_directories_repaired + 
                        self.episode_conflicts_resolved)
        
        if total_repairs == 0:
            return f"Validated {self.total_episodes_scanned} episodes - no repairs needed"
        
        parts = [f"Validated {self.total_episodes_scanned} episodes"]
        if self.corrupted_locations_repaired > 0:
            parts.append(f"{self.corrupted_locations_repaired} corrupted locations repaired")
        if self.corrupted_locations_failed > 0:
            parts.append(f"{self.corrupted_locations_failed} FAILED to repair")
        if self.parent_directories_repaired > 0:
            parts.append(f"{self.parent_directories_repaired} parent directories cleaned")
        if self.episode_conflicts_resolved > 0:
            parts.append(f"{self.episode_conflicts_resolved} episode conflicts resolved")
        
        # Add strategy breakdown if available
        if self.repairs_by_strategy:
            strategy_summary = ", ".join([f"{name}: {count}" for name, count in self.repairs_by_strategy.items()])
            parts.append(f"Strategies used: {strategy_summary}")
        
        return " - ".join(parts)


@dataclass
class SeasonStats:
    """Statistics for a single season within an activity."""
    
    season: int
    episode_count: int = 0  # Number of episodes found
    highest_episode_number: int = 0  # Highest episode number found
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'episode_count': self.episode_count,
            'highest_episode_number': self.highest_episode_number
        }
    
    def is_synchronized(self) -> bool:
        """Check if episode count matches highest episode number."""
        return self.episode_count == self.highest_episode_number


@dataclass
class ActivityEpisodeStats:
    """Statistics for a single activity's episodes."""
    
    activity: str
    total_episodes: int = 0
    seasons: Dict[int, SeasonStats] = field(default_factory=dict)  # season -> SeasonStats
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'activity': self.activity,
            'total_episodes': self.total_episodes,
            'seasons': {str(k): v.to_dict() for k, v in self.seasons.items()}
        }
    
    def get_summary(self) -> str:
        """Generate a summary showing episode counts vs highest episode numbers."""
        if not self.seasons:
            return f"{self.activity}: {self.total_episodes} episodes"
        
        parts = [f"{self.activity}: {self.total_episodes} episodes"]
        
        # Check for synchronization issues
        sync_issues = []
        for season_num, season_stats in sorted(self.seasons.items()):
            if not season_stats.is_synchronized():
                sync_issues.append(f"S{season_num}: {season_stats.episode_count} episodes, highest E{season_stats.highest_episode_number}")
        
        if sync_issues:
            parts.append(f"⚠️ Sync issues: {'; '.join(sync_issues)}")
        
        return " - ".join(parts)


@dataclass
class ExistingEpisodesMetrics:
    """Metrics for existing episodes found on disk and in subscriptions."""
    
    total_activities: int = 0
    total_episodes_on_disk: int = 0  # Physical files on disk only
    total_episodes_on_disk_previous: int = 0  # From last run
    total_subscriptions_in_yaml: int = 0  # Episodes defined in subscriptions.yaml
    total_subscriptions_in_yaml_previous: int = 0  # From last run
    total_subscriptions_after_cleanup: int = 0
    activities: Dict[str, ActivityEpisodeStats] = field(default_factory=dict)
    existing_class_ids_count: int = 0
    previous_snapshot: Optional[object] = None  # Previous RunSnapshot for detailed change tracking
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'total_activities': self.total_activities,
            'total_episodes_on_disk': self.total_episodes_on_disk,
            'total_episodes_on_disk_previous': self.total_episodes_on_disk_previous,
            'total_subscriptions_in_yaml': self.total_subscriptions_in_yaml,
            'total_subscriptions_in_yaml_previous': self.total_subscriptions_in_yaml_previous,
            'total_subscriptions_after_cleanup': self.total_subscriptions_after_cleanup,
            'activities': {k: v.to_dict() for k, v in self.activities.items()},
            'existing_class_ids_count': self.existing_class_ids_count
        }
    
    def get_disk_delta(self) -> int:
        """Calculate change in episodes on disk since last run."""
        return self.total_episodes_on_disk - self.total_episodes_on_disk_previous
    
    def get_subscriptions_delta(self) -> int:
        """Calculate change in subscriptions since last run."""
        return self.total_subscriptions_in_yaml - self.total_subscriptions_in_yaml_previous
    
    def get_episode_changes_by_activity(self, previous_snapshot) -> Dict[str, int]:
        """Get episode count changes by activity since last run.
        
        Args:
            previous_snapshot: Previous RunSnapshot or None
            
        Returns:
            Dictionary mapping activity name to episode count change
        """
        changes = {}
        
        if not previous_snapshot or not hasattr(previous_snapshot, 'episodes_by_activity'):
            # No previous data, all changes are +0
            for activity_name in self.activities.keys():
                changes[activity_name] = 0
            return changes
        
        # Compare current vs previous
        for activity_name, activity_stats in self.activities.items():
            current_count = activity_stats.total_episodes
            previous_count = previous_snapshot.episodes_by_activity.get(activity_name, 0)
            changes[activity_name] = current_count - previous_count
        
        return changes
    
    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        parts = [
            f"Found {self.total_activities} activities",
            f"{self.total_episodes_on_disk} episodes on disk"
        ]
        
        # Add disk delta if we have previous data
        disk_delta = self.get_disk_delta()
        if self.total_episodes_on_disk_previous > 0:
            if disk_delta > 0:
                parts.append(f"(+{disk_delta} since last run)")
            elif disk_delta < 0:
                parts.append(f"({disk_delta} since last run)")
            else:
                parts.append("(no change)")
        else:
            parts.append("(+0)")
        
        parts.append(f"{self.total_subscriptions_in_yaml} subscriptions in YAML")
        
        # Add subscriptions delta if we have previous data
        subs_delta = self.get_subscriptions_delta()
        if self.total_subscriptions_in_yaml_previous > 0:
            if subs_delta > 0:
                parts.append(f"(+{subs_delta} since last run)")
            elif subs_delta < 0:
                parts.append(f"({subs_delta} since last run)")
            else:
                parts.append("(no change)")
        else:
            parts.append("(+0)")
        
        parts.append(f"{self.existing_class_ids_count} unique class IDs")
        
        return " - ".join(parts)
    
    def get_detailed_breakdown(self) -> str:
        """Generate a detailed breakdown by activity and season showing episode counts vs highest episode numbers."""
        if not self.activities:
            return "No activity data available"
        
        lines = ["Detailed Episode Breakdown:"]
        
        for activity_name, activity_stats in sorted(self.activities.items()):
            lines.append(f"  {activity_stats.get_summary()}")
            
            # Show season details if available
            if activity_stats.seasons:
                for season_num, season_stats in sorted(activity_stats.seasons.items()):
                    sync_status = "✅" if season_stats.is_synchronized() else "⚠️"
                    lines.append(
                        f"    S{season_num}: {season_stats.episode_count} episodes, "
                        f"highest E{season_stats.highest_episode_number} ({sync_status})"
                    )
        
        return "\n".join(lines)


@dataclass
class ActivityScrapingStats:
    """Scraping statistics for a single activity."""
    
    activity: str
    classes_found: int = 0
    classes_skipped: int = 0
    classes_added: int = 0
    errors: int = 0
    status: str = "pending"  # pending, completed, failed
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if data['error_message'] is None:
            del data['error_message']
        return data


@dataclass
class WebScrapingMetrics:
    """Metrics collected during web scraping stage."""
    
    total_activities_scraped: int = 0
    total_classes_found: int = 0
    total_classes_found_previous: int = 0  # From last run
    total_classes_skipped: int = 0
    total_classes_added: int = 0
    total_errors: int = 0
    page_scrolls_config: int = 0  # Configuration value used
    activities: Dict[str, ActivityScrapingStats] = field(default_factory=dict)
    activity_totals: Dict[str, int] = field(default_factory=dict)  # activity -> total episodes after scraping
    activity_totals_previous: Dict[str, int] = field(default_factory=dict)  # activity -> total from last run
    class_limit_per_activity: int = 0  # Configuration value
    activities_over_limit: List[str] = field(default_factory=list)  # Activities that exceeded limit
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'total_activities_scraped': self.total_activities_scraped,
            'total_classes_found': self.total_classes_found,
            'total_classes_found_previous': self.total_classes_found_previous,
            'total_classes_skipped': self.total_classes_skipped,
            'total_classes_added': self.total_classes_added,
            'total_errors': self.total_errors,
            'page_scrolls_config': self.page_scrolls_config,
            'class_limit_per_activity': self.class_limit_per_activity,
            'activities_over_limit': self.activities_over_limit,
            'activities': {k: v.to_dict() for k, v in self.activities.items()},
            'activity_totals': self.activity_totals,
            'activity_totals_previous': self.activity_totals_previous
        }
    
    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        if self.total_activities_scraped == 0:
            return "No activities scraped"
        
        parts = [
            f"Scraped {self.total_activities_scraped} activities (page_scrolls={self.page_scrolls_config})",
            f"{self.total_classes_found} classes found"
        ]
        
        if self.total_classes_found_previous > 0:
            delta = self.total_classes_found - self.total_classes_found_previous
            if delta > 0:
                parts.append(f"(+{delta} vs last run)")
            elif delta < 0:
                parts.append(f"({delta} vs last run)")
        
        parts.append(f"{self.total_classes_skipped} skipped")
        parts.append(f"{self.total_classes_added} added")
        
        if self.activities_over_limit:
            parts.append(f"⚠️  {len(self.activities_over_limit)} activities over limit")
        
        if self.total_errors > 0:
            parts.append(f"{self.total_errors} errors")
        
        return " - ".join(parts)


@dataclass
class SubscriptionChangesMetrics:
    """Metrics for changes made to subscriptions.yaml."""
    
    subscriptions_removed_already_downloaded: int = 0
    subscriptions_removed_stale: int = 0
    subscriptions_added_new: int = 0
    subscription_directories_updated: int = 0
    subscription_titles_sanitized: int = 0
    subscription_conflicts_resolved: int = 0
    subscriptions_before_cleanup: int = 0  # Count before any removals
    subscriptions_after_cleanup: int = 0   # Count after removals
    subscriptions_after_cleanup_by_activity: Dict[str, int] = field(default_factory=dict)  # activity -> count after cleanup
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        changes = []
        
        if self.subscriptions_before_cleanup > 0:
            changes.append(f"File started with {self.subscriptions_before_cleanup} subscriptions")
        
        if self.subscriptions_removed_already_downloaded > 0:
            changes.append(f"Removed {self.subscriptions_removed_already_downloaded} because they were found on disk")
        if self.subscriptions_removed_stale > 0:
            changes.append(f"Removed {self.subscriptions_removed_stale} because they expired")
        if self.subscriptions_added_new > 0:
            changes.append(f"{self.subscriptions_added_new} new added")
        if self.subscription_directories_updated > 0:
            changes.append(f"{self.subscription_directories_updated} directories updated")
        if self.subscription_titles_sanitized > 0:
            changes.append(f"{self.subscription_titles_sanitized} titles sanitized")
        if self.subscription_conflicts_resolved > 0:
            changes.append(f"{self.subscription_conflicts_resolved} conflicts resolved")
        
        if self.subscriptions_after_cleanup > 0:
            changes.append(f"{self.subscriptions_after_cleanup} subscriptions remain in the base file")
        
        if not changes:
            return "No changes to subscriptions.yaml"
        
        return " - ".join(changes)


@dataclass
class SubscriptionHistoryMetrics:
    """Metrics for subscription history tracking."""
    
    total_tracked_subscriptions: int = 0
    subscriptions_added_to_history: int = 0
    subscriptions_removed_from_history: int = 0
    stale_subscriptions_found: int = 0
    subscriptions_near_purge_limit: int = 0  # Within warning threshold
    purge_limit_days: int = 15  # Config value
    warning_threshold_days: int = 3  # Config value
    history_synced: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def get_summary(self) -> str:
        """Generate a human-readable summary."""
        parts = [f"Tracking {self.total_tracked_subscriptions} subscriptions"]
        
        if self.subscriptions_added_to_history > 0:
            parts.append(f"{self.subscriptions_added_to_history} added")
        if self.subscriptions_removed_from_history > 0:
            parts.append(f"{self.subscriptions_removed_from_history} removed")
        if self.stale_subscriptions_found > 0:
            parts.append(f"{self.stale_subscriptions_found} stale (>{self.purge_limit_days} days)")
        if self.subscriptions_near_purge_limit > 0:
            parts.append(f"⚠️  {self.subscriptions_near_purge_limit} within {self.warning_threshold_days} days of purge")
        
        return " - ".join(parts)


@dataclass
class RunMetrics:
    """Complete metrics for a single application run."""
    
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    # Stage metrics
    directory_repair: DirectoryRepairMetrics = field(default_factory=DirectoryRepairMetrics)
    existing_episodes: ExistingEpisodesMetrics = field(default_factory=ExistingEpisodesMetrics)
    web_scraping: WebScrapingMetrics = field(default_factory=WebScrapingMetrics)
    subscription_changes: SubscriptionChangesMetrics = field(default_factory=SubscriptionChangesMetrics)
    subscription_history: SubscriptionHistoryMetrics = field(default_factory=SubscriptionHistoryMetrics)
    
    # Overall status
    success: bool = True
    error_message: Optional[str] = None
    
    def finalize(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark the run as complete and set final status."""
        self.end_time = datetime.now().isoformat()
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'run_id': self.run_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'success': self.success,
            'error_message': self.error_message,
            'directory_repair': self.directory_repair.to_dict(),
            'existing_episodes': self.existing_episodes.to_dict(),
            'web_scraping': self.web_scraping.to_dict(),
            'subscription_changes': self.subscription_changes.to_dict(),
            'subscription_history': self.subscription_history.to_dict()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary(self) -> str:
        """Generate a complete summary of the run."""
        lines = [
            f"Run Summary ({self.run_id})",
            "=" * 60,
            "",
            "Directory Repair:",
            f"  {self.directory_repair.get_summary()}",
            "",
            "Existing Episodes:",
            f"  {self.existing_episodes.get_summary()}",
            "",
            "Web Scraping:",
            f"  {self.web_scraping.get_summary()}",
            "",
            "Subscription Changes:",
            f"  {self.subscription_changes.get_summary()}",
            "",
            "Subscription History:",
            f"  {self.subscription_history.get_summary()}",
            "",
            "=" * 60
        ]
        
        if not self.success and self.error_message:
            lines.extend(["", f"ERROR: {self.error_message}"])
        
        return "\n".join(lines)
    
    def get_detailed_summary(self) -> str:
        """Generate a complete summary with detailed episode breakdown."""
        lines = [
            f"Run Summary ({self.run_id})",
            "=" * 60,
            "",
            "Directory Repair:",
            f"  {self.directory_repair.get_summary()}",
            "",
            "Existing Episodes:",
            f"  {self.existing_episodes.get_summary()}",
            "",
            f"  {self.existing_episodes.get_detailed_breakdown()}",
            "",
            "Web Scraping:",
            f"  {self.web_scraping.get_summary()}",
            "",
            "Subscription Changes:",
            f"  {self.subscription_changes.get_summary()}",
            "",
            "Subscription History:",
            f"  {self.subscription_history.get_summary()}",
            "",
            "=" * 60
        ]
        
        if not self.success and self.error_message:
            lines.extend(["", f"ERROR: {self.error_message}"])
        
        return "\n".join(lines)
    
    def get_pr_summary(self) -> str:
        """Generate a formatted summary for GitHub PR description."""
        lines = [
            "## Subscription Update Summary",
            "",
            f"**Run ID:** `{self.run_id}`",
            f"**Timestamp:** {self.start_time}",
            "",
            "### Configuration",
            "",
            f"- **Class limit per activity:** {self.web_scraping.class_limit_per_activity}",
            f"- **Page scrolls:** {self.web_scraping.page_scrolls_config}",
            f"- **Activities:** {len(self.web_scraping.activities)} scraped",
            "",
            "### Changes Made",
            ""
        ]
        
        # Subscription File Summary
        lines.extend([
            "### Subscription File Summary",
            ""
        ])
        
        # High-level subscription metrics
        if self.subscription_changes.subscriptions_before_cleanup > 0:
            lines.append(f"- **File started with {self.subscription_changes.subscriptions_before_cleanup} subscriptions**")
        
        removals = []
        if self.subscription_changes.subscriptions_removed_already_downloaded > 0:
            removals.append(f"{self.subscription_changes.subscriptions_removed_already_downloaded} because they were found on disk")
        if self.subscription_changes.subscriptions_removed_stale > 0:
            removals.append(f"{self.subscription_changes.subscriptions_removed_stale} because they expired")
        
        if removals:
            lines.append(f"- **Removed {', '.join(removals)}**")
        
        if self.subscription_changes.subscriptions_after_cleanup > 0:
            lines.append(f"- **{self.subscription_changes.subscriptions_after_cleanup} subscriptions remain in the base file**")
        
        lines.append("")
        
        # Subscription File Activity Breakdown with existing + added + total
        if self.web_scraping.total_classes_added > 0:
            lines.extend([
                "### Subscription File Activity Breakdown",
                ""
            ])
            
            # Activity breakdown with existing + added + total + limit status
            # Show all activities that have subscriptions (either existing or newly added)
            all_activities_with_subscriptions = set()
            
            # Add activities that have existing subscriptions
            all_activities_with_subscriptions.update(self.subscription_changes.subscriptions_after_cleanup_by_activity.keys())
            
            # Add activities that had new classes added
            for activity_name, stats in self.web_scraping.activities.items():
                if stats.classes_added > 0:
                    all_activities_with_subscriptions.add(activity_name.lower())
            
            # Generate breakdown for all activities with subscriptions
            for activity_name in sorted(all_activities_with_subscriptions):
                # Get existing count from subscriptions that remained after cleanup
                existing_count = self.subscription_changes.subscriptions_after_cleanup_by_activity.get(activity_name, 0)
                
                # Get added count from scraping stats
                added_count = 0
                classes_found = 0
                classes_skipped = 0
                if activity_name in self.web_scraping.activities:
                    stats = self.web_scraping.activities[activity_name]
                    added_count = stats.classes_added
                    classes_found = stats.classes_found
                    classes_skipped = stats.classes_skipped
                
                # Total count is existing + added
                new_total = existing_count + added_count
                
                # Check if at limit
                limit_status = "✅" if new_total == self.web_scraping.class_limit_per_activity else "⚠️"
                
                # Only show scraping details if there was scraping activity
                scraping_details = f" ({classes_found} scraped, {classes_skipped} skipped by scraper)" if classes_found > 0 else ""
                
                lines.append(
                    f"- **{activity_name}:** {existing_count} existing, {added_count} added, {new_total} total {limit_status}{scraping_details}"
                )
            
            lines.append("")
            
            # Calculate total subscriptions after scraper updates
            total_after_scraper = self.subscription_changes.subscriptions_after_cleanup + self.web_scraping.total_classes_added
            lines.extend([
                f"**After scraper updates, we are now tracking {total_after_scraper} subscriptions**",
                ""
            ])
        else:
            lines.extend([
                "- No new classes found",
                ""
            ])
        
        # Current state with detailed breakdown
        lines.extend([
            "### Current State",
            "",
        ])
        
        # Episodes on disk with detailed breakdown
        disk_delta = self.existing_episodes.get_disk_delta()
        if self.existing_episodes.total_episodes_on_disk_previous > 0:
            if disk_delta > 0:
                disk_change = f" (+{disk_delta})"
            elif disk_delta < 0:
                disk_change = f" ({disk_delta})"
            else:
                disk_change = " (no change)"
        else:
            disk_change = " (+0)"
        
        lines.append(f"- **Episodes on disk:** {self.existing_episodes.total_episodes_on_disk}{disk_change}")
        
        # Break down episodes on disk by activity with change tracking
        if self.existing_episodes.activities:
            episode_changes = self.existing_episodes.get_episode_changes_by_activity(self.existing_episodes.previous_snapshot)
            for activity_name, activity_stats in sorted(self.existing_episodes.activities.items()):
                change = episode_changes.get(activity_name, 0)
                if change > 0:
                    change_str = f" (+{change})"
                elif change < 0:
                    change_str = f" ({change})"
                else:
                    change_str = " (no change)" if self.existing_episodes.previous_snapshot else " (+0)"
                
                lines.append(f"  - {activity_name}: {activity_stats.total_episodes} episodes{change_str}")
                if activity_stats.seasons:
                    for season_num, season_stats in sorted(activity_stats.seasons.items()):
                        sync_status = "✅" if season_stats.is_synchronized() else "⚠️"
                        lines.append(f"    - S{season_num}: {season_stats.episode_count} episodes, highest E{season_stats.highest_episode_number} {sync_status}")
        
        lines.append("")
        
        # Subscriptions in YAML with detailed breakdown
        total_subs = self.existing_episodes.total_subscriptions_in_yaml + self.web_scraping.total_classes_added
        subs_delta = self.existing_episodes.get_subscriptions_delta()
        if self.existing_episodes.total_subscriptions_in_yaml_previous > 0:
            if subs_delta > 0:
                subs_change = f" (+{subs_delta})"
            elif subs_delta < 0:
                subs_change = f" ({subs_delta})"
            else:
                subs_change = " (no change)"
        else:
            subs_change = " (+0)"
        
        lines.append(f"- **Subscriptions in YAML:** {total_subs}{subs_change}")
        
        # Break down subscriptions by activity and flag limit violations
        if self.web_scraping.activities:
            for activity_name, activity_stats in sorted(self.web_scraping.activities.items()):
                # Get subscription count for this activity
                activity_sub_count = self.web_scraping.activity_totals.get(activity_name, 0)
                limit_warning = ""
                if activity_name in self.web_scraping.activities_over_limit:
                    limit_warning = " **OVER LIMIT**"
                lines.append(f"  - {activity_name}: {activity_sub_count} subscriptions{limit_warning}")
        
        lines.append("")
        
        # Activities with episodes on disk
        lines.append(f"- **Activities with episodes on disk:** {self.existing_episodes.total_activities}")
        if self.existing_episodes.activities:
            activity_names = sorted(self.existing_episodes.activities.keys())
            lines.append(f"  - {', '.join(activity_names)}")
        
        lines.append("")
        
        # Directory repairs (always show)
        lines.extend([
            "### Directory Validation",
            "",
            f"- {self.directory_repair.get_summary()}",
            ""
        ])
        
        
        lines.extend([
            "---",
            "",
            "*This PR was created automatically by ytdl-sub config manager.*"
        ])
        
        return "\n".join(lines)
    
    def create_snapshot(self) -> RunSnapshot:
        """Create a snapshot of key metrics for historical tracking."""
        # Create episodes by activity mapping
        episodes_by_activity = {}
        for activity_name, activity_stats in self.existing_episodes.activities.items():
            episodes_by_activity[activity_name] = activity_stats.total_episodes
        
        return RunSnapshot(
            run_timestamp=self.start_time,
            videos_on_disk=self.existing_episodes.total_episodes_on_disk,
            videos_in_subscriptions=self.existing_episodes.total_subscriptions_in_yaml + self.web_scraping.total_classes_added,
            new_videos_added=self.web_scraping.total_classes_added,
            total_activities=self.existing_episodes.total_activities,
            episodes_by_activity=episodes_by_activity
        )

