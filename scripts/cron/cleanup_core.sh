#!/bin/bash

# Find and remove files matching criteria in both directories, suppressing output
find "$HOME/live/lib/" "$HOME/live/" -iname "core.*" -mtime +175 -size +1000k -exec rm {} + >/dev/null 2>&1

exit 0

