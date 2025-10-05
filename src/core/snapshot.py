"""Shared RunSnapshot model."""

from dataclasses import dataclass, asdict, field
from typing import Dict


@dataclass
class RunSnapshot:
    """Snapshot of key metrics for a single run (stored in subscription-history.json)."""
    
    run_timestamp: str
    videos_on_disk: int = 0
    videos_in_subscriptions: int = 0
    new_videos_added: int = 0
    total_activities: int = 0
    episodes_by_activity: Dict[str, int] = field(default_factory=dict)  # activity -> episode count
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RunSnapshot':
        """Create from dictionary."""
        # Handle backward compatibility - episodes_by_activity might not exist in old snapshots
        if 'episodes_by_activity' not in data:
            data['episodes_by_activity'] = {}
        return cls(**data)

