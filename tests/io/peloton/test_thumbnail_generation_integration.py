"""Integration test for thumbnail generation with real files."""

import os
import shutil
from pathlib import Path
import pytest
from src.io.generic_directory_validator import GenericDirectoryValidator
from src.io.media_source_strategy import RepairAction

def check_ffmpeg_available():
    """Check if ffmpeg is available in PATH."""
    return shutil.which('ffmpeg') is not None

class TestThumbnailGenerationIntegration:
    """Integration test for thumbnail generation using ffmpeg-python."""
    
    @pytest.fixture
    def test_env(self, tmp_path):
        """Set up test environment with a real video file."""
        source_video_dir = Path("tests/test-data/peloton/Cycling/Bradley Rose/S5E3 - 20250509 - 5 min Cool Down Ride")
        source_video = source_video_dir / "S5E3 - 20250509 - 5 min Cool Down Ride.mp4"
        
        if not source_video.exists():
            pytest.skip(f"Source video not found: {source_video}")
        
        target_dir = source_video_dir
        video_path = source_video
        thumb_path = target_dir / "S5E3 - 20250509 - 5 min Cool Down Ride-thumb.jpg"
        
        return {
            "root_dir": Path("tests/test-data/peloton"),
            "episode_dir": target_dir,
            "video_path": video_path,
            "thumb_path": thumb_path
        }

    def test_real_thumbnail_generation(self, test_env):
        """Test generating a thumbnail from a real video file using the validator logic."""
        if not check_ffmpeg_available():
            pytest.skip("ffmpeg is not available in PATH. Please install ffmpeg and ensure it's in your system PATH.")
        
        root_dir = test_env["root_dir"]
        episode_dir = test_env["episode_dir"]
        video_path = test_env["video_path"]
        thumb_path = test_env["thumb_path"]
        
        print(f"\nTesting in: {episode_dir}")
        
        # 1. Clean up existing thumbnail if it exists
        if thumb_path.exists():
            print(f"Removing existing thumbnail: {thumb_path}")
            thumb_path.unlink()
            
        # 2. Verify thumbnail is gone
        assert not thumb_path.exists(), "Thumbnail should be deleted before generation"
        
        # 3. Create validator
        validator = GenericDirectoryValidator(
            media_dir=str(root_dir),
            validation_strategies=[],
            repair_strategies=[],
            dry_run=False
        )
        
        # 4. Manually construct the repair action
        action = RepairAction(
            action_type="generate_thumbnail",
            source_path=video_path,
            target_path=thumb_path,
            reason="Integration test thumbnail generation"
        )
        
        # 5. Execute action
        print(f"Generating thumbnail from: {video_path}")
        result = validator._execute_repair_actions([action])
        
        # 6. Verify success
        assert result is True, "Validator should report success"
        
        # Check if thumbnail was actually created (the code returns True even on failure for non-fatal behavior)
        if not thumb_path.exists():
            # Try to get more info about why it failed
            import subprocess
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
                raise AssertionError(
                    f"Thumbnail file was not created even though ffmpeg is available. "
                    f"Check logs above for ffmpeg errors. Expected: {thumb_path}"
                )
            except FileNotFoundError:
                raise AssertionError(
                    f"Thumbnail file was not created because ffmpeg is not available in PATH. "
                    f"Please install ffmpeg and ensure it's in your system PATH. Expected: {thumb_path}"
                )
            except subprocess.CalledProcessError:
                raise AssertionError(
                    f"Thumbnail file was not created. ffmpeg is available but returned an error. "
                    f"Check logs above for details. Expected: {thumb_path}"
                )
        
        file_size = thumb_path.stat().st_size
        assert file_size > 0, "Thumbnail file should not be empty"
        
        print(f"Successfully generated thumbnail: {thumb_path}")
        print(f"Thumbnail size: {file_size} bytes")

