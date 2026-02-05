
import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.io.generic_directory_validator import GenericDirectoryValidator
from src.io.media_source_strategy import RepairAction

class TestThumbnailGenerationLogic:
    """Test for thumbnail generation logic using mocks for ffmpeg."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_test_dir = Path("tests/temp_test_data_mock")
        self.temp_test_dir.mkdir(exist_ok=True)
        
        self.validator = GenericDirectoryValidator(
            media_dir=str(self.temp_test_dir),
            validation_strategies=[],
            repair_strategies=[],
            dry_run=False
        )
        
        self.video_path = self.temp_test_dir / "test_video.mp4"
        self.thumb_path = self.temp_test_dir / "test_video-thumb.jpg"
        
        # Create a dummy video file
        self.video_path.touch()

    def teardown_method(self):
        """Clean up."""
        if self.temp_test_dir.exists():
            shutil.rmtree(self.temp_test_dir)

    @patch('builtins.__import__')
    def test_generate_thumbnail_calls_ffmpeg_correctly(self, mock_import):
        """Test that the validator calls ffmpeg with the correct arguments."""
        
        # Create a mock ffmpeg module
        mock_ffmpeg = MagicMock()
        mock_import.side_effect = lambda name, *args, **kwargs: mock_ffmpeg if name == 'ffmpeg' else __import__(name, *args, **kwargs)
        
        # Setup the mock chain
        # ffmpeg.input().output().overwrite_output().run()
        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_overwrite = MagicMock()
        
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_overwrite
        
        action = RepairAction(
            action_type="generate_thumbnail",
            source_path=self.video_path,
            target_path=self.thumb_path,
            reason="Testing thumbnail generation"
        )
        
        # Execute
        result = self.validator._execute_repair_actions([action])
        
        assert result is True, "Repair action execution failed"
        
        # Verify calls
        mock_ffmpeg.input.assert_called_with(str(self.video_path), ss=2)
        mock_input.output.assert_called_with(str(self.thumb_path), vframes=1, qscale=2)
        mock_output.overwrite_output.assert_called_once()
        mock_overwrite.run.assert_called_once_with(capture_stdout=True, capture_stderr=True, quiet=True)

    @patch('builtins.__import__')
    def test_generate_thumbnail_audio_only_uses_spectrogram(self, mock_import):
        """Test that audio-only files use a spectrogram thumbnail."""
        mock_ffmpeg = MagicMock()
        mock_import.side_effect = lambda name, *args, **kwargs: mock_ffmpeg if name == 'ffmpeg' else __import__(name, *args, **kwargs)

        mock_ffmpeg.probe.return_value = {"streams": [{"codec_type": "audio"}]}

        mock_input = MagicMock()
        mock_filtered = MagicMock()
        mock_output = MagicMock()
        mock_overwrite = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.filter.return_value = mock_filtered
        mock_filtered.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_overwrite

        action = RepairAction(
            action_type="generate_thumbnail",
            source_path=self.video_path,
            target_path=self.thumb_path,
            reason="Testing audio-only thumbnail generation"
        )

        result = self.validator._execute_repair_actions([action])

        assert result is True, "Repair action execution failed"

        mock_ffmpeg.input.assert_called_with(str(self.video_path))
        mock_input.filter.assert_called_with('showspectrumpic', s='640x360')
        mock_filtered.output.assert_called_with(str(self.thumb_path))
        mock_output.overwrite_output.assert_called_once()
        mock_overwrite.run.assert_called_once_with(capture_stdout=True, capture_stderr=True, quiet=True)

if __name__ == "__main__":
    test = TestThumbnailGenerationLogic()
    try:
        test.setup_method()
        # Run the test method directly
        test.test_generate_thumbnail_calls_ffmpeg_correctly()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.teardown_method()

