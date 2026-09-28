# Perilous Realms — pr-stuff

Everything needed to build and run the Perilous Realms MUD (`pr3`) from a
clean machine, plus the data-extraction work around it. The game source
and world data live in two separate private repos that this repo's setup
script clones alongside it.

## Getting the game running

You need: `git`, `make`, `gcc` or `clang`, `bison`, `flex`, `libcrypt-dev`,
`screen`, and GitHub access to `cabarius/pr` and `cabarius/pr-world`.

```sh
git clone https://github.com/sjatkins/pr-stuff.git
cd pr-stuff
mkdir -p Backups
cp /path/to/players_YYYY-MM-DD.tar.gz Backups/       # a player backup, if you have one
scripts/setup_pr_home.sh <your-github-user>
scripts/PR_SERVER_SCRIPT
```

`setup_pr_home.sh` clones `src/` and `world/` if they are missing, creates
the `live/` tree, builds `pr3`, compiles the world, restores the newest
player backup from `Backups/` when there are no players yet, and rebuilds
the index files. It creates only what is missing, so rerunning it is
harmless. The GitHub user goes into the clone URLs so git can pick the
right stored credential; leave it off to use plain `github.com`.

`PR_SERVER_SCRIPT` runs the setup script, then starts `pr3` on ports 2150
and 5024 and restarts it whenever it exits. `telnet localhost 5024` should
show the login banner.

Every script resolves paths from `PR_HOME`, which defaults to the current
directory, so run them from here or `export PR_HOME=/path/to/pr-stuff`.

## Layout

| | |
|---|---|
| `src/` | game server source (clone of `cabarius/pr`, ignored here) |
| `world/` | world sources (clone of `cabarius/pr-world`, ignored here) |
| `live/` | runtime data: compiled world, players, saves, logs (ignored) |
| `Backups/` | player and full backups (ignored) |
| `scripts/` | setup, launch, restart, backup and restore scripts |
| `py_json/`, `py-pr/` | the world and player data as JSONL, and pydantic models over it |
| `explorations/` | notes on each game data type |
| `SUMMARY.md` | the full state of this work; start there for anything beyond the recipe |

## Other scripts

- `scripts/load_players_from_last_backup.sh [file]` restores players from a backup into an empty `live/`.
- `scripts/cron/backup_players.sh` and `backup_full.sh` make backups into `Backups/`.
- `scripts/restart_pr_server.sh` stops and restarts the game under `screen`.
