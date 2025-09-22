"""50/50 directory repair strategy for Peloton content."""

from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class Repair5050Strategy(DirectoryRepairStrategy):
    """Repair strategy for Peloton's 50/50 directory corruption issue."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is a 50/50 corruption issue that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        path_str = str(path).lower()
        
        # Look for 50/50 patterns that create extra directory levels
        corruption_patterns = [
            "50/50", "/50/", "\\50\\", "50-50", 
            "bootcamp 50", "bootcamp: 50"
        ]
        
        return any(pattern in path_str for pattern in corruption_patterns)
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for 50/50 corruption.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Try to infer the correct location by cleaning up problematic path parts
        path_parts = list(path.parts)
        corrected_parts = []
        
        for part in path_parts:
            # Skip problematic parts that create extra directory levels
            if part in ["50"] or "50/50" in part:
                self.logger.debug(f"Skipping problematic part: {part}")
                continue
                
            # Fix bootcamp names with 50/50 corruption
            if "bootcamp" in part.lower() and "50" in part:
                if "bike" in part.lower():
                    corrected_part = "Bike Bootcamp"
                elif "row" in part.lower():
                    corrected_part = "Row Bootcamp"
                elif "tread" in part.lower():
                    corrected_part = "Bootcamp"
                else:
                    corrected_part = "Bootcamp"
                
                self.logger.debug(f"Correcting bootcamp name: {part} -> {corrected_part}")
                corrected_parts.append(corrected_part)
            else:
                corrected_parts.append(part)
        
        # Generate repair action if we made corrections
        if corrected_parts != list(path.parts):
            target_path = Path(*corrected_parts)
            actions.append(RepairAction(
                action_type="move",
                source_path=path,
                target_path=target_path,
                reason="Fix 50/50 directory corruption"
            ))
            
            self.logger.info(f"Generated repair action: {path} -> {target_path}")
        
        return actions
