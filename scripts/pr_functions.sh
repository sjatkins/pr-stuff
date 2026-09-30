#!/bin/bash
# Shared functions for the Perilous Realms ops scripts. Source it:
#
#   . "$(dirname "$(readlink -f "$0")")/pr_functions.sh"
#
# PR_HOME is the directory that holds live/, scripts/ and Backups/ and
# defaults to the current directory. PR_LIB is the game's data directory.
PR_HOME="${PR_HOME:-$(pwd)}"
PR_LIB="${PR_LIB:-$PR_HOME/live/lib}"

# rebuild_index <dir> <index-file>
#   Write the names of every file under <dir>/a .. <dir>/z, one per line,
#   to <index-file>. This is how players.new and account.list are made:
#   the server only appends to them, so after a restore they are rebuilt
#   from the directory contents. (Was stash/build and account/build.)
rebuild_index() {
  local dir=$1 out=$2 letter
  : > "$out" || return 1
  for letter in {a..z}; do
    [ -d "$dir/$letter" ] && ls "$dir/$letter" >> "$out"
  done
  return 0
}

# rebuild_locker_index [lib]
#   List LockerSave/*.room into lockers.save, which lockers.c reads.
#   Empty when there are no lockers. (Was LockerSave/build.)
rebuild_locker_index() {
  local lib=${1:-$PR_LIB}
  ( cd "$lib/LockerSave" 2>/dev/null && ls *.room 2>/dev/null ) > "$lib/lockers.save" || true
}

# rebuild_indexes [lib]
#   All three: players.new, account.list, lockers.save. PR_SERVER_SCRIPT
#   runs this before every start.
rebuild_indexes() {
  local lib=${1:-$PR_LIB}
  rebuild_index "$lib/stash"   "$lib/players.new"  || return 1
  rebuild_index "$lib/account" "$lib/account.list" || return 1
  rebuild_locker_index "$lib"
}

# list_all_players [lib]
#   Print every character name as a quoted, comma-terminated line, for
#   pasting into a list literal. (Was stash/list_all_players.sh.)
list_all_players() {
  local lib=${1:-$PR_LIB} letter n
  for letter in {a..z}; do
    [ -d "$lib/stash/$letter" ] || continue
    for n in "$lib/stash/$letter"/*; do
      [ -e "$n" ] && printf '"%s",\n' "$(basename "$n")"
    done
  done
}

# prune_logs [logs-dir]
#   Delete rotated logs (<logs-dir>/*.log) older than the retention
#   cutoff: the start of the current year or three months ago, whichever
#   is earlier, so at least the current year or the last three months is
#   kept. The live "log" and recent/ are never touched. PR_SERVER_SCRIPT
#   runs this after rotating at every start.
prune_logs() {
  local logs=${1:-$PR_HOME/live/logs} year_start three_months cutoff
  year_start=$(date +%Y-01-01)
  three_months=$(date -d '3 months ago' +%Y-%m-%d) || return 1
  if [[ "$three_months" < "$year_start" ]]; then
    cutoff=$three_months
  else
    cutoff=$year_start
  fi
  find "$logs" -maxdepth 1 -name '*.log' -type f ! -newermt "$cutoff" -delete
}
