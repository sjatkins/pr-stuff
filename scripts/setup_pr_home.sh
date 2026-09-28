#!/bin/bash
# Set up (or verify) a Perilous Realms home directory.
#
#   setup_pr_home.sh [github-user]
#
# PR_HOME is the directory that holds src/, world/, live/, scripts/ and
# Backups/; it defaults to the current directory. Every step creates only
# what is missing and leaves what exists alone, so it is safe to rerun and
# is a no-op on a host that is already set up.
#
#   1. Clone src/ (cabarius/pr) and world/ (cabarius/pr-world) if absent.
#      With a github-user argument the URLs take the https://USER@github.com
#      form, which lets git pick that user's stored credential; otherwise
#      plain https://github.com. Existing checkouts are never pulled.
#   2. Create the live tree the server expects but does not create.
#   3. Point live/pr3 at src/pr3; link millie_compile.sh and
#      restart_pr_server.sh into PR_HOME.
#   4. Build pr3, tran and Zone/syntax if src/pr3 is absent.
#   5. Compile the world into live/lib if world.out is absent.
#   6. Restore the newest Backups/players_*.tar.gz if live has no players.
#   7. Rebuild the player, account and locker indexes.
set -e
PR_HOME="${PR_HOME:-$(pwd)}"; export PR_HOME
. "$(dirname "$(readlink -f "$0")")/pr_functions.sh"

GITHUB_USER="$1"
if [ -n "$GITHUB_USER" ]; then
  GITHUB="https://$GITHUB_USER@github.com"
else
  GITHUB="https://github.com"
fi
PR_BRANCH="${PR_BRANCH:-master}"

DIR="$PR_HOME/live"
LIB="$DIR/lib"

say() { echo "setup_pr_home: $*"; }

# 1. Source checkouts.
for pair in "src=pr" "world=pr-world"; do
  d="${pair%%=*}"; repo="${pair##*=}"
  if [ -d "$PR_HOME/$d" ]; then
    say "$d/ exists, leaving it alone"
  else
    say "cloning cabarius/$repo into $d/"
    git clone --branch "$PR_BRANCH" "$GITHUB/cabarius/$repo.git" "$PR_HOME/$d"
  fi
done

# 2. Live tree. The server creates stash/, account/ and WorldSave/ itself
#    but opens RoomSave/ and WorldSave/Misc/ with a plain fopen and dies
#    without them; PR_SERVER_SCRIPT's log rotation needs logs/recent/.
mkdir -p "$LIB/RoomSave" "$LIB/WorldSave/Misc" "$LIB/stash" "$LIB/account" \
         "$LIB/LockerSave" "$LIB/PURGED" "$DIR/logs/recent" "$PR_HOME/Backups"

# 3. The binary the server script runs, and the two scripts run by hand
#    from PR_HOME (as on production, where they were symlinked from ~pr).
ln -sfn ../src/pr3 "$DIR/pr3"
ln -sfn scripts/millie_compile.sh    "$PR_HOME/millie_compile.sh"
ln -sfn scripts/restart_pr_server.sh "$PR_HOME/restart_pr_server.sh"

# 4. Build if there is no binary. serverversion must come first: it is
#    the only target that produces O/version.o, which pr3 links.
if [ -x "$PR_HOME/src/pr3" ]; then
  say "src/pr3 exists, not building"
else
  say "building pr3, tran and Zone/syntax"
  ( cd "$PR_HOME/src" &&
    make -f makefile.linux serverversion &&
    make -f makefile.linux pr3 &&
    make -f makefile.linux -C tran &&
    make -f makefile.linux -C Zone )
fi

# 5. Compile the world if it has not been. world/compile writes to
#    ../../live/lib by a hardcoded relative path, so the layout matters.
if [ -f "$LIB/world.out" ]; then
  say "live/lib/world.out exists, not compiling the world"
else
  say "compiling the world into live/lib"
  ( cd "$PR_HOME/world" && ./compile )
fi

# 6. Players. If there are none, restore the newest player backup from
#    Backups/ (if there is one); otherwise leave the live data alone.
if [ "$(find "$LIB/stash" -mindepth 2 -type f 2>/dev/null | wc -l)" -gt 0 ]; then
  say "players exist in live/lib/stash, not restoring"
elif ls "$PR_HOME"/Backups/players_*.tar* >/dev/null 2>&1; then
  "$(dirname "$(readlink -f "$0")")/load_players_from_last_backup.sh"
else
  say "no players and no Backups/players_*.tar.gz to restore; the world will be empty"
fi

# 7. Indexes.
rebuild_indexes "$LIB"
say "done: $PR_HOME"
