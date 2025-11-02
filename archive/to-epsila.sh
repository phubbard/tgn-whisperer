#!/bin/bash

# Set the source directory (where your numbered directories are)
SOURCE_DIR="podcasts/tgn"

# Set the destination directory (where you want to copy the files)
DEST_DIR="./to-epsila"

# Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Find all episode.md files in the source directory and its subdirectories
find "$SOURCE_DIR" -type f -name "episode.md" | while read -r file; do
    # Get the parent directory name
    parent_dir=$(basename "$(dirname "$file")")
    
    # Copy the file to the destination directory with the new name
    cp "$file" "$DEST_DIR/${parent_dir}.txt"
    
    echo "Copied $file to $DEST_DIR/${parent_dir}.txt"
done

echo "File copying and renaming complete."
