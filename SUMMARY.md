# Perilous Realms — Project State and Handoff

**Last updated:** 2026-09-19 (Docker image built, run and verified)
**Goal:** revive Perilous Realms (`pr3`) and package it as an installable
Docker image for its maintainer, preserving the existing player base.

A new session can start from this file alone. A turn-by-turn record of how we
got here is in `transcript.md` alongside it.

---

## 1. Layout

```
~/work/pr-stuff/
├── src/         git@github.com:cabarius/pr.git        — server source (private)
├── world/       git@github.com:cabarius/pr-world      — world data sources
├── live/lib/    NOT in git — runtime data directory
├── transcript.md
└── SUMMARY.md   (this file)
```

`live/` is untracked by design: mutable runtime state belonging to neither
repo. Both repos reference it by **relative path**, so the directory names
matter:

- `world/lib` is a symlink to `../live/lib`
- `world/compile` writes to `../../live/lib` (hardcoded, no override)
- `world/tran` is a symlink to `../src/tran/tran`

This layout dates to at least 2014 (see `src/README.macos-xcode-2014`).

---

## 2. How the server finds its data

`pr3` **chdirs into its data directory** and opens everything relative to it:

| what | where |
|---|---|
| default data dir | `"lib"` — `DFLT_DIR`, `h/const.h:1439` |
| override | `-d <dir>` — `main.c:181` |
| chdir | `main.c:250` |
| player index | `"players.new"` — `PLAYER_FILE`, `h/const.h:1455` |
| account index | `"account.list"` — `db.c:589`, and `popen("wc -l < account.list")` at `db.c:187` |

`src/lib` in the repo is a **stub** containing only `motd.c`. Always run with
`-d ../live/lib`.

### Directories the server does NOT create

It creates `WorldSave`, `account` and `stash` on demand, but `RoomSave` and
`WorldSave/Misc` are opened with plain `fopen()` (`room.save.c:151`,
`world.save.c:115`) and must exist beforehand.

### The `exit(1)` trap

`db.c:288-292`: when `WorldSave/Misc/limited.obj` exists,
`bypass_scan = LoadLimitCount()` is true and the server takes a fast-boot path
that **requires** `players.new` and calls `exit(1)` when absent. `limited.obj`
is written on every clean shutdown — so a world with no player index boots once
and dies on the second run with `No player files.`

---

## 3. Building

**Use `makefile.linux`.** The default `makefile` is the macOS/Xcode build
(`-framework Ruby`, `/System/Library/Frameworks/Ruby.framework/Headers`) and is
the cause of any `fatal error: ruby.h: No such file or directory`.
`makefile.linux` compiles with `-DNO_RUBY`; **Ruby is not needed anywhere**,
including for `tran`.

```sh
cd pr
make -f makefile.linux serverversion   # MUST come first -- see below
make -f makefile.linux pr3
make -f makefile.linux -C tran      # needed by world/compile
make -f makefile.linux -C Zone      # builds `syntax`, needed by ZONE/compile
```

**`serverversion` is not optional in a clean tree.** It is the only target that
compiles `O/version.o`, which the `pr3` link line requires. `pr3`'s own
`version` prerequisite (`makefile.linux:151`) is a no-op on every host but
`demon`, and `serverversion` (`:156`) is reachable only from `all`. A tree that
has ever run `make all` keeps `O/version.o` and hides this; a fresh clone fails
with `clang: error: no such file or directory: 'O/version.o'`.
(Verified 2026-09-19 in a clean container build.)

**Do not use `make -f makefile.linux all`.** Its `subproj` target also builds
`trident_client`, whose Makefile hardcodes `/usr/local/liboqs/lib64` and
`/usr/local/openssl/lib64` — valid only on the host named `demon`. It fails
with `/usr/bin/ld: cannot find -loqs`. `pr3` is already linked by that point,
so the failure is cosmetic, but it makes CI red for no reason.

`pr3` links the **prebuilt** `trident_libs/*.so` committed to the repo, via
`-Wl,-rpath,'$ORIGIN/trident_libs'`. No system liboqs required.

**But those prebuilts set a glibc floor of 2.38.** `trident_libs/libcrypto.so`
needs `__isoc23_strtol@GLIBC_2.38`; the other `.so` files need only 2.34.
Debian **bookworm ships glibc 2.36 and cannot link `pr3`**:

```
/usr/bin/ld: trident_libs/libcrypto.so: undefined reference to `__isoc23_strtol@GLIBC_2.38'
```

Use **trixie** (glibc 2.41) or newer; on trixie the runtime OpenSSL package is
`libssl3t64`, not `libssl3`. Anything older needs liboqs and OpenSSL built from
source instead. (Verified 2026-09-19.)

Note `makefile.linux` branches on `HOST=$(shell hostname -s)`; the `demon`
branch uses `/usr/local` paths. Any other hostname (including a container) gets
the portable bundled-libs path, which is what we want.

Build deps observed sufficient on Debian trixie:
`make clang gcc bison flex hostname libssl-dev libsqlite3-dev libzstd-dev
libcrypt-dev`. `Zone` needs bison/flex because its generated `parser.c` and
`scanner.c` are gitignored.

---

## 4. World data

```sh
mkdir -p live/lib
cd world && ./compile
```

Runs `tran` and per-directory `compile` scripts over `SECT/ ROOM/ ZONE/ MOB/
OBJ/ RACE/ SHOP/ CLAN/ ITEM_SETS/ SKILL/` and copies results plus `CLASSES/`,
`HELP/` and `MISC/*` into `../../live/lib/`.

`MISC/termcap` arrives in that last step. Skipping this gives
`termcap: No such file or directory` at `Boot db -- BEGIN` (`termcap.c:82`).

---

## 5. Players and accounts

**One account owns many characters.**

- **Account** — `acct_data`, `h/structs.h:783`; file at
  `account/<first-letter>/<name>` (`account.c:21`). Holds the **password**,
  email, balance, warehouse, ignore list, `char_list[]`, `num_chars`.
- **Character** — file at `stash/<first-letter>/<name>` (`player.save.c:49`);
  points back via `account_name` (`h/structs.h:742`).
- `char_account_valid()` (`account.c:298`) requires both directions to agree.
- Because the password is account-side, **characters and accounts must be
  restored together.**

### Current state of `live/lib`

Restored from `src/backup/PR-players-120829.tgz` (August 2012):

| | |
|---|---|
| characters in `stash/` | 577 files |
| accounts in `account/` | 136 files |
| `players.new` | 556 entries |
| loaded at boot | **554 players** |

The 2012 files load cleanly against `CURRENT_PLAYER_FILE_VERSION 6` — no
version errors, no `Invalid account` warnings.

Unresolved (minor): 556 entries vs 554 loaded. One entry, `suzie`, has no file
in `stash/s/`; the second discrepancy was never chased down.

### Restoring from backup

`backup/PR-players-*.tgz` is self-contained — characters, accounts,
`LockerSave`, and both indexes. But the indexes sit one level too deep for
where the server looks:

```sh
cd live
tar xzf ../src/backup/PR-players-120829.tgz --exclude='._*'
cp lib/stash/players.new    lib/players.new
cp lib/account/account.list lib/account.list
```

**`backup/PR-lib-*.tgz` must NOT be untarred over `live/lib`** — it is a full
2012 snapshot including 2012-vintage `world.out`, `mob.out` and `obj.out`,
which would clobber freshly compiled world data. Extract selectively (boards,
lockers) if needed.

---

## 6. Running

```sh
cd pr
./pr3 -d ../live/lib
```

Port **5024**. Flags (`main.c`): `-d <dir>` data directory, `-a <port>`
additional port, `-s` suppress special routines.

Benign boot messages, all optional files: `no-new`, `wizlocked`,
`always-sites`, `Directory UPDATE cannot be opened`, `NNNN.board does not
exist`, `Rooms N-M outside any zone`, `sh: line 1: account.list: No such file
or directory` (only on a world without accounts).

---

## 7. Git state

Both repos are on branch **`sam_build`**, pushed to `origin`.

**`pr`** — two commits ahead of `master`:

| commit | contents |
|---|---|
| `7732ab5` | `README.md` (new Linux build/run doc); `makefile.linux` — dropped `-L/usr/lib` from `LIBS` (this change was already uncommitted in the working tree, not authored here) |
| `c70b7dd` | `README` → `README.macos-xcode-2014` (git mv), plus a pointer to it from `README.md` |

**Uncommitted in `pr`:** `Dockerfile`, `docker-entrypoint.sh` — see below.

**`world`** (the pr-world repo) — branch `sam_build` created and pushed, **no commits**; working
tree clean. Nothing from this work touched that repo; all generated world data
went to `live/lib`, outside both repos.

Note: `sam_build` did not previously exist in either repo, locally or on the
remotes, despite an expectation that it did. If a `sam_build` was created
elsewhere (another machine, the GitHub web UI), expect a divergence.

### GitHub credentials

`~/.git-credentials` now has two `github.com` lines, `sjatkins` and `sjasoft`.
Two hazards learned the hard way:

- **`credential.useHttpPath=true` breaks host-only credential lines.** It was
  set during this session and caused authentication to fail with a valid token;
  it has been unset. Do not re-enable it without also adding per-path lines.
- **`git-credential-store` deletes lines silently.** On a rejected credential
  git calls the helper's `erase` and the line is removed from the file with no
  message. A hand-added line that "disappears" means the token was rejected.
  Validate first: `curl -s -H "Authorization: Bearer $TOK" https://api.github.com/user`.

---

## 8. Docker — built, run and verified (2026-09-19)

Image builds clean and the server accepts connections:

```
Welcome to Perilous Realms...
Revision: PR3.001.386 (22379a5acdad)
login:
```

First run seeded 556 index entries and loaded **554 players**; second run
logged `existing player database found, not seeding` and booted through the
`limited.obj` fast path without tripping the `exit(1)` trap. SIGTERM saves
players and world. Image size 373MB.

```sh
cd ~/work/pr-stuff
docker build -f src/Dockerfile -t pr3 .
docker run -d --name pr3 -p 5024:5024 -v pr-data:/data/lib pr3
```

Docker access on this host needed `usermod -aG docker samantha` plus
`systemctl enable --now docker` — Omarchy creates the `docker` group and
installs the unit but enables neither.

### `.dockerignore` — required, and unversioned

`pr-stuff/.dockerignore` keeps host-built artifacts out of the builder. Docker
preserves mtimes, so without it `make` sees objects newer than their sources,
skips the rebuild, and the image ships binaries linked against the host's
glibc. **It lives in `pr-stuff/`, which is not a git repo, so it exists only on
this machine.** CI does not need it (a fresh checkout has no artifacts).

Three traps found writing it, all of which produce confusing failures:

- **Do not exclude `*.a`** — `src/trident_libs/libtrident_engine.a` is a
  committed prebuilt that `pr3` links, not a build artifact.
- **Do not exclude `world/*/*.out`** — `ROOM/sector.out` is a *symlink* to
  `../SECT/sector.out` which the ROOM stage opens directly; excluding it gives
  the opaque `Can't boot sectors... dying`. All eleven `.out` files are
  regenerated by `compile`, so stale copies are harmless anyway.
- **`h/fcns.h`, `proto` and `Zone/parser.c` are deliberately NOT excluded**
  though git ignores them. Their regeneration in a clean tree is unverified;
  shipping them keeps the image build off that unknown. A CI build from a fresh
  checkout will exercise the real path.

- `src/Dockerfile` — multi-stage, Debian bookworm-slim
- `src/docker-entrypoint.sh`

### Design

**Builder stage** installs its own toolchain, `COPY`s both repos from a context
rooted at `pr-stuff/`, builds `pr3` + `tran` + `Zone/syntax`, then runs
`world/compile`. Nothing comes from the host.

**Build context must be the parent directory**, because `world/compile`
hardcodes `../../live/lib` and `world/tran` symlinks into `../src/tran/`:

```sh
cd ~/work/pr-stuff
docker build -f src/Dockerfile -t pr3 .
```

**Runtime stage** carries `pr3`, `trident_libs/`, compiled world data at
`/opt/pr/world/` (immutable), and an unpacked player snapshot at `/opt/pr/seed/`.
Runs as a non-root `pr` user. State volume at `/data/lib`.

**The core design problem:** `live/lib` mixes derived data (rebuilt from
sources — `world.out`, `help`, `termcap`) with mutable state (`stash/`,
`account/`, `RoomSave/`, `players.new`) in one flat directory. So the volume
cannot simply be mounted over it. The entrypoint merges the two at startup:

1. **Seed players only if the volume has none** — checks for a non-empty
   `players.new` or any file under `stash/`. If players exist it logs
   `not seeding` and leaves them alone, so upgrading the image never clobbers
   live player data.
2. Create `RoomSave`, `WorldSave/Misc`, `account`, `stash`.
3. Copy top-level regular files from `/opt/pr/world` into the volume — derived
   data, image is authoritative. Subdirectories are untouched.
4. `touch players.new` if still absent.
5. `exec ./pr3 -d /data/lib`

Build args: `--build-arg PLAYER_SEED=backup/PR-players-YYYYMMDD.tgz` for a
newer snapshot, or `PLAYER_SEED=` for an image with no players.

Caveat documented in the entrypoint: the world refresh overwrites `motd`, which
is compiled from `world/HELP/motd`, so in-game edits to it do not survive a
restart.

### Note on the second run

The fast-boot path does not print `There are N players`; that line appears only
on the first, scanning boot. Its absence on run two is expected, not a
regression. The failure to watch for is `No player files.`

### Immediate next step

GitHub Actions (§9). The build recipe above is now verified end to end, so the
workflow can encode it directly.

---

## 9. Then: GitHub Actions

Decided order was Dockerfile first, Actions second. The workflow should
`actions/checkout` both repos side by side and build with the workspace root as
context — no in-Dockerfile cloning, no secrets, and the same Dockerfile works
locally. A plain `make -f makefile.linux pr3` compile smoke test falls out of
it for free.

---

## 10. Known bugs, not fixed

- **`fopen_mkdir()`, `world.save.c:142`** — returns `NULL` when `mkdir` fails,
  including with `EEXIST`. It would therefore succeed for the first file
  created in a directory and fail for every one after. Currently **nothing
  calls it**, so it is latent. The in-source comment acknowledges the missing
  `EEXIST` check.
- **`trident_client/Makefile`** hardcodes `/usr/local/liboqs/lib64` and
  `/usr/local/openssl/lib64`, breaking `make all` on every host but `demon`.
- **`world/compile`** hardcodes `../../live/lib` with no variable to
  override, which is what forces the Docker build context to be the parent
  directory.
- **`makefile.linux:110`** — the `pr3` target links `$Oversion.o` but does not
  depend on anything that builds it. Its `version` prerequisite is a no-op off
  `demon`; the real rule is `serverversion`, reachable only from `all`. So
  `make -f makefile.linux pr3` cannot succeed in a clean tree. Worked around by
  calling `serverversion` first rather than fixing the makefile, since no
  source changes were in scope.

No source files were modified in this work beyond the README rename; all
breakage encountered was missing runtime state, not code.

---

## 11. Remit, and decisions made 2026-09-19 (evening)

**The remit is packaging only:** get Perilous Realms running nicely in Docker
on some host, in a form the *singleton maintainer/improver* can comfortably
work on. Rearchitecture (real database, admin CLI, Python port) is explicitly
out of scope for now. Context on it is recorded below so it is not re-derived.

### How the maintainer edits the world today

Two routes, and they interact badly:

- **Source route (authoritative):** edit the brace-syntax text under
  `world/ROOM/*.room`, `MOB/*.mob`, `OBJ/`, … then `world/compile`,
  then restart. The whole world pipeline needs only `tran`, `Zone/syntax`,
  `sh` and `cp` — **no C compiler**.
- **In-game route:** `redit` (`redit.c:902`), `rdig`, etc. edit `room_data`
  **in memory only**, and the save files do not carry definitions. `WriteRoom`
  / `ReadRoom` (`room.save.c:27`, `:55`) persist only runtime **state** — door
  states that differ from default, mobs present, objects present,
  `room_flags` — onto a room that must already exist from `world.out`. Name,
  description, exits and extra descriptions are never saved. So `redit desc`,
  `redit name` and `rdig` are **lost on every restart, in every room**; only
  `redit flags` survives. `redit` is a prototyping tool; the definition must be
  transcribed into the `.room` source (or exported with `room2tran`) to stick.
  `SaveZone()` → `WorldSave/zone.N` (zones with a `save (lo-hi)` range; 119 of
  136) and `SaveRoom()` → `RoomSave/<vnum>.room` (rooms flagged `AUTOSAVE`) are
  the two state-snapshot mechanisms; both load after `world.out` at boot.
- `room2tran` (`makefile.linux:131`, not built by default) converts live rooms
  back to `.room` source syntax — the bridge from in-game building to the repo.

### Docker consequences

- In-game **state** (contents, mobs, doors, flags) persists across container
  restarts and image upgrades: `WorldSave/` and `RoomSave/` are subdirectories
  of the volume and the entrypoint only refreshes top-level files. In-game
  **definition** edits never persisted anywhere, in any deployment — see above.
- Source edits currently require a full image rebuild, because `world.out` is
  baked in and re-copied over the volume on every start. The runtime image has
  no sources, no `tran`, no compiler, no editor — that is a choice in the
  Dockerfile's runtime stage, not a Docker limitation.

### Decided: a `pr3-dev` image alongside `pr3`

- `pr3` — unchanged, 373MB, what gets deployed.
- `pr3-dev` — the builder stage plus `git`, an editor, and both repos **with
  `.git` history** (56MB + 25MB), so the maintainer can edit, `compile`,
  restart, `make`, and `git commit && git push` from inside the container.
  ~1.2GB; fine for a dev image.
- Needs: `.dockerignore`'s `**/.git` exclusion made stage-conditional; a
  `PR_REFRESH_WORLD` gate in the entrypoint so a world compiled in-container is
  not clobbered on restart; `pr` user created with `--uid 1000` so bind-mounted
  host checkouts have matching ownership.
- Push credentials come in at **run time** only (`-v ~/.gitconfig:...:ro`,
  `-v ~/.git-credentials:...:ro`, or SSH agent). Never baked:
  `~/.git-credentials` holds plaintext tokens for two accounts.

**Not yet implemented.** Still open after it: the GitHub Actions workflow (§9).

### Things found in `world` (pr-world) that nobody had noted

- `DOCS/` (21 files) is the **builder documentation** — `configflags.txt`,
  `skills-spells-profs.txt`, `ClassAbilities.txt`, `backplot.txt`, maps. Much
  of it is `.rtf` / `.xlsx` / `.ods` / `.numbers` from the macOS era; the
  important ones should be converted to text for the maintainer.
- `DOCS/scripting-example.lua`, plus `PRLib/interpreter.c` / `Proc.c` /
  `GEN_proc_table.c` and the dead `-DNO_RUBY` paths: at least two prior
  attempts at an embedded scripting engine.

### Context for the eventual rearchitecture (out of scope)

- `PRLib/fields.c` holds **17 declarative `Schema` tables** (room, mob, obj,
  `char_data`, clan, race, shop, skill, item_set…) and `PRLib/Schema.c` is a
  generic read/write/reflection engine over them. `tran` uses them to parse the
  text sources. A database backend would be a new backend against this
  existing data model, not a rewrite — but the migration to it is half-done
  (see the hand-rolled `switch` with `InitWithSchema` grafted in at
  `sector.c:37`).
- The packed `.out` binaries are **derived** from text; a port never needs to
  read them. The only binary-only data is players/accounts in `stash/` and
  `account/` (`player.save.c`, described by `char_data_fields`) — one careful
  decoder, run once as a migration.
- `-lsqlite3` is linked only for `trident_libs`; the MUD itself uses no
  database.
- Sam has a **2023 Python port** (partial; converts some but not all of the
  data; Mongo was the storage idea at the time). It is **not on this machine**
  — to be pulled in separately.
