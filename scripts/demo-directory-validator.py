#!/usr/bin/env python3
"""
Demonstration script for the Directory Validator functionality.

This script creates a sample media directory with various issues and shows
how the DirectoryValidator can detect and repair them.
"""

import tempfile
import json
from pathlib import Path
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ytdl_sub_config_manager.io.directory_validator import DirectoryValidator
from ytdl_sub_config_manager.core.logging import setup_logging


def create_sample_corrupted_media_directory(base_path: Path) -> Path:
    """Create a sample media directory with various corruption issues."""
    media_dir = base_path / "media" / "peloton"
    
    print("🔧 Creating sample media directory with corruption issues...")
    
    # Create normal episodes (these should be left alone)
    normal_episodes = [
        "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
        "Strength/Andy Speer/S10E001 - 2024-01-15 - 10 min Core",
        "Yoga/Aditi Shah/S15E001 - 2024-01-15 - 15 min Flow",
    ]
    
    # Create conflicting episodes (same season/episode numbers)
    conflicting_episodes = [
        "Cycling/Emma Lovewell/S20E002 - 2024-01-16 - 20 min Rock Ride",
        "Cycling/Cody Rigsby/S20E002 - 2024-01-17 - 20 min Pop Ride",  # CONFLICT!
        "Strength/Matty Maggiacomo/S10E002 - 2024-01-16 - 10 min Arms",
        "Strength/Callie Gullickson/S10E002 - 2024-01-17 - 10 min Legs",  # CONFLICT!
    ]
    
    # Create corrupted 50/50 structure episodes
    corrupted_episodes = [
        "Bootcamp 50/50/Jess Sims/S30E001 - 2024-01-15 - 30 min Full Body",
        "Tread Bootcamp 50/50/Andy Speer/S25E001 - 2024-01-16 - 25 min HIIT",
    ]
    
    all_episodes = normal_episodes + conflicting_episodes + corrupted_episodes
    
    for i, episode_path in enumerate(all_episodes):
        full_path = media_dir / episode_path
        full_path.mkdir(parents=True, exist_ok=True)
        
        # Create a sample .info.json file
        info_file = full_path / f"{full_path.name}.info.json"
        
        # Extract duration from the folder name more carefully
        folder_name = full_path.name
        duration = 30  # default
        if 'S' in folder_name and 'E' in folder_name:
            try:
                # Extract season number (which represents duration in minutes)
                s_part = folder_name.split('S')[1].split('E')[0]
                duration = int(s_part)
            except (IndexError, ValueError):
                duration = 30
        
        info_data = {
            "id": f"class_{i+1:03d}",
            "title": folder_name,
            "instructor": episode_path.split('/')[1] if '/' in episode_path else "Unknown",
            "duration": duration,
        }
        info_file.write_text(json.dumps(info_data, indent=2))
    
    print(f"✅ Created {len(all_episodes)} episodes:")
    print(f"   📁 {len(normal_episodes)} normal episodes")
    print(f"   ⚠️  {len(conflicting_episodes)} episodes with conflicts")
    print(f"   💥 {len(corrupted_episodes)} episodes in corrupted 50/50 structure")
    
    return base_path


def demonstrate_directory_validation(media_dir: Path, dry_run: bool = True):
    """Demonstrate the directory validation and repair process."""
    print(f"\n🔍 Starting directory validation {'(DRY RUN)' if dry_run else '(LIVE RUN)'}...")
    
    # Create validator
    validator = DirectoryValidator(str(media_dir), dry_run=dry_run)
    
    # Step 1: Show initial scan
    print("\n📊 Initial directory scan:")
    all_episodes = validator._scan_all_episodes()
    print(f"   Found {len(all_episodes)} total episodes")
    
    # Count issues
    corrupted_episodes = [ep for ep in all_episodes if ep.is_corrupted_location]
    conflicts = validator._detect_episode_conflicts(all_episodes)
    
    print(f"   🚨 {len(corrupted_episodes)} episodes in corrupted locations")
    print(f"   ⚔️  {len(conflicts)} episode number conflicts")
    
    # Show details of issues
    if corrupted_episodes:
        print("\n💥 Corrupted locations detected:")
        for ep in corrupted_episodes:
            print(f"   📂 {ep.path}")
            print(f"      Activity: {ep.activity or 'UNKNOWN'}")
            print(f"      Instructor: {ep.instructor}")
            print(f"      Episode: S{ep.season}E{ep.episode}")
    
    if conflicts:
        print("\n⚔️  Episode conflicts detected:")
        for conflict in conflicts:
            print(f"   🎯 {conflict.activity.name if conflict.activity else 'UNKNOWN'} "
                  f"S{conflict.season}E{conflict.episode}")
            for path in conflict.conflicting_paths:
                print(f"      📂 {path}")
    
    # Step 2: Run validation and repair
    print(f"\n🔧 Running validation and repair {'(simulated)' if dry_run else '(actual)'}...")
    success = validator.validate_and_repair()
    
    if success:
        print("✅ Validation and repair completed successfully!")
    else:
        print("❌ Validation and repair encountered issues!")
    
    # Step 3: Show final state (only meaningful if not dry run)
    if not dry_run:
        print("\n📊 Final directory scan:")
        final_episodes = validator._scan_all_episodes()
        final_corrupted = [ep for ep in final_episodes if ep.is_corrupted_location]
        final_conflicts = validator._detect_episode_conflicts(final_episodes)
        
        print(f"   Found {len(final_episodes)} total episodes")
        print(f"   🚨 {len(final_corrupted)} episodes still in corrupted locations")
        print(f"   ⚔️  {len(final_conflicts)} episode conflicts remaining")
        
        if len(final_corrupted) == 0 and len(final_conflicts) == 0:
            print("🎉 All issues resolved!")
        else:
            print("⚠️  Some issues may require manual intervention")


def main():
    """Main demonstration function."""
    print("🎬 Directory Validator Demonstration")
    print("=" * 50)
    
    # Set up logging
    setup_logging(level="INFO", format_type="standard")
    
    # Create temporary directory for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample corrupted media directory
        media_dir = create_sample_corrupted_media_directory(temp_path)
        
        # Demonstrate validation in dry run mode
        demonstrate_directory_validation(media_dir, dry_run=True)
        
        print("\n" + "=" * 50)
        print("🎯 Summary:")
        print("   The DirectoryValidator successfully:")
        print("   ✅ Detected corrupted 50/50 directory structures")
        print("   ✅ Identified episode number conflicts") 
        print("   ✅ Planned repairs to fix both issues")
        print("   ✅ Would rename minimal files to resolve conflicts")
        print("\n   In a real scenario (dry_run=False), it would:")
        print("   🔄 Move corrupted episodes to correct locations")
        print("   📝 Renumber conflicting episodes sequentially")
        print("   🧹 Ensure all episode numbers are unique per activity/season")
        
        print(f"\n📁 Sample directory created at: {temp_path}")
        print("   You can explore the structure before it's cleaned up!")
        
        # Keep the directory around for a moment so user can inspect
        input("\nPress Enter to continue and clean up the demo directory...")


if __name__ == "__main__":
    main()
