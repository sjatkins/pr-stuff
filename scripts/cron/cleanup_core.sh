#!/bin/bash

# PR_HOME is the directory that holds live/, scripts/ and Backups/.
# Defaults to the current directory, so run from that directory or export it.
PR_HOME="${PR_HOME:-$(pwd)}"; export PR_HOME

# Find and remove files matching criteria in both directories, suppressing output
find "$PR_HOME/live/lib/" "$PR_HOME/live/" -iname "core.*" -mtime +175 -size +1000k -exec rm {} + >/dev/null 2>&1

exit 0

