"""Folder/filename mismatch repair strategy."""

import re
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class FolderFilenameMismatchRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for folder/filename mismatches.
    
    This strategy detects when a folder name doesn't match the video file name inside it
    (minus the extension) and repairs the mismatch by renaming the folder to match the file.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this path has a folder/filename mismatch that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        # Only process directories
        if not path.is_dir():
            return False
        
        # Look for video files in the directory
        video_files = self._find_video_files(path)
        if not video_files:
            return False
        
        # Check if any video file name doesn't match the folder name
        folder_name = path.name
        for video_file in video_files:
            video_name_without_ext = video_file.stem  # filename without extension
            
            # Skip corrupted video files (like "50" from 50/50 corruption)
            if len(video_name_without_ext) < 5 or not video_name_without_ext.startswith('S'):
                self.logger.debug(f"FolderFilenameMismatchRepairStrategy skipping corrupted video file: '{video_name_without_ext}'")
                continue
            
            # If folder name doesn't match video name, we can repair it
            if folder_name != video_name_without_ext:
                self.logger.info(f"FolderFilenameMismatchRepairStrategy detected mismatch:")
                self.logger.info(f"  Folder name: '{folder_name}'")
                self.logger.info(f"  Video file name: '{video_name_without_ext}'")
                self.logger.info(f"  Video file path: '{video_file}'")
                return True
        
        # No mismatch detected - no need to log every directory
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for folder/filename mismatches.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Find video files in the directory
        video_files = self._find_video_files(path)
        if not video_files:
            self.logger.warning(f"No video files found in directory: {path}")
            return actions
        
        folder_name = path.name
        
        self.logger.info(f"Analyzing folder/filename mismatch for: {path}")
        self.logger.info(f"  Current folder name: '{folder_name}'")
        self.logger.info(f"  Found {len(video_files)} video files:")
        
        # Check which names are valid with proper S#E# pattern validation
        folder_has_valid_pattern = bool(re.search(r'S\d+E\d+', folder_name))
        
        valid_video_files = []
        for video_file in video_files:
            video_name_without_ext = video_file.stem
            self.logger.info(f"    Video file: '{video_file.name}' (stem: '{video_name_without_ext}')")
            
            # Only consider video files with proper S#E# pattern as valid
            if (len(video_name_without_ext) >= 5 and 
                video_name_without_ext.startswith('S') and
                re.search(r'S\d+E\d+', video_name_without_ext)):
                valid_video_files.append(video_file)
                self.logger.info(f"      ✅ Valid episode pattern detected")
            else:
                self.logger.info(f"      ❌ Invalid/corrupted filename (no S#E# pattern)")
        
        # DECISION LOGIC: Only fix clear corruption, not episode number differences
        if valid_video_files and folder_has_valid_pattern:
            # Both folder and files have valid S#E# patterns
            video_name = valid_video_files[0].stem
            
            # Extract episode numbers to compare
            folder_episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
            video_episode_match = re.search(r'S(\d+)E(\d+)', video_name)
            
            if folder_episode_match and video_episode_match:
                folder_episode = int(folder_episode_match.group(2))
                video_episode = int(video_episode_match.group(2))
                
                self.logger.info(f"  Folder episode: E{folder_episode}, Video episode: E{video_episode}")
                
                # If episode numbers are different, choose which one to trust
                if folder_episode != video_episode:
                    # Trust the video file episode number (it contains the actual content)
                    # Rename folder to match video file
                    self.logger.info(f"  Decision: Different episode numbers - trusting video file (E{video_episode}) over folder (E{folder_episode})")
                    
                    target_path = path.parent / video_name
                    
                    if target_path.exists():
                        self.logger.warning(f"Target directory already exists: {target_path}")
                        return actions
                    
                    actions.append(RepairAction(
                        action_type="move",
                        source_path=path,
                        target_path=target_path,
                        reason=f"Rename folder to match video file episode number: E{folder_episode} -> E{video_episode}"
                    ))
                    
                    self.logger.info(f"  Will rename folder: {folder_name} -> {video_name}")
                    return actions
                
                # Same episode numbers but different text - rename files to match folder (folder is source of truth)
                self.logger.info(f"  Decision: Same episode numbers, different text - will rename files to match folder")
                self._rename_files_to_match_folder(path, folder_name, actions)
            else:
                # Couldn't parse episode numbers - use length/detail comparison as fallback
                if len(video_name) > len(folder_name):
                    self.logger.info(f"  Decision: Video file has more detail - will rename folder")
                    # (existing folder rename logic would go here, but likely won't be reached)
                else:
                    self.logger.info(f"  Decision: Folder name preferred - will rename files to match folder")
                    self._rename_files_to_match_folder(path, folder_name, actions)
                
        elif folder_has_valid_pattern:
            # Only folder has valid pattern, video files are corrupted - rename files to match folder
            self.logger.info(f"  Decision: Only folder name '{folder_name}' is valid - will rename corrupted files to match")
            self._rename_files_to_match_folder(path, folder_name, actions)
        
        else:
            # Folder name looks invalid - rename folder to match video file
            target_folder_name = valid_video_files[0].stem
            self.logger.info(f"  Decision: Video file name '{target_folder_name}' looks more valid - will rename folder")
            
            # Create the target path
            target_path = path.parent / target_folder_name
            
            # Check if target already exists
            if target_path.exists():
                self.logger.warning(f"Target directory already exists: {target_path}")
                return actions
            
            # Create folder rename action
            actions.append(RepairAction(
                action_type="move",
                source_path=path,
                target_path=target_path,
                reason=f"Rename folder to match video file: '{folder_name}' -> '{target_folder_name}'"
            ))
            
            self.logger.info(f"  Will rename folder: {folder_name} -> {target_folder_name}")
        
        return actions
    
    def _rename_files_to_match_folder(self, path: Path, folder_name: str, actions: List[RepairAction]) -> None:
        """Helper method to rename all files in a directory to match the folder name.
        
        Args:
            path: Directory path
            folder_name: Target base name for files
            actions: List to append repair actions to
        """
        self.logger.info(f"  Renaming all files to match folder name: '{folder_name}'")
        
        all_files = [f for f in path.iterdir() if f.is_file()]
        for file_item in all_files:
            # Determine new file name based on folder name
            file_extension = file_item.suffix
            
            # Handle special extensions
            if file_item.name.endswith('-thumb.jpg'):
                new_file_name = folder_name + '-thumb.jpg'
            elif file_item.name.endswith('.info.json'):
                new_file_name = folder_name + '.info.json'
            else:
                new_file_name = folder_name + file_extension
            
            target_file_path = path / new_file_name
            
            # Only rename if different
            if file_item.name != new_file_name:
                actions.append(RepairAction(
                    action_type="move",
                    source_path=file_item,
                    target_path=target_file_path,
                    reason=f"Rename file to match folder: '{file_item.name}' -> '{new_file_name}'"
                ))
                
                self.logger.info(f"    Will rename file: {file_item.name} -> {new_file_name}")
    
    def _find_video_files(self, directory: Path) -> List[Path]:
        """Find video files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of video file paths
        """
        from ...core.models import VIDEO_EXTENSIONS
        video_extensions = {f".{ext}" for ext in VIDEO_EXTENSIONS}
        video_files = []
        
        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix.lower() in video_extensions:
                    video_files.append(item)
        except OSError as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return video_files
