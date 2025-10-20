"""Tests for subscription history manager."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from src.io.subscription_history_manager import SubscriptionHistoryManager, SubscriptionEntry


class TestSubscriptionEntry:
    """Test SubscriptionEntry dataclass."""
    
    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = SubscriptionEntry(
            id="test-id-123",
            date_added="2024-01-15T10:30:00"
        )
        
        result = entry.to_dict()
        
        assert result == {
            'id': 'test-id-123',
            'date_added': '2024-01-15T10:30:00'
        }
    
    def test_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            'id': 'test-id-456',
            'date_added': '2024-01-16T14:45:00'
        }
        
        entry = SubscriptionEntry.from_dict(data)
        
        assert entry.id == 'test-id-456'
        assert entry.date_added == '2024-01-16T14:45:00'


class TestSubscriptionHistoryManager:
    """Test SubscriptionHistoryManager class."""
    
    def test_init(self):
        """Test initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(
                subs_file_path=str(subs_file),
                timeout_days=10
            )
            
            assert manager.subs_file_path == subs_file
            assert manager.timeout_days == 10
            assert manager.history_file_path == subs_file.parent / "subscription-history.json"
    
    def test_init_default_timeout(self):
        """Test initialization with default timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            assert manager.timeout_days == 15
            assert manager.retention_days == 14
    
    def test_init_with_retention_days(self):
        """Test initialization with custom retention days."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file), timeout_days=30, retention_days=7)
            
            assert manager.timeout_days == 30
            assert manager.retention_days == 7
    
    def test_load_history_file_not_exists(self):
        """Test loading history when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            history = manager._load_history()
            
            assert history == {}
    
    def test_load_history_valid_file(self):
        """Test loading history from valid file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            # Create history file
            history_file = subs_file.parent / "subscription-history.json"
            history_data = {
                'subscriptions': [
                    {'id': 'id1', 'date_added': '2024-01-15T10:00:00'},
                    {'id': 'id2', 'date_added': '2024-01-16T11:00:00'}
                ],
                'last_updated': '2024-01-16T12:00:00'
            }
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f)
            
            manager = SubscriptionHistoryManager(str(subs_file))
            history = manager._load_history()
            
            assert len(history) == 2
            assert 'id1' in history
            assert 'id2' in history
            assert history['id1'].id == 'id1'
            assert history['id1'].date_added == '2024-01-15T10:00:00'
    
    def test_load_history_invalid_json(self):
        """Test loading history from invalid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            # Create invalid history file
            history_file = subs_file.parent / "subscription-history.json"
            with open(history_file, 'w') as f:
                f.write("invalid json content")
            
            manager = SubscriptionHistoryManager(str(subs_file))
            history = manager._load_history()
            
            assert history == {}
    
    def test_save_history(self):
        """Test saving history to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-15T10:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-16T11:00:00')
            }
            
            result = manager._save_history(history)
            
            assert result is True
            assert manager.history_file_path.exists()
            
            # Verify file content
            with open(manager.history_file_path, 'r') as f:
                data = json.load(f)
            
            assert len(data['subscriptions']) == 2
            assert 'last_updated' in data
            subscription_ids = [sub['id'] for sub in data['subscriptions']]
            assert 'id1' in subscription_ids
            assert 'id2' in subscription_ids
    
    def test_save_history_error(self):
        """Test saving history with error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock the open function to raise an exception
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                history = {
                    'id1': SubscriptionEntry(id='id1', date_added='2024-01-15T10:00:00')
                }
                
                result = manager._save_history(history)
                
                assert result is False
    
    def test_get_stale_subscription_ids_no_stale(self):
        """Test getting stale IDs when none are stale."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file), timeout_days=30)
            
            # Create recent history
            history = {
                'id1': SubscriptionEntry(
                    id='id1', 
                    date_added=(datetime.now() - timedelta(days=10)).isoformat()
                ),
                'id2': SubscriptionEntry(
                    id='id2', 
                    date_added=(datetime.now() - timedelta(days=5)).isoformat()
                )
            }
            
            with patch.object(manager, '_load_history', return_value=history):
                stale_ids = manager.get_stale_subscription_ids()
                
                assert stale_ids == set()
    
    def test_get_stale_subscription_ids_with_stale(self):
        """Test getting stale IDs when some are stale."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file), timeout_days=10)
            
            # Create mixed history (some stale, some not)
            history = {
                'id1': SubscriptionEntry(
                    id='id1', 
                    date_added=(datetime.now() - timedelta(days=15)).isoformat()  # Stale
                ),
                'id2': SubscriptionEntry(
                    id='id2', 
                    date_added=(datetime.now() - timedelta(days=5)).isoformat()   # Not stale
                ),
                'id3': SubscriptionEntry(
                    id='id3', 
                    date_added=(datetime.now() - timedelta(days=20)).isoformat()  # Stale
                )
            }
            
            with patch.object(manager, '_load_history', return_value=history):
                stale_ids = manager.get_stale_subscription_ids()
                
                assert stale_ids == {'id1', 'id3'}
    
    def test_get_stale_subscription_ids_invalid_date(self):
        """Test getting stale IDs with invalid date format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file), timeout_days=10)
            
            # Create history with invalid date
            history = {
                'id1': SubscriptionEntry(id='id1', date_added='invalid-date'),
                'id2': SubscriptionEntry(
                    id='id2', 
                    date_added=(datetime.now() - timedelta(days=5)).isoformat()
                )
            }
            
            with patch.object(manager, '_load_history', return_value=history):
                stale_ids = manager.get_stale_subscription_ids()
                
                # Invalid dates should be considered stale
                assert stale_ids == {'id1'}
    
    def test_add_subscription_ids_new_ids(self):
        """Test adding new subscription IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock existing history
            existing_history = {
                'existing_id': SubscriptionEntry(
                    id='existing_id', 
                    date_added='2024-01-01T00:00:00'
                )
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, '_save_history', return_value=True) as mock_save:
                
                new_ids = {'new_id1', 'new_id2'}
                result = manager.add_subscription_ids(new_ids)
                
                assert result is True
                mock_save.assert_called_once()
                
                # Verify the history passed to save includes new IDs
                call_args = mock_save.call_args[0][0]
                assert 'existing_id' in call_args
                assert 'new_id1' in call_args
                assert 'new_id2' in call_args
    
    def test_add_subscription_ids_no_new_ids(self):
        """Test adding subscription IDs when none are new."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock existing history
            existing_history = {
                'existing_id': SubscriptionEntry(
                    id='existing_id', 
                    date_added='2024-01-01T00:00:00'
                )
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, '_save_history', return_value=True) as mock_save:
                
                new_ids = {'existing_id'}  # Already exists
                result = manager.add_subscription_ids(new_ids)
                
                assert result is True
                mock_save.assert_not_called()
    
    def test_add_subscription_ids_empty_set(self):
        """Test adding empty set of subscription IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            with patch.object(manager, '_load_history'), \
                 patch.object(manager, '_save_history') as mock_save:
                
                result = manager.add_subscription_ids(set())
                
                assert result is True
                mock_save.assert_not_called()
    
    def test_remove_subscription_ids(self):
        """Test removing subscription IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock existing history
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-02T00:00:00'),
                'id3': SubscriptionEntry(id='id3', date_added='2024-01-03T00:00:00')
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, '_save_history', return_value=True) as mock_save:
                
                ids_to_remove = {'id1', 'id3'}
                result = manager.remove_subscription_ids(ids_to_remove)
                
                assert result is True
                mock_save.assert_called_once()
                
                # Verify the history passed to save excludes removed IDs
                call_args = mock_save.call_args[0][0]
                assert 'id1' not in call_args
                assert 'id2' in call_args
                assert 'id3' not in call_args
    
    def test_remove_subscription_ids_empty_set(self):
        """Test removing empty set of subscription IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            with patch.object(manager, '_load_history'), \
                 patch.object(manager, '_save_history') as mock_save:
                
                result = manager.remove_subscription_ids(set())
                
                assert result is True
                mock_save.assert_not_called()
    
    def test_extract_subscription_ids_from_urls(self):
        """Test extracting subscription IDs from Peloton URLs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            urls = [
                "https://members.onepeloton.com/classes/player/0c3a783d638940d5826b3173729781df",
                "https://members.onepeloton.com/classes/player/1d4b894e749051e6937c4284830892ef?param=value",
                "https://members.onepeloton.com/classes/player/2e5c905f85a162f7048d5395941903fg#fragment",
                "https://members.onepeloton.com/classes/player/3f6d016f96b273g8159e6406a5014gh",
                "invalid-url",
                "https://members.onepeloton.com/classes/player/",  # No ID
            ]
            
            result = manager.extract_subscription_ids_from_urls(urls)
            
            expected = {
                '0c3a783d638940d5826b3173729781df',
                '1d4b894e749051e6937c4284830892ef',
                '2e5c905f85a162f7048d5395941903fg',
                '3f6d016f96b273g8159e6406a5014gh'
            }
            
            assert result == expected
    
    def test_extract_subscription_ids_from_urls_empty_list(self):
        """Test extracting subscription IDs from empty URL list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            result = manager.extract_subscription_ids_from_urls([])
            
            assert result == set()
    
    def test_get_all_tracked_ids(self):
        """Test getting all tracked subscription IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock existing history
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-02T00:00:00')
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history):
                result = manager.get_all_tracked_ids()
                
                assert result == {'id1', 'id2'}

    def test_sync_existing_subscriptions_add_new(self):
        """Test syncing existing subscriptions - adding new IDs to history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            
            # Create a subscriptions.yaml file with some subscriptions
            subs_data = {
                "Plex TV Show by Date": {
                    "= Cycling (20 min)": {
                        "20 min Ride with Hannah": {
                            "download": "https://members.onepeloton.com/classes/player/id1",
                            "overrides": {"season_number": 20, "episode_number": 1}
                        }
                    },
                    "= Yoga (30 min)": {
                        "30 min Flow with Aditi": {
                            "download": "https://members.onepeloton.com/classes/player/id2",
                            "overrides": {"season_number": 30, "episode_number": 1}
                        }
                    }
                }
            }
            
            import yaml
            with open(subs_file, 'w') as f:
                yaml.dump(subs_data, f)
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock empty history (no existing IDs)
            with patch.object(manager, '_load_history', return_value={}), \
                 patch.object(manager, 'add_subscription_ids', return_value=True) as mock_add, \
                 patch.object(manager, 'remove_subscription_ids', return_value=True) as mock_remove:
                
                result = manager.sync_existing_subscriptions()
                
                assert result is True
                mock_add.assert_called_once_with({'id1', 'id2'})
                mock_remove.assert_not_called()

    def test_sync_existing_subscriptions_remove_old(self):
        """Test syncing existing subscriptions - removing IDs no longer in subscriptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            
            # Create a subscriptions.yaml file with only one subscription
            subs_data = {
                "Plex TV Show by Date": {
                    "= Cycling (20 min)": {
                        "20 min Ride with Hannah": {
                            "download": "https://members.onepeloton.com/classes/player/id1",
                            "overrides": {"season_number": 20, "episode_number": 1}
                        }
                    }
                }
            }
            
            import yaml
            with open(subs_file, 'w') as f:
                yaml.dump(subs_data, f)
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock history with IDs that are no longer in subscriptions
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-02T00:00:00'),  # No longer in subscriptions
                'id3': SubscriptionEntry(id='id3', date_added='2024-01-03T00:00:00')   # No longer in subscriptions
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, 'add_subscription_ids', return_value=True) as mock_add, \
                 patch.object(manager, 'remove_subscription_ids', return_value=True) as mock_remove:
                
                result = manager.sync_existing_subscriptions()
                
                assert result is True
                mock_add.assert_not_called()  # id1 already exists
                mock_remove.assert_called_once_with({'id2', 'id3'})

    def test_sync_existing_subscriptions_bidirectional(self):
        """Test syncing existing subscriptions - both adding and removing IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            
            # Create a subscriptions.yaml file with some subscriptions
            subs_data = {
                "Plex TV Show by Date": {
                    "= Cycling (20 min)": {
                        "20 min Ride with Hannah": {
                            "download": "https://members.onepeloton.com/classes/player/id1",
                            "overrides": {"season_number": 20, "episode_number": 1}
                        }
                    },
                    "= Yoga (30 min)": {
                        "30 min Flow with Aditi": {
                            "download": "https://members.onepeloton.com/classes/player/id2",
                            "overrides": {"season_number": 30, "episode_number": 1}
                        }
                    }
                }
            }
            
            import yaml
            with open(subs_file, 'w') as f:
                yaml.dump(subs_data, f)
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock history with some IDs that are no longer in subscriptions
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),  # Still in subscriptions
                'id3': SubscriptionEntry(id='id3', date_added='2024-01-03T00:00:00')   # No longer in subscriptions
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, 'add_subscription_ids', return_value=True) as mock_add, \
                 patch.object(manager, 'remove_subscription_ids', return_value=True) as mock_remove:
                
                result = manager.sync_existing_subscriptions()
                
                assert result is True
                mock_add.assert_called_once_with({'id2'})  # id2 is new
                mock_remove.assert_called_once_with({'id3'})  # id3 is no longer in subscriptions

    def test_sync_existing_subscriptions_no_file(self):
        """Test syncing when subscriptions file doesn't exist - should clear all history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            # Don't create the file
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock history with some IDs
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-02T00:00:00')
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, '_save_history', return_value=True) as mock_save:
                
                result = manager.sync_existing_subscriptions()
                
                assert result is True
                mock_save.assert_called_once_with({})  # Should clear all history

    def test_sync_existing_subscriptions_empty_data(self):
        """Test syncing when subscriptions file has no data - should clear all history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subs_file = Path(temp_dir) / "subscriptions.yaml"
            subs_file.touch()  # Create empty file
            
            manager = SubscriptionHistoryManager(str(subs_file))
            
            # Mock history with some IDs
            existing_history = {
                'id1': SubscriptionEntry(id='id1', date_added='2024-01-01T00:00:00'),
                'id2': SubscriptionEntry(id='id2', date_added='2024-01-02T00:00:00')
            }
            
            with patch.object(manager, '_load_history', return_value=existing_history), \
                 patch.object(manager, '_save_history', return_value=True) as mock_save:
                
                result = manager.sync_existing_subscriptions()
                
                assert result is True
                mock_save.assert_called_once_with({})  # Should clear all history
