"""Subscription history manager for tracking subscription IDs and their creation dates."""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set, List, Optional
from dataclasses import dataclass

from ..core.logging import get_logger
from ..core.snapshot import RunSnapshot

logger = get_logger(__name__)


@dataclass
class SubscriptionEntry:
    """Represents a subscription entry in the history file."""
    id: str
    date_added: str  # ISO format date string
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'date_added': self.date_added
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'SubscriptionEntry':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            date_added=data['date_added']
        )


class SubscriptionHistoryManager:
    """Manages subscription history tracking in a flat file."""
    
    def __init__(self, subs_file_path: str, timeout_days: int = 15):
        """Initialize the subscription history manager.
        
        Args:
            subs_file_path: Path to the subscriptions YAML file
            timeout_days: Number of days after which subscriptions are considered stale
        """
        self.subs_file_path = Path(subs_file_path)
        self.timeout_days = timeout_days
        
        # Create history file path in the same directory as subs file
        self.history_file_path = self.subs_file_path.parent / "subscription-history.json"
        
        self.logger = get_logger(__name__)
    
    def _load_history(self) -> Dict[str, SubscriptionEntry]:
        """Load subscription history from file.
        
        Returns:
            Dictionary mapping subscription ID to SubscriptionEntry
        """
        if not self.history_file_path.exists():
            self.logger.info(f"Subscription history file does not exist, creating: {self.history_file_path}")
            # Create empty history file
            self._save_history({})
            return {}
        
        try:
            with open(self.history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            history = {}
            for entry_data in data.get('subscriptions', []):
                entry = SubscriptionEntry.from_dict(entry_data)
                history[entry.id] = entry
            
            self.logger.debug(f"Loaded {len(history)} subscription entries from history file")
            return history
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Error loading subscription history file: {e}")
            return {}
    
    def _save_history(self, history: Dict[str, SubscriptionEntry], snapshot = None) -> bool:
        """Save subscription history to file.
        
        Args:
            history: Dictionary mapping subscription ID to SubscriptionEntry
            snapshot: Optional run snapshot to append to history
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing run snapshots if file exists
            existing_snapshots = []
            if self.history_file_path.exists():
                try:
                    with open(self.history_file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        existing_snapshots = existing_data.get('run_snapshots', [])
                except Exception as e:
                    self.logger.warning(f"Could not load existing run snapshots: {e}")
            
            # Convert to list format for JSON
            subscriptions = [entry.to_dict() for entry in history.values()]
            data = {
                'subscriptions': subscriptions,
                'last_updated': datetime.now().isoformat(),
                'run_snapshots': existing_snapshots
            }
            
            # Append new snapshot if provided
            if snapshot:
                data['run_snapshots'].append(snapshot.to_dict())
                # Keep only the last 50 snapshots to avoid unbounded growth
                data['run_snapshots'] = data['run_snapshots'][-50:]
            
            with open(self.history_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved {len(history)} subscription entries to history file")
            if snapshot:
                self.logger.info(f"Saved run snapshot to history file")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving subscription history file: {e}")
            return False
    
    def get_stale_subscription_ids(self) -> Set[str]:
        """Get subscription IDs that are older than the timeout period.
        
        Returns:
            Set of stale subscription IDs
        """
        history = self._load_history()
        cutoff_date = datetime.now() - timedelta(days=self.timeout_days)
        stale_ids = set()
        
        for entry in history.values():
            try:
                entry_date = datetime.fromisoformat(entry.date_added)
                if entry_date < cutoff_date:
                    stale_ids.add(entry.id)
            except ValueError as e:
                self.logger.warning(f"Invalid date format in history entry {entry.id}: {e}")
                # Consider entries with invalid dates as stale
                stale_ids.add(entry.id)
        
        if stale_ids:
            self.logger.info(f"Found {len(stale_ids)} stale subscription IDs (older than {self.timeout_days} days)")
        else:
            self.logger.info("No stale subscription IDs found")
        
        return stale_ids
    
    def get_subscriptions_near_timeout(self, warning_threshold_days: int = 3) -> Set[str]:
        """Get subscription IDs that are within N days of the timeout period.
        
        Args:
            warning_threshold_days: Number of days before timeout to warn about
            
        Returns:
            Set of subscription IDs approaching timeout
        """
        history = self._load_history()
        warning_cutoff = datetime.now() - timedelta(days=self.timeout_days - warning_threshold_days)
        timeout_cutoff = datetime.now() - timedelta(days=self.timeout_days)
        near_timeout_ids = set()
        
        for entry in history.values():
            try:
                entry_date = datetime.fromisoformat(entry.date_added)
                # Include entries between warning threshold and timeout
                if entry_date < warning_cutoff and entry_date >= timeout_cutoff:
                    near_timeout_ids.add(entry.id)
            except ValueError:
                # Skip entries with invalid dates
                continue
        
        if near_timeout_ids:
            self.logger.info(f"Found {len(near_timeout_ids)} subscriptions within {warning_threshold_days} days of timeout")
        
        return near_timeout_ids
    
    def add_subscription_ids(self, subscription_ids: Set[str]) -> bool:
        """Add new subscription IDs to the history file.
        
        Args:
            subscription_ids: Set of subscription IDs to add
            
        Returns:
            True if successful, False otherwise
        """
        if not subscription_ids:
            return True
        
        history = self._load_history()
        today = datetime.now().isoformat()
        added_count = 0
        
        for sub_id in subscription_ids:
            if sub_id not in history:
                history[sub_id] = SubscriptionEntry(id=sub_id, date_added=today)
                added_count += 1
        
        if added_count > 0:
            self.logger.info(f"Adding {added_count} new subscription IDs to history")
            return self._save_history(history, snapshot=None)
        else:
            self.logger.debug("No new subscription IDs to add to history")
            return True
    
    def remove_subscription_ids(self, subscription_ids: Set[str]) -> bool:
        """Remove subscription IDs from the history file.
        
        Args:
            subscription_ids: Set of subscription IDs to remove
            
        Returns:
            True if successful, False otherwise
        """
        if not subscription_ids:
            return True
        
        history = self._load_history()
        removed_count = 0
        
        for sub_id in subscription_ids:
            if sub_id in history:
                del history[sub_id]
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Removing {removed_count} subscription IDs from history")
            return self._save_history(history, snapshot=None)
        else:
            self.logger.debug("No subscription IDs to remove from history")
            return True
    
    def extract_subscription_ids_from_urls(self, urls: List[str]) -> Set[str]:
        """Extract subscription IDs from Peloton class URLs.
        
        Args:
            urls: List of Peloton class URLs
            
        Returns:
            Set of extracted subscription IDs
        """
        subscription_ids = set()
        
        for url in urls:
            # Extract ID from URLs like: https://members.onepeloton.com/classes/player/0c3a783d638940d5826b3173729781df
            if '/classes/player/' in url:
                try:
                    # Split by '/classes/player/' and take the last part
                    id_part = url.split('/classes/player/')[-1]
                    # Remove any query parameters or fragments
                    subscription_id = id_part.split('?')[0].split('#')[0]
                    if subscription_id:
                        subscription_ids.add(subscription_id)
                except Exception as e:
                    self.logger.warning(f"Failed to extract ID from URL {url}: {e}")
        
        return subscription_ids
    
    def get_all_tracked_ids(self) -> Set[str]:
        """Get all currently tracked subscription IDs.
        
        Returns:
            Set of all tracked subscription IDs
        """
        history = self._load_history()
        return set(history.keys())
    
    def sync_existing_subscriptions(self) -> bool:
        """Sync subscription IDs between subscriptions.yaml and history file.
        
        This ensures the history file accurately reflects the current state of subscriptions.yaml:
        - Adds new subscription IDs from subscriptions.yaml to history
        - Removes subscription IDs from history that are no longer in subscriptions.yaml
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import yaml
            
            # Load current history
            current_history = self._load_history()
            current_tracked_ids = set(current_history.keys())
            
            # Load subscriptions file
            if not self.subs_file_path.exists():
                self.logger.info("No subscriptions file found to sync - clearing all history")
                # If no subscriptions file exists, clear all history
                if current_tracked_ids:
                    self.logger.info(f"Removing {len(current_tracked_ids)} subscription IDs from history (no subscriptions file)")
                    return self._save_history({})
                return True
            
            with open(self.subs_file_path, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
            
            if not subs_data or "Plex TV Show by Date" not in subs_data:
                self.logger.info("No subscription data found to sync - clearing all history")
                # If no subscription data exists, clear all history
                if current_tracked_ids:
                    self.logger.info(f"Removing {len(current_tracked_ids)} subscription IDs from history (no subscription data)")
                    return self._save_history({})
                return True
            
            # Extract all subscription URLs from the subscriptions file
            subscription_urls = []
            for duration_key, episodes in subs_data["Plex TV Show by Date"].items():
                if not isinstance(episodes, dict):
                    continue
                
                for episode_title, episode_data in episodes.items():
                    if not isinstance(episode_data, dict):
                        continue
                    
                    download_url = episode_data.get("download", "")
                    if download_url:
                        subscription_urls.append(download_url)
            
            # Extract subscription IDs from URLs
            current_subscription_ids = self.extract_subscription_ids_from_urls(subscription_urls)
            
            # Find IDs to add (in subscriptions but not in history)
            ids_to_add = current_subscription_ids - current_tracked_ids
            
            # Find IDs to remove (in history but not in subscriptions)
            ids_to_remove = current_tracked_ids - current_subscription_ids
            
            # Apply changes - ADD FIRST, then REMOVE
            changes_made = False
            
            # Step 1: Add missing subscription IDs to history first
            if ids_to_add:
                self.logger.info(f"Adding {len(ids_to_add)} new subscription IDs to history")
                if self.add_subscription_ids(ids_to_add):
                    changes_made = True
                else:
                    self.logger.error("Failed to add new subscription IDs to history")
                    return False
            
            # Step 2: Remove subscription IDs that are no longer in subscriptions
            if ids_to_remove:
                self.logger.info(f"Removing {len(ids_to_remove)} subscription IDs from history (no longer in subscriptions)")
                if self.remove_subscription_ids(ids_to_remove):
                    changes_made = True
                else:
                    self.logger.error("Failed to remove subscription IDs from history")
                    return False
            
            if not changes_made:
                self.logger.debug("History file is already in sync with subscriptions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing existing subscriptions: {e}")
            return False
    
    def save_run_snapshot(self, snapshot) -> bool:
        """Save a run snapshot to the history file.
        
        Args:
            snapshot: Run snapshot to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current history
            history = self._load_history()
            
            # Save with snapshot
            return self._save_history(history, snapshot=snapshot)
            
        except Exception as e:
            self.logger.error(f"Error saving run snapshot: {e}")
            return False
    
    def get_run_snapshots(self, limit: int = 10):
        """Get the most recent run snapshots from history.
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of run snapshots (most recent first)
        """
        try:
            if not self.history_file_path.exists():
                return []
            
            with open(self.history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            snapshots_data = data.get('run_snapshots', [])
            snapshots = [RunSnapshot.from_dict(s) for s in snapshots_data]
            
            # Return most recent first
            return snapshots[-limit:][::-1]
            
        except Exception as e:
            self.logger.error(f"Error loading run snapshots: {e}")
            return []
    
    def get_last_run_snapshot(self):
        """Get the most recent run snapshot.
        
        Returns:
            Last run snapshot or None if no snapshots exist
        """
        snapshots = self.get_run_snapshots(limit=1)
        return snapshots[0] if snapshots else None
