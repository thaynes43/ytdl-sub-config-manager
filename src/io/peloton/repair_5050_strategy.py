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
        """Check if this is a corruption issue that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        path_str = str(path)
        
        # SIMPLE: Check if "50/50" appears ANYWHERE in the entire file path
        # This catches all corruption caused by slashes in "50/50" class names
        if "50/50" in path_str:
            self.logger.debug(f"50/50 strategy detected '50/50' corruption in path: {path}")
            return True
            
        # Check for duplicated episode name corruption
        if self._has_duplicated_episode_name(path):
            self.logger.debug(f"50/50 strategy detected duplicated episode name in: {path}")
            return True
        
        # No corruption detected
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for various corruption patterns.
        
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
        
        i = 0
        while i < len(path_parts):
            part = path_parts[i]
            
            # Skip problematic parts that create extra directory levels
            if part in ["50"] or "50/50" in part:
                self.logger.debug(f"Skipping problematic part: {part}")
                i += 1
                continue
            
            # Handle the case where "50/50" was split by pathlib into ": 50" and "50"
            # Check if current part ends with ": 50" and next part is "50"
            if (i < len(path_parts) - 1 and 
                part.endswith(": 50") and 
                path_parts[i + 1] == "50" and
                "bootcamp" in part.lower()):
                
                # Combine them into ": 50-50"
                corrected_part = part.replace(": 50", ": 50-50")
                self.logger.debug(f"Combining split 50/50: {part} + {path_parts[i + 1]} -> {corrected_part}")
                corrected_parts.append(corrected_part)
                i += 2  # Skip both parts
                continue
                
            # Fix bootcamp names with 50/50 corruption - preserve episode name but clean corruption
            if "bootcamp" in part.lower() and "50" in part:
                # Extract the episode name and clean it up
                corrected_part = self._clean_episode_name(part)
                self.logger.debug(f"Correcting bootcamp name: {part} -> {corrected_part}")
                corrected_parts.append(corrected_part)
            else:
                corrected_parts.append(part)
            
            i += 1
        
        # Handle duplicated episode name corruption
        corrected_parts = self._fix_duplicated_episode_names(corrected_parts)
        
        # Generate repair action if we made corrections
        if corrected_parts != list(path.parts):
            target_path = Path(*corrected_parts)
            
            # Check if target already exists and handle accordingly
            if target_path.exists():
                # If target exists, we need to merge the contents
                # Move the corrupted directory contents to the existing target
                self.logger.info(f"Repairing 50/50 corruption: {path} -> {target_path} (merging contents)")
                
                # Create a special action that the validator can handle
                actions.append(RepairAction(
                    action_type="move_contents",
                    source_path=path,
                    target_path=target_path,
                    reason="Fix directory corruption - move contents to existing directory"
                ))
            else:
                # Normal move operation
                actions.append(RepairAction(
                    action_type="move",
                    source_path=path,
                    target_path=target_path,
                    reason="Fix directory corruption"
                ))
                self.logger.info(f"Repairing 50/50 corruption: {path} -> {target_path}")
        
        return actions
    
    def _clean_episode_name(self, episode_name: str) -> str:
        """Clean up episode name by fixing 50/50 corruption while preserving the episode info.
        
        Args:
            episode_name: Original episode name with corruption
            
        Returns:
            Cleaned episode name
        """
        # Convert "50/50" to "50-50" (this is the correct format)
        cleaned = episode_name.replace(": 50/50", ": 50-50")
        
        # Remove ": 50" suffix that appears in corrupted names (standalone : 50, not : 50-50)
        # But only if it's not part of ": 50-50"
        if ": 50-50" not in cleaned:
            cleaned = cleaned.replace(": 50", "")
        
        # Remove any standalone "50" that might be at the end (but not "50-50")
        if not cleaned.endswith("50-50"):
            cleaned = cleaned.rstrip(" 50")
        
        # Clean up any double spaces that might have been created
        cleaned = cleaned.replace("  ", " ")
        
        return cleaned.strip()
    
    def _has_duplicated_episode_name(self, path: Path) -> bool:
        """Check if the path has duplicated episode names creating extra directory levels.
        
        Args:
            path: Path to check
            
        Returns:
            True if duplicated episode names are detected
        """
        path_parts = list(path.parts)
        
        # Look for consecutive parts that look like episode names
        for i in range(len(path_parts) - 1):
            current_part = path_parts[i]
            next_part = path_parts[i + 1]
            
            # Check if both parts look like episode names (contain episode patterns)
            if (self._looks_like_episode_name(current_part) and 
                self._looks_like_episode_name(next_part)):
                # Check for exact duplicates or similar episode names (same date/activity)
                if (current_part == next_part or 
                    self._are_similar_episodes(current_part, next_part)):
                    return True
                
        return False
    
    def _looks_like_episode_name(self, part: str) -> bool:
        """Check if a path part looks like an episode name.
        
        Args:
            part: Path part to check
            
        Returns:
            True if it looks like an episode name
        """
        # Episode names typically contain patterns like S30E109, dates, and activity info
        episode_patterns = [
            r"S\d+E\d+",  # Season/Episode pattern
            r"\d{8}",      # Date pattern (YYYYMMDD)
            r"\d+\s+min",  # Duration pattern
            "bootcamp", "cycling", "yoga", "strength"  # Activity keywords
        ]
        
        import re
        part_lower = part.lower()
        
        # Check if it contains multiple episode indicators
        pattern_count = 0
        for pattern in episode_patterns:
            if re.search(pattern, part_lower):
                pattern_count += 1
                
        return pattern_count >= 2  # Episode names typically have multiple indicators
    
    def _are_similar_episodes(self, part1: str, part2: str) -> bool:
        """Check if two episode names are similar (same date/activity but different episode numbers).
        
        Args:
            part1: First episode name
            part2: Second episode name
            
        Returns:
            True if episodes are similar
        """
        import re
        
        # Extract date and activity from both parts
        date_pattern = r'(\d{8})'  # YYYYMMDD
        activity_pattern = r'(\d+\s+min\s+\w+)'  # duration and activity
        
        date1 = re.search(date_pattern, part1)
        date2 = re.search(date_pattern, part2)
        activity1 = re.search(activity_pattern, part1.lower())
        activity2 = re.search(activity_pattern, part2.lower())
        
        # Episodes are similar if they have the same date and activity
        return bool(date1 and date2 and date1.group(1) == date2.group(1) and
                   activity1 and activity2 and activity1.group(1) == activity2.group(1))
    
    def _fix_duplicated_episode_names(self, path_parts: List[str]) -> List[str]:
        """Fix duplicated episode names in path parts.
        
        Args:
            path_parts: List of path parts
            
        Returns:
            Corrected path parts with duplicates removed
        """
        corrected_parts = []
        i = 0
        
        while i < len(path_parts):
            current_part = path_parts[i]
            
            # Check if this part is duplicated with the next part
            if (i < len(path_parts) - 1 and 
                self._looks_like_episode_name(current_part) and 
                self._looks_like_episode_name(path_parts[i + 1]) and
                (current_part == path_parts[i + 1] or 
                 self._are_similar_episodes(current_part, path_parts[i + 1]))):
                
                self.logger.debug(f"Removing duplicate/similar episode name: {current_part} / {path_parts[i + 1]}")
                # Skip the duplicate, only add the first occurrence
                corrected_parts.append(current_part)
                i += 2  # Skip both the current and next part
            else:
                corrected_parts.append(current_part)
                i += 1
                
        return corrected_parts
