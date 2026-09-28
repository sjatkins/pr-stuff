#!/bin/bash

# PR_HOME is the directory that holds live/, scripts/ and Backups/.
# Defaults to the current directory, so run from that directory or export it.
PR_HOME="${PR_HOME:-$(pwd)}"
cd "$PR_HOME/world" || exit 1
git pull
./compile
