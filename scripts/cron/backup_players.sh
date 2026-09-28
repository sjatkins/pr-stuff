#!/bin/bash

# PR_HOME is the directory that holds live/, scripts/ and Backups/.
# Defaults to the current directory, so run from that directory or export it.
PR_HOME="${PR_HOME:-$(pwd)}"; export PR_HOME

BACKUP_NAME="players_$(date +%F).tar.gz"
BACKUP_DIR="$PR_HOME/Backups"
SOURCE_DIR="$PR_HOME/live/lib"

# Suppress output for tar and mv commands
tar czf "$BACKUP_NAME" -C "$SOURCE_DIR" stash account >/dev/null 2>&1
mv "$BACKUP_NAME" "$BACKUP_DIR" >/dev/null 2>&1

# Check if the backup exists and is larger than 1000KB, suppress output
if find "$BACKUP_DIR" -iname "$BACKUP_NAME" -size +1000k >/dev/null 2>&1; then
  exit 0
else
  exit 1
fi
