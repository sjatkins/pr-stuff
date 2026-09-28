#!/bin/bash

# PR_HOME is the directory that holds live/, scripts/ and Backups/.
# Defaults to the current directory, so run from that directory or export it.
PR_HOME="${PR_HOME:-$(pwd)}"

BACKUP_NAME="full_backup_$(date +%F).tar.gz"
BACKUP_DIR="$PR_HOME/Backups"
SOURCE_DIR="$PR_HOME/live"

# Suppress output for tar and mv commands
tar --exclude="*.tgz" --exclude="*.tar.gz" --exclude="core.*" --exclude="logs" -czf "$BACKUP_NAME" -C "$SOURCE_DIR" lib >/dev/null 2>&1
mv "$BACKUP_NAME" "$BACKUP_DIR" >/dev/null 2>&1

# Check if the backup exists and is larger than 5000KB, suppress output
if find "$BACKUP_DIR" -iname "$BACKUP_NAME" -size +5000k >/dev/null 2>&1; then
  exit 0
else
  exit 1
fi

