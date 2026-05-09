#!/bin/bash

# Configuration
REPO_URL="https://github.com/Uomocosa/paper-scraper.git"
TARGET_DIR="$HOME/paper-scraper"

echo ">>> Downloading latest lele-paper-scraper repository..."

if [ -d "$TARGET_DIR/.git" ]; then
    echo "Directory exists and is a git repo. Pulling updates..."
    # -C allows running git commands in a specific directory
    git -C "$TARGET_DIR" pull
elif [ -d "$TARGET_DIR" ]; then
    echo "Warning: $TARGET_DIR exists but is not a git repository."
    echo "Please move or delete the directory and try again."
    exit 1
else
    echo "Directory does not exist. Cloning repository..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

echo ">>> Done!"
