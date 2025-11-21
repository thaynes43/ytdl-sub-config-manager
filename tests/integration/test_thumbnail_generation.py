
import pytest
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.io.generic_directory_validator import GenericDirectoryValidator
from src.io.generic_repair_strategies.incomplete_episode_cleanup_strategy import IncompleteEpisodeCleanupStrategy
from src.io.media_source_strategy import DirectoryPattern, RepairAction

def check_ffmpeg_available():
    """Check if ffmpeg is available in the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

class TestThumbnailGenerationIntegration:
    """Integration test for thumbnail generation using real ffmpeg."""

    def setup_method(self):
        """Set up test environment."""
        # Skip if ffmpeg is not available
        if not check_ffmpeg_available():
            pytest.skip("ffmpeg is not available in the system")
        
        self.test_data_dir = Path("tests/test-data/peloton")
        self.temp_test_dir = Path("tests/temp_test_data")
        
        # Clean up previous run if exists
        if self.temp_test_dir.exists():
            shutil.rmtree(self.temp_test_dir)
            
        # Copy test data to temp directory
        shutil.copytree(self.test_data_dir, self.temp_test_dir)
        
        self.validator = GenericDirectoryValidator(
            media_dir=str(self.temp_test_dir),
            validation_strategies=[],
            repair_strategies=[],
            dry_run=False
        )
        
        # Target specific episode that we know exists in test data
        # Structure: Cycling/Bradley Rose/S5E3 - 20250509 - 5 min Cool Down Ride
        self.episode_path = self.temp_test_dir / "Cycling" / "Bradley Rose" / "S5E3 - 20250509 - 5 min Cool Down Ride"
        self.video_path = self.episode_path / "S5E3 - 20250509 - 5 min Cool Down Ride.mp4"
        self.thumb_path = self.episode_path / "S5E3 - 20250509 - 5 min Cool Down Ride-thumb.jpg"
        
        # Ensure video exists
        if not self.video_path.exists():
            pytest.skip("Test video file not found in test data")
            
        # Ensure thumbnail DOES NOT exist for the test
        if self.thumb_path.exists():
            self.thumb_path.unlink()

    def teardown_method(self):
        """Clean up."""
        if self.temp_test_dir.exists():
            shutil.rmtree(self.temp_test_dir)

    def test_generate_thumbnail_execution(self):
        """Test that GenericDirectoryValidator correctly executes generation."""
        
        # Create the action manually
        action = RepairAction(
            action_type="generate_thumbnail",
            source_path=self.video_path,
            target_path=self.thumb_path,
            reason="Testing thumbnail generation"
        )
        
        # Execute the action
        result = self.validator._execute_repair_actions([action])
        
        assert result is True, "Repair action execution failed"
        assert self.thumb_path.exists(), "Thumbnail file was not created"
        assert self.thumb_path.stat().st_size > 0, "Thumbnail file is empty"

if __name__ == "__main__":
    # Manually run the test setup and execution if run as script
    test = TestThumbnailGenerationIntegration()
    try:
        test.setup_method()
        test.test_generate_thumbnail_execution()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        test.teardown_method()

