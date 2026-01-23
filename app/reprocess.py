#!/usr/bin/env python3
"""
Reprocess a podcast episode by selectively removing generated files.

Usage:
    uv run python app/reprocess.py tgn 14.0 --all
    uv run python app/reprocess.py wcl 100 --transcribe --attribute
    uv run python app/reprocess.py hodinkee 246 --download
    uv run python app/reprocess.py tgn 14 --all --make

Flags control which files are removed:
    --download    Remove episode.mp3 (forces re-download)
    --transcribe  Remove transcript files (forces re-transcription)
    --attribute   Remove speaker-map.json (forces re-attribution)
    --markdown    Remove episode.md/html (forces regeneration)
    --all         Remove all generated files (full reprocess)
    --make        Run make to rebuild after removing files
"""

import argparse
import sys
import subprocess
from pathlib import Path
from loguru import logger as log


def main():
    parser = argparse.ArgumentParser(
        description="Reprocess a podcast episode by removing generated files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Full reprocess with rebuild:
    uv run python app/reprocess.py tgn 14.0 --all --make

  Just re-run speaker attribution:
    uv run python app/reprocess.py tgn 14 --attribute --make

  Re-download and transcribe:
    uv run python app/reprocess.py hodinkee 246 --download --transcribe --make
        """
    )
    parser.add_argument("podcast", choices=["tgn", "wcl", "hodinkee"],
                       help="Podcast name")
    parser.add_argument("episode",
                       help="Episode number (e.g., 14.0 or 14)")
    parser.add_argument("--download", action="store_true",
                       help="Remove MP3 file (forces re-download)")
    parser.add_argument("--transcribe", action="store_true",
                       help="Remove transcript files (forces re-transcription)")
    parser.add_argument("--attribute", action="store_true",
                       help="Remove speaker map (forces re-attribution)")
    parser.add_argument("--markdown", action="store_true",
                       help="Remove markdown files (forces regeneration)")
    parser.add_argument("--all", action="store_true",
                       help="Remove all generated files (full reprocess)")
    parser.add_argument("--make", action="store_true",
                       help="Run make to rebuild after removing files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be removed without actually removing")

    args = parser.parse_args()

    # Normalize episode number (add .0 if missing)
    episode = args.episode
    if '.' not in episode:
        episode = f"{episode}.0"

    # Find episode directory
    project_root = Path(__file__).parent.parent
    episode_dir = project_root / "podcasts" / args.podcast / episode

    if not episode_dir.exists():
        log.error(f"Episode directory not found: {episode_dir}")
        sys.exit(1)

    log.info(f"Reprocessing {args.podcast} episode {episode}")
    log.info(f"Episode directory: {episode_dir}")

    # Determine which files to remove
    files_to_remove = []

    if args.all:
        log.info("Full reprocess requested (--all)")
        files_to_remove = [
            "episode.mp3",
            "episode-transcribed.json",
            "whisperx.json",
            "speaker-map.json",
            "episode.md",
            "episode.html"
        ]
    else:
        if args.download:
            files_to_remove.append("episode.mp3")
        if args.transcribe:
            files_to_remove.extend(["episode-transcribed.json", "whisperx.json"])
        if args.attribute:
            files_to_remove.append("speaker-map.json")
        if args.markdown:
            files_to_remove.extend(["episode.md", "episode.html"])

    if not files_to_remove:
        log.error("No action specified. Use --all or specify individual flags.")
        log.info("Available flags: --download, --transcribe, --attribute, --markdown, --all")
        sys.exit(1)

    # Show what will be removed
    log.info(f"Files to remove: {', '.join(files_to_remove)}")

    # Remove files
    removed = []
    skipped = []

    for filename in files_to_remove:
        file_path = episode_dir / filename
        if file_path.exists():
            if args.dry_run:
                log.info(f"[DRY RUN] Would remove: {filename}")
                removed.append(filename)
            else:
                log.info(f"Removing: {filename}")
                file_path.unlink()
                removed.append(filename)
        else:
            skipped.append(filename)
            log.debug(f"File not found (skipping): {filename}")

    # Report results
    if args.dry_run:
        log.info(f"\n[DRY RUN] Would remove {len(removed)} files:")
        for f in removed:
            log.info(f"  - {f}")
        if skipped:
            log.info(f"\nWould skip {len(skipped)} files (don't exist):")
            for f in skipped:
                log.info(f"  - {f}")
        log.info("\nRe-run without --dry-run to actually remove files")
        sys.exit(0)

    if not removed:
        log.warning("No files were removed - they may not exist yet")
        sys.exit(0)

    log.success(f"Removed {len(removed)} files: {', '.join(removed)}")

    if skipped:
        log.info(f"Skipped {len(skipped)} files (didn't exist): {', '.join(skipped)}")

    # Run make if requested
    if args.make:
        log.info("\nRunning make to rebuild episode...")
        result = subprocess.run(
            ["make"],
            cwd=project_root,
            capture_output=False,  # Show output in real-time
            text=True
        )
        if result.returncode == 0:
            log.success("Make completed successfully")
        else:
            log.error(f"Make failed with exit code {result.returncode}")
            sys.exit(result.returncode)
    else:
        log.info("\nTo rebuild the episode, run: make")
        log.info(f"Or re-run with --make flag")


if __name__ == "__main__":
    main()
