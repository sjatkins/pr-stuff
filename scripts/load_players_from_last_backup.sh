#!/bin/bash
# Restore players and accounts into the live data directory from a player
# backup: the reverse of cron/backup_players.sh.
#
#   load_players_from_last_backup.sh [-y] [backup-file]
#
# With no file, uses the newest Backups/players_*.tar.gz (or .tar). The
# backup holds stash/ and account/; both are extracted into PR_LIB and the
# index files are rebuilt from the result. Refuses to run while pr3 is
# running, and refuses to overwrite existing players unless -y is given.
set -e
PR_HOME="${PR_HOME:-$(pwd)}"
. "$(dirname "$(readlink -f "$0")")/pr_functions.sh"

yes=0
if [ "$1" = "-y" ]; then yes=1; shift; fi
file="$1"
if [ -z "$file" ]; then
  file=$(ls -t "$PR_HOME"/Backups/players_*.tar.gz "$PR_HOME"/Backups/players_*.tar 2>/dev/null | head -n 1)
fi
if [ -z "$file" ] || [ ! -f "$file" ]; then
  echo "load_players: no player backup found (looked in $PR_HOME/Backups for players_*.tar.gz)" >&2
  exit 1
fi

if pgrep -x pr3 >/dev/null; then
  echo "load_players: pr3 is running; stop it before restoring players" >&2
  exit 1
fi

existing=$(find "$PR_LIB/stash" -mindepth 2 -type f 2>/dev/null | wc -l)
if [ "$existing" -gt 0 ] && [ "$yes" -ne 1 ]; then
  echo "load_players: $PR_LIB/stash already holds $existing player files; pass -y to overwrite from $file" >&2
  exit 1
fi

mkdir -p "$PR_LIB"
echo "load_players: extracting stash/ and account/ from $file into $PR_LIB"
tar xf "$file" -C "$PR_LIB" stash account
rebuild_indexes "$PR_LIB"
echo "load_players: $(wc -l < "$PR_LIB/players.new") players, $(wc -l < "$PR_LIB/account.list") accounts"
