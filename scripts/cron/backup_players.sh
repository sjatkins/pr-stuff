#!/bin/bash

BACKUP_NAME="players_$(date +%F).tar.gz"
BACKUP_DIR="$HOME/Backups"
SOURCE_DIR="$HOME/live/lib"

# Suppress output for tar and mv commands
tar czf "$BACKUP_NAME" -C "$SOURCE_DIR" stash account >/dev/null 2>&1
mv "$BACKUP_NAME" "$BACKUP_DIR" >/dev/null 2>&1

# Check if the backup exists and is larger than 1000KB, suppress output
if find "$BACKUP_DIR" -iname "$BACKUP_NAME" -size +1000k >/dev/null 2>&1; then
  exit 0
else
  exit 1
fi
