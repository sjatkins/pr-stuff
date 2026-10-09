# Perilous Realms — Project State and Handoff

**Last updated:** 2026-09-28 (built master here with production players; use-after-free fix merged; production ops scripts in git)
**Goal:** revive Perilous Realms (`pr3`) and package it as an installable
Docker image for its maintainer, preserving the existing player base.

A new session can start from this file alone. Turn-by-turn records are in
`transcript.md` (the 2026-09-18/19 packaging session) and
`explorations/102626.md` (the 2026-09-27 data-extraction session).

---

## 1. Layout

```
~/work/pr-stuff/
├── src/         git@github.com:cabarius/pr.git        — server source (private)
├── world/       git@github.com:cabarius/pr-world      — world data sources
├── live/lib/    NOT in git — runtime data directory
├── py_json/     uv project: world + player sources -> out/*.jsonl (§12)
├── py-pr/       uv project: pydantic models and coded enums over that JSONL
├── explorations/  per-type org notes on the game data, session transcript
├── graphify-out/  graphify knowledge graph of src/ + world/
├── FUTURE.md    out-of-scope rearchitecture notes (property graph, Mongo)
├── README.md    the collaborator recipe: clone, setup_pr_home.sh, PR_SERVER_SCRIPT
├── transcript.md
└── SUMMARY.md   (this file)
```

`pr-stuff/` is itself a git repo, `sjatkins/pr-stuff` on GitHub
(`origin/main`). **Intended to move to `cabarius/pr-stuff`** once the owner
creates an empty repo there: `git remote set-url origin
https://sjatkins@github.com/cabarius/pr-stuff.git && git push -u origin
main`, then fix the clone URL in README.md. Sam lacks permission to create
it (2026-09-28). `src/`, `world/`, `live/`
and the `players_*.tar` backups are ignored; the JSONL output is committed
so it need not be re-extracted.

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


---

## 12. Data extraction and models (2026-09-27/28)

Separate from the packaging remit. Motivation (Sam): the game is "weirdly
file and binary file based"; the goal is a Mongo database with a collection
per type. Details and caveats per type are in `explorations/*.org`.

### `py_json/` — sources to JSONL

`uv run world2jsonl` writes one JSONL file per type into `py_json/out/`.
`src/prworld/tranparse.py` reimplements the text side of `src/tran/tran.c`
(`#include`, `#define`, `#offset`, `@macro`); `schemas.py` transcribes the
`Schema` tables in `PRLib/fields.c`; `names.json` (from `tools/gen_names.py`)
carries the C name tables; zones and classes have their own parsers.

| type | records | checked against |
|---|---|---|
| rooms | 26,287 | `world.out` (vnum sets match, `tools/check_bin.py`) |
| mobs | 3,450 | `mob.out` |
| objects | 4,855 | `obj.out` |
| shops / races / sectors / clans / item_sets | 63 / 54 / 84 / 29 / 85 | their `.out` files |
| zones / classes / effects / skills | 129 / 40 / 2 / 1 | text only, no binary |
| players / accounts | 697 / 279 | `players_2026-09-23.tar` |

Players and accounts are the hand-coded binary formats of `player.save.c`,
`account.c` and `objdb.c`, transcribed in `players.py`; field sizes come from
`player_layout.json`, generated by compiling `tools/layout.c` against the
server headers (rerun if `structs.h` changes). Password hashes are dropped
unless `--include-secrets`; emails, real names and last login sites are kept
(private repo). The one unparsed account, `account/a/alcanzar`, is a player
file saved in the wrong directory.

Decisions made deliberately, do not revisit without asking:
- Every schema key is present on every record, `null` when unset. Kept on
  purpose for the pydantic work, even though Mongo does not need it.
- Parenthesised values `field ( 10 )` are accepted; `tran` drops them, so
  the JSON is more complete than the binaries there.
- Apply blocks are dicts; repeated numeric applies are summed.
- Work from the tar and the C source only; `live/lib` is off limits.

### `py-pr/` — pydantic models

`src/classes.py` has one model per extracted type plus models for structures
nothing extracts yet (lockers, warehouses, world save, boards, auctions, help,
socials, reference tables). `src/names.py` is generated by
`tools/gen_enums.py`: code tables are `StrEnum`s carrying `.code`; the 18
bit tables are `enum.Flag` classes (`CodedFlag`) whose members carry the
game's label, with list-of-names only at the JSONL boundary. `ItemType` is a
class hierarchy dispatched on kind; positional int lists became named models
(`Dice`, `Defense`, `HitPoints(current, rolled)`, `Pool(current, bonus)`).
`uv run python tools/validate_jsonl.py` validates all fourteen files.
`extra="forbid"` catches drift between extractor and models.

Two C name-table errors are corrected in `gen_names.py` (`NAME_FIXES`):
immunity bit 19 is `magic` (IMM_MAGIC), and action bits 14/15 are
`polymorphed-self` / `polymorphed-other`. No data uses them.

### Facts learned about the game (see the org files)

- A saved object is a full copy; the vnum is a join key the runtime never
  dereferences. `.out` edits take effect only on restart.
- Zones populate rooms: one-minute tick, `find_zone` returns the first zone
  in `zone.list` order containing the vnum, overlaps only warn.
- Locker = object 10100, a communal chest in a clan room, backed by
  `LockerSave/`. Warehouse = bank storage on the character (50) or account
  (500), reachable only via the banker special.
- "Damage type" is one shared attack-type numbering (spells, weapon types,
  room hazards, skills, proficiencies); modelled as `AttackType`.

### Open items

- Dockerfile and entrypoint exist only on `src` branch `sam_build`
  (f5271fbc), never merged to `master`. `pr3-dev` image and GitHub Actions
  still unbuilt (§9, §11).
- 13 players have no level or class (abandoned creations); 83 spell entries
  numbered 242–246 lie above the named spell table and are kept as `#N`.
- Affect bits 38/39/46 and immunity bit 5 have no names in `constants.c`;
  emitted as `bitN`.
- Nothing has been loaded into Mongo yet.


---

## 13. Local build with production players, and the production host (2026-09-28)

### Building master on this machine

`src` master no longer links Trident (removed on production 2026-09-24,
commit a7ae330; `src/notes/2026-09-24-rebuild-and-trident-removal.md` is
the record). The link line is now just `-lPR -lcrypt -lm`, so §3's glibc
2.38 floor and the bookworm/trixie note apply only to `sam_build`.

The §3 recipe still holds (`serverversion` first, then `pr3`, `tran`,
`Zone`). One trap found and fixed: `Zone/makefile.linux` called gcc with
no `-std`, and gcc 15+ defaults to C23, where `bool` is a keyword and
`h/compat.h:27` `typedef char bool;` is an error. It now pins
`-std=gnu11` (94876a77 on `src` master, verified with a clean rebuild
from the grammar sources). `setup_pr_home.sh` therefore builds cleanly on
a current toolchain.

### Player data

Production players were restored from `players_2026-09-23.tar` (kept at
`pr-stuff/`, gitignored): 697 characters, 280 accounts, both indexes
inside the tar at `stash/players.new` and `account/account.list`, copied up
one level exactly as in §5. All 697 load; no invalid-account warnings.

`account/a/alcanzar` is **a character save, not an account record** (3,370
bytes, February 2023, player-file signature), sitting beside the real
character in `stash/a/alcanzar`. It is the same on production, so that
account entry has been broken for over three years. Not touched.

### The crash, and the fix (merged to `master`)

With these players, boot segfaulted in the `boot_players` scan, first in
`reset_and_apply_item_set_bonuses` (handler.c) and, after fixing that, in
`reset_and_apply_remort_bonuses`. Both had the same loop: walk
`ch->affected`, and on the first match call `affect_from_char`, which
frees every node of that type, then read `caf->next` from the freed node.
`affect_from_char` already removes all matching affects in one safe pass,
so each loop became a single call. Commit e9c14de8, rebased and
fast-forwarded onto `master` and pushed; the branch is deleted.

The path runs on every login, remove and quit by a player with set gear or
remort bonuses (257 of 697 players carry those affects), and during every
boot scan. **Production has run this code for years without crashing.**
The only build-environment difference found is glibc: production is
Debian 13 / glibc 2.41, this machine glibc 2.44; compiler (clang) and
makefile flags are the same. That is inference, not proof; an
AddressSanitizer build would show every such read at once.

`src` is on `master` at e9c14de8. The game runs here from that binary:
`./pr3 -d ../live/lib`, port 5024. **Production still runs the old code**
(started 2026-09-25, before the fix); it needs a pull, rebuild and restart
to pick it up.

### Production host (`pr3-pr` in `~/.ssh/config`, user `pr`)

Surveyed read-only. Nothing there was changed.

- Debian 13, glibc 2.41, clang. Game at `~pr/live/pr3`, data `~pr/live/lib`,
  run as `pr3 -p 179 -d /home/pr/live/lib -a 5024 2150`. Up since
  2026-09-25 02:21 as of the survey.
- **No systemd unit and no cron runs or restarts the game.** The `pr` user
  has no `crontab` command; `/etc/cron.d` has only the distro entry; no
  timers. `~pr/scripts/cron/check_and_restart_pr_server.sh` exists but
  nothing invokes it. A unit Sam recalls adding is not present.
- **Backups:** `~pr/scripts/cron/backup_players.sh` tars `stash` and
  `account` from `live/lib` into `~pr/Backups/players_<date>.tar.gz`;
  `backup_full.sh` tars all of `lib` as `full_backup_<date>.tar.gz`.
  1,995 files there. Player backups run daily until 2026-03-08, then
  nothing until 2026-09-20..23, consistent with being run by hand.
  Monthly full backups exist through at least 2025-01.
- `~pr/scripts/` was not under version control. Now copied into
  `pr-stuff/scripts/` (see below).
- Production's `live/pr3` is a hand-made symlink into `src/`, and the
  restart script launches `live/PR_SERVER_SCRIPT` in a screen session.
  **`PR_SERVER_SCRIPT` is still only on the host**, not in the copy.
- The host is a lineage of snapshots: the 09-24 rebuild copied the previous
  install and rebuilt the source in place, so hand-set things (the symlink,
  the scripts, the stray `alcanzar` file) carry forward.

### What live/lib holds beyond the player tar

The tar covers `stash/`, `account/` and the two indexes only. Also player
state, not in the tar: `LockerSave/` (clan lockers), `WorldSave/zone.N`
and `RoomSave/` (room contents), board files, the auction file, and
`PURGED/` (deleted characters/accounts, moved there by a shell `mv` the
server never creates the directory for). `full_backup_*.tar.gz` covers all
of it.

### Ops scripts, now in git (`pr-stuff/scripts/`)

Copied from production, then made portable. Commits 919ec43, 2a80561 and
3913d6e are the verbatim copies (`~pr/scripts/`, `live/PR_SERVER_SCRIPT`,
and the scripts that lived *inside* `live/lib`); cf1423a, 0b2f743, 0e16692
and 4b29ced are the rewrites.

**`PR_HOME` convention.** Every script starts with
`PR_HOME="${PR_HOME:-$(pwd)}"` and resolves `src/`, `world/`, `live/`,
`scripts/` and `Backups/` from it; `PR_LIB` (default `$PR_HOME/live/lib`)
is the data directory. On production `PR_HOME=/home/pr` reproduces the old
`$HOME`-relative behaviour. **Recommended practice (README):** export it
once in the shell profile to the checkout directory, so every script
works from anywhere including cron. Running from the checkout with it
unset also works; only someone with several checkouts sets it per
command. Children inherit both the variable and the working directory,
so no script exports it or changes directory. Reviewed all scripts
2026-09-28 for stale paths after the moves into `scripts/`.

| script | what it does |
|---|---|
| `setup_pr_home.sh [github-user]` | one command from empty directory to running-ready, no-op afterwards: clone `src`/`world` if absent (`https://USER@github.com` form only when a user is given), create the live tree and `Backups/`, `ln -sfn ../src/pr3 live/pr3`, link `millie_compile.sh` and `restart_pr_server.sh` into `PR_HOME` (as on production), build if `src/pr3` absent, `world/compile` if `world.out` absent, restore the newest `Backups/players_*.tar.gz` if `stash/` is empty, rebuild indexes. Never pulls. |
| `load_players_from_last_backup.sh [file]` | reverse of `backup_players.sh`: extract `stash/` and `account/` from the newest `Backups/players_*.tar.gz` (or `.tar`, or the given file) into `live/lib` and rebuild the indexes. Only ever restores into an empty `stash/`; refuses if players exist or `pr3` is running. Tested against the 09-23 tar in a scratch `PR_HOME`: all 697 player and 280 account files and both indexes byte-identical to `live/lib`. |
| `PR_SERVER_SCRIPT` | the launch loop the restart script runs under `screen`: calls `setup_pr_home.sh`, rotates `live/logs`, rebuilds indexes, runs `pr3 -p 179 -d live/lib -a 5024 2150`, relaunches on exit; `CLEAN_EXIT` / `BOOT_CLEAN` marker files |
| `pr_functions.sh` | sourced library: `rebuild_index`, `rebuild_locker_index`, `rebuild_indexes` (players.new, account.list, lockers.save from the directory listings) and `list_all_players`. Replaces `stash/build`, `account/build`, `LockerSave/build`, `stash/list_all_players.sh`, which were hand-written into the data directory in 2016/2023 and travel in every player tar |
| `restart_pr_server.sh` | stop the game (exact `pgrep -x pr3`), optional clean reboot (`-c`), start `scripts/PR_SERVER_SCRIPT` under `screen` (was `live/PR_SERVER_SCRIPT` on production), wait for the port |
| `cron/check_and_restart_pr_server.sh` | probe ports 5024 / 2150 for the banner, three tries 30 s apart, then run the restart script |
| `cron/backup_players.sh`, `cron/backup_full.sh` | `Backups/players_<date>.tar.gz` of `stash`+`account`; `full_backup_<date>.tar.gz` of all of `lib` |
| `cron/cleanup_core.sh` | delete `core.*` older than 175 days |
| `millie_compile.sh` | `git pull` in `world`, then `./compile` |
| `unpurge`, `extr` | 2006 single-player restore from a tar (default: newest `Backups/players_*.tar.gz`); interactive |
| `gen_defines` | 2006 perl: `#define`s from the `IMMORTALS` file; unused |
| `deprecated/`, `cron/us_debt.sh`, `db/` | old versions, a 2011 Ruby launcher, and an unrelated debt tracker; untouched |

**Index files are derived.** `players.new` and `account.list` are just
`ls` of the letter directories; the server only appends to them. After any
restore, `rebuild_indexes` (or a start via `PR_SERVER_SCRIPT`) regenerates
them. Verified: the function reproduces the 2026-09-23 tar's indexes
exactly. This is also why the misfiled `alcanzar` is in `account.list`.

**`setup_pr_home.sh` tested on an already set up `PR_HOME`** (here,
2026-09-28, game running): it skipped the clones, the build and the world
compile with a message each, created only `Backups/`, `live/lib/PURGED/`,
an empty `lockers.save` and the `live/pr3` symlink, and rewrote
`players.new` and `account.list` byte-identical (diffed against copies
taken first). It exposed one bug: with no lockers, `ls *.room` returns 2
and `set -e` made the script exit 2 after writing every index. Fixed in
`pr_functions.sh` (72752c1); rerun exits 0.

**Not yet exercised:** the fresh-directory path, clone and build.
Production already has `src/pr3`, so the build step is skipped there.

**Collaborator recipe:** clone `pr-stuff`, drop a `players_*.tar.gz` into
`Backups/` (gitignored), run `scripts/setup_pr_home.sh <github-user>`,
then `scripts/PR_SERVER_SCRIPT`. On this machine the 09-23 backup is at
`Backups/players_2026-09-23.tar.gz`.

**Still nothing schedules any of it** on production: no cron, no timer, no
unit. The auto-restart is the `while true` loop in `PR_SERVER_SCRIPT`.

## 14. Web access (https on 80/443) — direction chosen, nothing built (2026-09-28)

Goal: `https://<game-domain>` with a landing page and a game page showing an
optional generated picture of the player's current room above a terminal
widget that talks to the game.

How networking works now (`src/comm.c`): `setup_ports` opens one plain TCP
listener per port via `init_socket` (binds to `gethostbyname(hostname)`, not
0.0.0.0); `game_loop` is a `select` loop; `new_id` accepts and knows the
listening port; per-connection telnet negotiation (IAC DO LINEMODE at
connect, MXP offer if the client sends IAC) in `process_input`/`hello_new_conn`;
`write_to_conn` renders `#` colour tags per terminal type; `write_to_fd`
writes raw bytes. Nothing speaks TLS, HTTP or WebSocket.

Chosen shape (Sam, 2026-09-28):
- Caddy on 80/443 (TLS, Let's Encrypt): `/` → static React build (landing +
  game page with picture widget and xterm.js terminal widget); `/api/*` and
  `/ws` → FastAPI/uvicorn.
- FastAPI: `/ws` is a dumb asyncio relay to a dedicated game port on
  localhost (`-a 2151`); `/api/room-image/{vnum}` and
  `/api/zone-image/{zone}`, page falls back to zone on 404; other non-game pages as wanted.
- Game (small C change, not done): per-port "web" flag set in accept; on such
  connections skip telnet negotiation and, in `look_room` (`src/look.c:869`,
  the single room-display entry point), emit an OSC marker like
  `ESC ] 9001 ; room=<zone>:<vnum> BEL`. xterm.js `registerOscHandler` catches it
  in the browser and swaps the picture; nothing is shown in the terminal.
- Pictures: per zone (155) and per room where wanted.
  World has 26,284 rooms (10,001 sector "Prototype"), 5,450 distinct names.

Sketches in `explorations/http-server/`: Caddyfile, `tty_proxy.py`, `api_server.py`, `web/` (Vite + React + xterm.js). None run yet.
Production (checked as `pr`) has nothing on 80/443 and no active Caddy.

Rejected: TLS or WebSocket framing inside the C code; ttyd/websockify bridge
(no side channel for room id, though fine for a first plain-terminal demo).

## 15. Report: `show obj sword` shows no swords on production (2026-09-30)

Investigated from local source and production logs only (no production
source). Path: `do_show` (`src/show.c:663`) → `is_abbrev("obj","objects")`
gated on level ≥ I5 (2005) → `show_db` → `hash_iterate2(&obj_db,
print_index_data_name, sb, "sword")` → `str_str` (case-insensitive) on
`obj->name` (the keyword list) → `page_string`, 35 lines per page.
Command lookup is an exact match on "show" (`interpreter.c:101`).

Reproduced the core routine on the local build against a scratch copy of
`live/lib` under gdb (boot to `game_loop`, call `hash_iterate2` by hand):
returns 7,659 bytes of sword lines, first vnums 4, 5, 39, 43, 44, 45...
So search + data are fine here; obj count matches production (4,854).

Production log since the 2026-09-25 boot has no `show` command lines at all
(only players with the log flag are logged) and no errors, crashes or cores.
Reporter is Nitemare: level 2011 (game-written `lib/IMMORTALS` roster,
builder range 500000-999999), so the level gate is not it. Neither the
local object table (max vnum 257,005) nor production's zone list (129 zones
loaded, none above 257xxx) has anything in that range. In-game `oedit` only
modifies existing prototypes; nothing creates or persists new ones, so any
sword made in-game does not survive a reboot (last boot 2026-09-25 02:21).
Page height is validated 0-255, so the pager cannot be wedged by it.
Syn (I6, account crow) is the only logged session; no `show` lines.
Still unresolved; need the exact text Nitemare sees.

Side finding: `hash_find` (hash.c, commit 8c8b558b 2023 "possible fix to
last crash") stops at any chain entry with key 0, so a lookup that collides
with vnum 0's bucket can return vnum 0's data. Not the cause of this report.

Same immortal also reports `where <name>` returning nothing. `do_where`
(`src/cmds3.c`, subcmd CMD_OWHERE=35, level I5) walks `object_list`,
matches `str_str(obj->name, arg)` on the whole remaining argument
(`only_argument`), skips objects whose carrier fails `CAN_SEE`, and prints
"Couldn't find any such thing." when the string block is empty. Shared with
`show obj`: `only_argument` + `str_str` + string block + `page_string`.
Input assembly (`process_input`) drops control chars and bytes >127, so a
stray CR/tab cannot poison the argument; trailing spaces are kept but would
only thin the list. Dispatch passes `cmd_info[cmd].num`, so the subcmd is
right. Per-account/char command revocation exists (`cmd_ok`) but yields
"Pardon?", not an empty list. No cause found in code; the failure is
specific to this character or client. Next: exact transcript from Nitemare
(commands as typed and full reply), their client, and whether Syn (I6) gets
results for the same `show obj sword` / `where sword`.

Reproduction with Nitemare's own data (2026-09-30): booted a scratch copy of
`live/lib` under gdb, loaded the character with `load_char` and account
`bun` with `load_acct` (no password involved), attached a fake connection,
and called `do_where(ch,"sword",35)` and `do_show(ch,"obj sword",0)`. Both
return full results (where: swords on mobs with vnums; show: the 4, 5, 39...
list). Character: level 2011, page_size 0, invis_level 0, no revoked
commands on char or account, `cmd_ok` true for both. So code + world data +
this character (as of the 09-23 backup) all work here. Whatever fails on
production is in its runtime state, its compiled world files, or its binary,
none of which can be checked from logs, and the logs record nothing.
Sam: no transcript obtainable; Syn considered too low level to compare.

Correction (2026-09-30): I earlier said Nitemare's commands are not logged.
Wrong: production has 15,174 Nitemare lines across 2,852 log files. Their
commands (`[bun]{room}Nitemare:cmd`) were logged up to 2022-10-12; since
then only events (link loss/reconnect, board/account admin). Last logged
`show`/`where` by Nitemare: 2020. So no Sept-2026 evidence of either
command either way. Sept 2026 lines: logins from 94.5.223.226 /
82.132.x / 195.89.130.8, account deletes (hutt, huttan) on 09-22, board
removal on 09-21, and "Nitemare tried to make Calista implementor" on 09-22
14:38:30 followed by a dropped link (same on 03-08 for Countess). That comes
from `do_set` level I10/I11 in `wizard.c:1027`: actor not in a hardcoded
name list gets host-wizlocked and disconnected; the list said "Bunta" until
commit b7bffd4a (2026-09-24) changed it to "Nitemare", so pre-09-25 binaries
kicked Nitemare for it. No "Reject from" lines followed (wizlock toggles, and
no `wizlocked` file existed at the 09-25 boot). Production booted 7 times
between 09-19 and 09-25 (new-host migration). "mod 40 out of range 0 and
37" is logged at Nitemare's login on production and when loading the
character locally: an apply/affect index the current tables do not know.

Resolution (2026-09-30): the reporting player's immortal character is Bun,
i.e. Bunta (level 2011 in Jan 2026, 2010 in Mar 2026), not Nitemare
(same person, account bun). Local `logs/` (2,852 files, a copy of
production's) shows on 2026-09-22 04:04:33: "Bunta deleted", "Bunnyboo
deleted", "Account huttan deleted", "Nitemare deleted account huttan".
Bunta lived on account huttan; deleting the account deleted the character.
No `bunta` player file exists in the 09-23 backup or on production now, and
Bunta is absent from the game-written IMMORTALS roster. `load_char` on the
backup returns -1; running `show obj sword` as that empty character prints
the Usage list, `where` nothing. A new level-1 cleric "Buntie" was created
on 09-22 13:21. So `show`/`where` "fail" because the character running
them is no longer an immortal (or is a fresh mortal): `show` needs I4,
`show obj` I5, `where` I5. Fix is administrative: restore Bunta from a
pre-09-22 player backup (Backups/players_2026-09-20..21) or re-advance a
character; no code bug. Note `logs/*2026*` matches 4 old files by name
substring (YYMMDD naming); 2026 logs are `logs/26*.log`.

Correction: "Bun" is the account, not a character (no character Bun
exists anywhere). Account bun (loaded via `load_acct` in the gdb sandbox,
char list only) has 17 entries: Nitemare (x2), Kazin, Quorra, Calista,
Druna, Jet, Fae, Fay, Ichika, Belle, Belletwo, Clara, Gwen, Roux, Elza,
Bumble; player files in the 09-23 backup exist for nitemare, calista,
bumble, gwen, roux, elza. Only Nitemare is an immortal (2011). Calista is a
level-496 Paladin with per-character granted commands "goto, restore,
chat, transfer" (logged at each save), active 09-21/22, and on 09-22
14:38 Nitemare tried to set Calista to I10/I11 and was kicked by the old
Bunta-only guard. So if the player runs `show`/`where` as Calista, both
answer "Pardon?" (not granted, level < I4/I5). Likely resolution: advance
Calista (now possible with the 09-25 binary) or grant `show` and `where`.
The Bunta deletion note above stands as a fact but is not this report.

Telnet-faithful reproduction (2026-09-30): a sandbox instance runs from
`src/pr3 -d <scratchpad>/gdblib 2151` under gdb (scratchpad = the session
dir under /tmp/claude-1000/-home-samantha-work-pr-stuff/<session>/).
`gdblib` is a copy of `live/lib`; in that copy only, account bun's password
was set to "x" via the game's own `load_acct`/`save_acct` (script
`setpw.gdb`). `tclient.py <host> <port> <lines...>` is a scripted telnet
client (strips IAC, prints everything). Logged in as bun → `l nitemare` →
`show obj sword`: full paged list, identical to production's expected
output. Observed: a command typed while the pager is waiting at "[Press
return to continue, q to quit]" is consumed by the pager and never runs.
The sandbox was left running on 2151 (Sam: "may come in handy").

ROOT CAUSE (2026-09-30). Nitemare's transcript: `show obj sword` prints
only the header "VNUM    count names"; `show obj 1 100` works. That is the
search branch matching nothing. Every build tried here (master, production
commit eb40d673, the pre-Trident commit b7bffd4a, and the NEW host's actual
binary /home/pr/src/pr3 copied over) lists the swords. Then: the new host's
log has no login from account bun since its 09-25 boot at all, and DNS
(perilousrealms.com → 54.219.85.41) only exposes port 5024. The OLD host,
54.193.215.24 (`Host pr-pr`, Amazon Linux 2, ip-172-31-2-62), is STILL
RUNNING the game (pid 1291, `-a 5024 2150`, booted 09-25 06:20) and that is
where Nitemare plays (reconnects 09-28, 09-30 12:22; Calista entered game
09-30 12:36). Its binary copied here (with its liboqs/openssl and a Debian
libcrypt) reproduces exactly: header only. gdb inside the callback:
`str_str("sword small training","sword")` → NULL, even `str_str("abc","b")`
→ NULL, while `strstr` works. Disassembly of that binary's `str_str`
(PRLib/utility.c): after the two lowercase loops it does `xor eax,eax; ret`
— the `strstr(b1,b2)` call is gone (frame even uses the red zone, i.e. it
was compiled as a leaf). Source at the old host's commit d1bc0db
(2026-01-04) is identical to today's (`return(strstr(b1,b2));`), and no
header redefines strstr; the old host's libPR.a/utility.o date from
2026-01-03/12, built with clang 11.1.0 against glibc 2.26, and the 09-22
pr3 was only relinked against them. Why that toolchain dropped the call is
not established (old-glibc string.h inlines or a miscompile are the
candidates); it is not reproducible with clang 19/22 or gcc. Impact on the
old host: all 28 `str_str` call sites (show obj/mob search, where, boards,
auction, stat, reception, bounty hunter, spec_mob) match nothing.

Operational finding: TWO production games are live and diverging since
09-19/25. Old host since its 09-25 boot: 3 accounts, 50 game entries, 15
player files saved. New host: 5 accounts, 21 entries, 18 files. Nitemare's
client evidently has the old IP. Fix for the report: rebuild on the old host
(or retire it and point players at perilousrealms.com:5024); merging the
forked player saves is a separate problem. The five sandboxes, their data copies, the copied production binaries
and the two worktrees were removed on 2026-09-30; only `tclient.py`,
`setpw.gdb` and the session transcripts remain in the scratchpad.

2026-09-30, later: Sam shut down the old host's game instance
(54.193.215.24). Players who still used that address (Nitemare / account
bun among them) must now connect to perilousrealms.com:5024. Player saves
made on the old host between 09-19/25 and the shutdown (15 files since its
09-25 boot) are not on production; whether to merge them is open.

Log retention (2026-09-30): production `live/logs` was 2.8 GB / 2,850
files since 2018, ~99% "Reset zone" lines; nothing ever deleted them.
Added `prune_logs [dir]` to `scripts/pr_functions.sh`, called by
PR_SERVER_SCRIPT right after rotating at each start: deletes `*.log`
older than the earlier of Jan 1 of this year and three months ago (keeps
whichever is more). Live `log` and `recent/` untouched. Tested on fake
files; takes effect on production at its next restart after a pull.

## 16. Architecture notes for a Python rewrite (discussion, 2026-09-30)

Sam is considering a clean Python server with a real database instead of
the binary/text world files. Conclusions from the discussion:

**Performance is not the risk.** Production today: 133 MB RSS, ~12% of one
core, 21 game entries since boot; world 26k rooms, 4.9k object protos,
~10k mob instances; ~0.1 s pulse. One asyncio loop (same shape as the C
select loop) is idle most of the time at 10x the players. Condition: the
database stays off the hot path. Live state in memory; DB for what must
survive restart; writes behind the loop, never per tick. The risk is the
rewrite itself: 106k lines of C in 96 files, mostly game rules. Prefer
carving (new Python network/persistence layer first, rules ported one
system at a time with the C code as reference and extracted world data as
fixtures) over a big-bang rewrite.

**Relationships as triples.** Nearly all live state is a relation
(in_room, carried_by, worn_by+slot, inside, fighting, follows, affects).
The C structs embed these as pointers + intrusive lists (obj: in_room,
carried_by, equipped_by, in_obj, contains, next_content, next; char:
in_room, fighting, equipment[], carrying, next_in_room, next, master,
followers, 3 affect lists; room: contents, people) and half the crash
history is those disagreeing. Replace with an indexed triple set; game
code inserts/removes triples directly (that is the point), with small
helpers (move_to, wear, fight) so a stale triple can only come from a
skipped helper; invariants (one location, one item per slot) become
assertable. Qualifiers (slot, direction) go beside the triple as edge
properties, not inside the object slot, so all indexes stay id-keyed.
Single-valued roles store a value, multi-valued a set.

**Measured at game scale** (26k rooms, 10k mobs, 30k objects, 92k
relations): dict-indexed triples (spo + ops) 60 MB, ~2 µs per lookup;
networkx 3.7 DiGraph 85 MB, 2-10 µs per lookup, 9 µs per move (no
predicate index, so "in room" filters edges; fix: one DiGraph per
relation). General triple store keeps 3 (SPO/POS/OSP) or 6 permutations;
the game needs 2, maybe role-first as a third. Script:
scratchpad/nxbench.py (session-local).

**Stores.** Mongo: triple collection {s,r,o,+qualifiers} with indexes
{s,r,o},{o,r,s},{r,s,o} mirrors the in-memory permutations; $graphLookup
for transitive queries; player saves as one document each (snapshot,
restorable, diffable); round trip ~0.3-1 ms so fine per action, not per
tick. Neo4j: natural for world/builder queries; node/edge properties are
schema-free but FLAT (primitives or arrays only; a map/JSON must be a
string, queryable only after promotion to properties/edges). Kùzu is the
closest embedded option. Sam's UOP (uniform ids across classes + triple
table + per-commit changesets with timestamp covering fields, metadata and
relationships) is the substrate; extend with in-memory indexes and
on-demand networkx views rather than reimplementing algorithms.

**Changesets.** Would have solved this week's problems: Bunta's deletion
(revert one commit instead of restoring a tar) and the two-server fork
(merge two change streams). Journal the durable model (characters,
accounts, world defs, boards), not tick churn (mob wandering, regen,
rounds), matching what the C server saves today. Uses: point-in-time
restore, builder undo, event feed for web/notifications, read-only backup
DB, "changes since my last update" for a node coming up.

**Distribution.** Zone ownership (one node owns a zone, others mirror)
avoids most conflicts. NATS core for fast ephemeral traffic (subjects:
zone.<n>.*, player.<name>.tell, global.chat; sub-ms; no topology to
maintain). JetStream as the changeset log of record: durable, ordered,
replayable; consumers track sequence; snapshot + tail for cold start;
publish-first-apply-on-receipt for all writes so nodes cannot diverge
(also ends the two-servers problem by construction). KV for presence.
Stream retention is a working window; an archiver consumer writes the
complete append-only history to cheap storage (partitioned by time,
checksummed/hash-chained), a snapshot consumer emits full state images
with their sequence; other consumers: structured game log (replacing
2.8 GB of "Reset zone" lines), per-player history, metrics. Cold start =
snapshot + archive tail + live stream.

**Changesets as the only contract (later in the same discussion).** The
game publishes semantic changesets, `id: {field: value, ...}` plus
relationship and metadata adds/removes per commit with timestamp and
context; it carries no database driver. Consumers keep projections
(Mongo, Neo4j, files, the game's own boot store) and any store can be
added later by replaying the archive. No old values in changesets: the
stream is ordered, appliers only set, so every changeset is idempotent;
a prior value is found by walking back along changesets for that id and
field (per-id index of sequences; bounded by the last snapshot; absent
if never set). Undo = re-emit prior values as a new commit. Consequences:
every object has a full version history like a git log keyed by id
("find the changeset that removed the player→sword relation" answers
"where did my sword go", plus when and why from commit context; the C
server cannot answer that at all). Subgraph movies: take the subgraph
reachable from X over chosen relations, scrub forward by applying
changesets that touch the frame and backward by the prior-value walk,
with the frame recomputed as relations change (the sword's new holder
enters the picture). Uses: incident investigation (Bunta, dupes, lost
items, crashes), builder review of a zone over time, a player's own
story played back, debugging live data with single-step; also a fix for
player memory: how they got into their current regrettable state, and
resurrecting things they learned and forgot. Cost is reads only:
snapshot + filtered deltas; the web front end's graph view with a time
slider is the natural renderer.

**AI agent over the stream and log.** The changeset log is already the
form an agent works best with: discrete, timestamped, semantic facts with
ids to follow. Tools: history of an id, subgraph at a sequence, diff
between two sequences, search commits by context/field. Answers cite the
changeset sequences used, so reported history is checkable. Uses:
support that knows ("where did my sword go" with commit, time, cause);
NPCs with real memory (a sage who recounts what the player did and
reminds them of the clue from three months ago); a builder's assistant
(explain what an edit did in play, flag rooms nobody reaches); watchers
on the live stream (dupes, gold from nowhere, impossible states, with
evidence). Scope from the start: player-facing agents confined to that
player's subgraph, admin agents with an audit trail of what they read;
scoping is the movie's frame computation, enforced rather than chosen.

**Language.** Sam is also weighing Common Lisp (SBCL) for the rewrite.
Case for: live image (redefine while players stay connected; every fix
this week needed a restart), CLOS multiple dispatch for the rules
(spells, item interactions, modifiers; `:around` methods as the place to
emit changesets), conditions/restarts instead of "signal trapping" and a
reboot loop, world files and mob programs as reader/macros replacing the
Zone/AMPL yacc compilers, native speed, `save-lisp-and-die` as snapshot,
Sly/SLIME into the running game (inspect the reporting player in place,
send to their telnet session, puppet an NPC). Cost: NATS — ccQ is the
Common Lisp client (core pub/sub only, not listed JetStream-enabled);
JetStream via CFFI to nats.c which has it; Postgres via postmodern is
first-rate; UOP would be ported (side project). Sam's POV: the running
image is the truth, the DB/log are what can be reconstructed; the gap is
exactly the unlogged tick churn. Sam already wrote a Python parser for
the world/mob-program formats (regular structure, factorable warts) and
the JSONL extraction (§12) exists, so the path is: JSON → CLOS classes
via initialize-instance → refactor to Lisp-native representation, pulling
relations out into the triple store at load.

**Pydantic for live game objects.** Methods are fine on models; the real
frictions are identity (generated `__eq__` is by value, unhashable unless
frozen — fix: eq/hash on the id), per-assignment overhead through
pydantic's `__setattr__` (leave validate_on_assignment off), and cyclic
object graphs (gone by design since relations live in the triple store,
objects hold only their own properties). With those, the model doubles as
the save format (model_dump / model_validate) and schema. Things a
pydantic model can't do like a plain class: positional construction,
`__slots__`, unannotated class attributes (need ClassVar), underscore
field names (become private attrs), `model_` namespace, a second
metaclass, free `__getattr__`/`__setattr__` overrides; opt-in: extra
attributes, arbitrary field types, validate-on-assignment, hashing via
frozen; properties are not fields unless computed_field.

**Ids (UOP pattern).** Every persisted object, and everything in a
relation, gets a uniform id: class id + instance id, base-62 strings. The
class id is a 32-bit random number fixed once in source as a ClassVar per
persisted class (git is the registry; never reuse a retired one; a
five-line test for duplicates/missing); the instance part is 64 random
bits. ~17 chars, URL/JSON/subject-safe, a dict key everywhere. The class
prefix makes the id self-describing: a changeset consumer knows the
table from the id; dereference = prefix dispatch + PK read; "all
relations involving any Room" is a left-anchored LIKE, a btree range
scan in Postgres with C collation or text_pattern_ops; in memory, prefix
walk or a per-class id set. Distinct from vnum (prototype name); the
instance→prototype link is a field or triple. Class fixed at birth: an
object changing class is a new id plus a changeset retiring the old one.
Collision: 32 bits is fine for hundreds of classes; 64 bits fine for any
size this game reaches; creation order comes from the changeset stream,
not the id.

**Engine loop documented** (2026-09-30): `explorations/game-engine-loop.org`
describes `game_loop()` (comm.c:91) pass by pass at 100 pulses/s: select,
accept, per-connection input with command resolution and priority queue
at enqueue, one event slot of the 6,000-slot timing wheel per pulse, one
command per connection per pulse gated by wait state, output/prompt
states, then periodic work (zone save 10 s, zone reset ageing 60 s,
sounds 60 s, sector damage 4 s, pulse affects 1 s, class resources 2 s,
the 60 s tick: long-term scheduler, weather, spell durations, idle
boots). Event types and producers (mob AI ~1/s per mob, per-attacker
strikes timed by calc_speed, per-character and per-object tick updates,
run/travel/fall/river/teleport/door/spell), the tick-granularity
scheduler, mob AI order, wait states, signals, shutdown, cost model,
quirks, and rewrite implications (frame + timing wheel + coarse
scheduler; the per-second character_list walks are the only
world-size-scaled cost).

**Mobs documented** (2026-10-02): `explorations/mobs.org`. Mobs are
`char_data` with ACT_ISNPC; no trigger on player arrival: they act only
from their own ~1/s think (`act_state` priority list: group, drop lost
fight, special proc, hatred decay, lag/charm/paralysis, healer, fight,
hunt, aggression every 4th think, aid friends, scavenge/items, default
position, hateful, afraid, wander every 5th think, guardian) and from a
player's command in the room running the mob's special before the
command (SPEC_CMD/MOVE; order room, worn, carried, mobs, floor). Memory:
hates/fears by category (race, sex, alignment, class, vnum) plus
individuals for one real hour, added on blows landed when patience
(health%) < alignment gap, spread by citizens/police once a minute.
Hunting: SetHunting on flee/fear/special/notoriety, budget level+1..50
steps, one shortest-path step per think, zone-bound unless FAR_HUNT.
117 C specials bound by vnum; no scripted mob language in src.

**Rewrite requirement (2026-10-02): instance identity.** The C server has
no identity for mob or object instances: a vnum names the prototype, and
an instance is distinguished only by its memory address (reused after
death); player files store copies of objects, not references. Hatred,
hunting, grouping and the long-term scheduler all work around this with
pointers validated against live lists, and "same vnum = friend". Every
mob and object instance must get an id at creation (UOP form, class
prefix + instance part), kept for life; prototype becomes a field; all
relations, memory, saves and changesets reference the id.

**Players documented** (2026-10-02): `explorations/players.org`. Accounts
(acct_data, A_ flags, tagged-binary file under account/<l>/, creation
prompts, menu, 64-char limit, warehouse, granted/revoked) vs characters
(char_data with ACT_ISNPC clear; identity is the case-folded name;
tagged-binary file under stash/<l>/ with version marker 245 / v6, every
field by tag, inventory and equipment serialised inline as copies,
affects; load room in tag 49). Creation: S/C/R methods → do_start
(level 1, exp 1, 10 hp, class spells/skills, bread/water/map/recalls).
Progression: mortal 1-500, per-class exp table, remort resets to level
1 with a stat bonus and remort_count++, apex levels beyond; immortals
2001-2011 with I9/I10 gating most wiz commands, owner list hardcoded
for I10/I11. Sessions: reconnect to a link-dead char, autosave ~100 s,
idle save/void/extract at 5/720/1440 ticks, link loss saves and keeps
the char in world, camp needs a RENTABLE room, quit elsewhere loses
gear, PK cooldown blocks both. Death: exp penalty, <20 spared, >100
years becomes a ghost, corpse, respawn LOAD_ROOM_MORTAL. Purge: -p
parsed, purge code fully commented out. Quirks: pw hash and email in
both files; objects are copies with no identity.

**Objects documented** (2026-10-02): `explorations/objects.org`.
Prototype (obj_db index_mem: template, counts, max_exist/max_for_player,
special) vs instance (a copy with no identity; five mutually exclusive
location pointers plus intrusive lists). 31 item types with per-type
value[] meanings named in the world files; wear flags and 22 wear slots;
extra flags (15 unused bits); CONT_ flags with a Mastermind crack game.
Rarity (5 levels, colours), tiers, mutate_object (random karma'd applies
with name modifiers, cap 15 applies), sockets (gems add socket_apply[]),
item sets (two-piece+ bonuses; the 09-28 crash site). Sources: zone
resets only (load_obj: count-to-needed, probability per copy, >100 =
~0.1%, max_exist), imm load, corpses, specials, shops. Per-object tick:
timer2 phase-out, biodegrade, corpse decay with spill, lights. 13 object
specials. Persistence: inline in player files as a diff against the
prototype (unmodified items are ~just the vnum; prototype edits change
saved copies), WorldSave/zone.N every 10 s for saveable zones, lockers,
account warehouse. extract_obj frees with no log.

**Rooms documented, docs cross-linked** (2026-10-02):
`explorations/rooms.org`: room_data (vnum-hashed, light/dark counters,
exits list with door flags/keys/reset timers/crack codes, river and
teleport fields, tracks ring, max_people, cached map, special), 26
room flags, 30 sectors with per-sector move cost/delay/tracks/damage and
minimap glyphs from world/SECT, look_room contents, the do_move flow,
zones (range, save range, reset type/freq, zone_limit, boot_only, the
load grammar), ageing/reset every 60 s, WorldSave every 10 s for
saveable zones, live room edits via redit/rsave into lib/UPDATE, 18 room
specials. All five exploration docs (engine, mobs, players, objects,
rooms) now carry "See also" lines and org links to each other's files
and headings (`[[file:x.org::*Heading]]`).

**Policy (2026-10-02): no behaviour changes in the C code.** Changes to
`src/` are only bug fixes or added functionality; gameplay rule changes
go into the Python/CL rewrite. First item on that list: `quit` outside a
RENTABLE room drops all carried and worn gear on the floor
(`do_quit`, other.c:538; under level 10 bounced once, above it needs
`quit yes`, immortals exempt); link-dead players keep everything, so
the rule only bites those who type quit. Rewrite: quit means quit,
inventory saved; keep the fighting/PK-cooldown/charm refusals and the
die-if-stunned rule. Also noted: `quit +N` is a hardcoded debugging
back door for an owner account and two names.

## 17. Rewrite: the semantic layer first (discussion, 2026-10-02)

The docs in `explorations/` (engine loop, mobs, players, objects, rooms,
all cross-linked with CUSTOM_ID anchors) describe a frozen artefact; the
C code gets bug fixes and new features only. The rewrite (Python or CL;
CL favoured) is not "port 106k lines" but: build a small semantic layer
of CLOS classes and generics for this kind of MUD, then say the game in
it. The JSON/pydantic extraction is the import path, not the model.

**Findings that shape it.** Mob and object instances have no identity
(prototype vnum + memory address; objects are inline copies in whatever
holds them; mobs are persisted only with the rooms of a zone's save
range (SaveMob/LoadMob, every 10 s, restored at boot: a correction of
the earlier "never"), and even those have no identity, so a mob cannot learn or
grow). The prototype is genotype, the incarnation a runtime phenotype,
and there is no "individual" layer between. Specials bind by a hardcoded
vnum→C-function table (386 rows, 94 functions: 38 reused behaviours on
330 rows, 56 one-off set pieces); the `special` act flag is not the
link. A special runs first in the think and either consumes it (return
true) or falls through to the canned list, which is a hand-rolled method
combination. The canned behaviours (aggression, wander, hunt, hate,
assist, scavenge, citizen, healer) are themselves rules of the same
shape; `ACT_*` flags are just which are attached. Many rules have no
natural owner (damage between attacker, weapon, victim; key vs door;
visibility), which is the case for multiple dispatch over receiver
tables.

**The layer** (each a few hundred lines, testable alone):
- Engine: clock, event wheel (FIFO slots), per-pulse step (fire due
  events, one command per session, periodic work), single mutator,
  injectable clock for tests/replay.
- World: kinds / individuals / incarnations with UOP-style ids,
  prototype link as a field, the indexed relation store with move/wear/
  fight helpers; `where`, `contents`, `occupants`, `holder` as generics.
- Event + Scene: event vocabulary (enter, leave, command, say, hurt,
  death, timer, think, tick); Scene = roles (bound to kinds or
  individuals), triggers, guards, actions (message, move, spawn, give,
  fight, flag, set phase, schedule), phase; a kind or individual carries
  an ordered scene list (head runs, may call next — the "cheap
  call-next"; push to override, pop to roll back). Specials are scenes
  with fixed participants; canned mob behaviours are scenes with none;
  flags disappear. Behaviours are named in the mob definition and
  resolved by name at load, loud error if unknown. A persistent mob
  individual (NPC-player) is the player save path pointed at a mob;
  which kinds spawn individuals is per-kind.
- Rules: generics (`damage`, `affect`, `can-see`, `can-enter`, `price`)
  specialised on participant classes (class, race, item type, sector,
  alignment as types); the 450 spell functions collapse to a dozen
  patterns plus table rows; "semantically the same" as the C, not
  transcript-identical.
- Journal: changesets emitted from the mutation generics, publish path,
  snapshot/restore.
- Session: connection with queues and a renderer (telnet or bot),
  accounts and login state machine. Bots: a connection whose far end is
  a program; scripted bots as test harness/load; rule-driven NPC
  players; model-driven characters consulted on events, not per think,
  rate-limited like anyone. An LLM+harness playing by telnet with its
  own memory/map/notebook, told almost nothing, measured against what a
  good player knows (not the engine docs), is a planned experiment.

**Estimate** (semantic equivalence, not transcript diff): core world you
can walk in, 1–2 weeks of sessions; rules 3–4 weeks; long tail (56
scenes as builder-notation data, boards, mail, clans, arena, builder
tools) a few weeks, triaged by zones people play. Order: identity and
relation model first; nothing above it until it exists.

**C code quality notes (2026-10-02).** 106,237 lines by purpose: rules
(combat/magic/spells/skills/limits) 29%, commands/UI 17%, mob AI +
specials 12%, storage/formats 11%, pointer bookkeeping (handler.c,
utils.c) 7%, imm/builder tools 7%, network/sessions 5%, shops/boards/
mail/clans 4%, tables 3%, leftovers 5%. Structural housekeeping is ~25%
by file, but inside the rules files most lines are repeated guard
checks, act() message variants, affect-struct filling and type
switches, so lines that state a game rule are on the order of 20k:
"80% drivel" is about right by content. No list type: every struct
carries its own `next` (objects two: global list and container/room
chain; characters `next` and `next_in_room`), each chain has its own
insert/walk/remove code, nothing shared, no macro. The unlink idiom
`prev->next = cur->next` is hand-written 25 times in 12 files;
membership (loop + pointer compare) ~18 times (9 in magic.c);
validate_char/validate_obj scan the whole global lists before firing
scheduled events; removal is one function per relation (char_from_room,
obj_from_char, obj_from_obj, affect_from_char, ...). Only ten functions
take a function pointer at all; the only iteration helpers are
hash_iterate(_range) over the vnum hashes and for_each_char (copies the
list first); no find_if/remove_if/member-with-predicate for any chain,
so conditions like "can see" are re-inlined per call site. The 09-28
use-after-free was this idiom. If the C had a future, the best refactor
is a small chain library (find/for-each/unlink with the head case done
once) plus typed predicates: safe, mechanical, and still a simulation
of lambdas with void* contexts — hence not worth a month given the
rewrite. In CL all of it is member/find-if/remove/dolist and the
relation store; the `next` fields and most of handler.c have no
counterpart.

**GenericDiku (idea, 2026-10-02).** The semantic layer in §17 is mostly
Diku-generic: every Diku descendant (Circle, ROM, Smaug, PR) shares
vnums, zones with reset commands, rooms/exits/flags, the mob and object
prototype field set, affects/applies, the pulse loop, intrusive lists
and vnum-table specials; what differs is rules tables, class/spell
lists and one-off scenes. So: a generic CL package (engine, world model
with identity and relations, events and scenes, journal, sessions,
importers for Diku/Circle and PR world formats; the exploration docs
are near enough its spec) and a per-game package on top (rules as
methods and tables, scenes, builder notation, content), with PR as the
reference implementation. Audience is small but the common case out
there is a 1995 C codebase one person still understands; a package that
re-expresses such a game in a few thousand lines, keeps its world
files, and adds live editing and real persistence could carry a dozen
of them through their next decade. Historical aside recorded: the
genre's object model is Zork's (MDL/Lisp, 1977–79) but the multiplayer
line was assembler→BCPL→C (MUD1, Aber, Diku 1990), rebuilding Lisp
machinery by hand ever since; this code even carries a dead Ruby
embedding (ruby_cmds.c, -DNO_RUBY). Guile scripting on the C base is
possible but spends effort on the layer the rewrite replaces.

**Combat documented** (2026-10-02): `explorations/combat.org`. No rounds:
per-attacker EVT_STRIKE chains at calc_speed (par 1/s; players
100+10*level/speed_level × weapon speed/10 × dex, capped by class;
mobs attacks_per_round×100). set_fighting caps a mob's attackers at 6
(ok_to_fight says 10/12). To-hit: hit location from aim vs dex/int or a
height-class table; THAC0 = max(200-10*level/thaco_level, thaco_min*10)
- 7*hitroll (mobs 200-10*hitroll), + half missing weapon proficiency,
- str; d200 vs thac0-AC[loc], >196 auto-hit, <5 miss; AC per location
±100. Damage: str bonus + weapon dice × proficiency (or mob dice), crits
on a d200 window from remort/precision, location multipliers (head
1.11..feet 1.0). damage(): resistances/immunities by damage type with
saving roll (d100 vs resist score ≤95), stopping[loc]+worn−penetration
subtracted (sanctuary adds flat stopping, not halving), absorb pulse
affects, item damage on heavy blows, hit_shield, then hp; positions by
hp (−3 incap, −6 mortally, −11 dead); wimpy flee; die → SPEC_DEATH,
alignment, death cry, group_gain (victim exp / sum of present group
levels, then per-class curve), corpse, players to LOAD_ROOM_MORTAL with
1 hp. Flee: random open exit, roll to stumble, exp loss outside arena,
leaves a hunter. PK is global except PEACEFUL rooms; aggressor becomes
criminal with a 15-min rent_disable. ~30 skill commands share one shape.

**Spells documented** (2026-10-03): `explorations/spells.org`. Two tables
must agree by number: engine `spell_info[]` (beats, position, flags,
TAR_ target bits, cast_ wrapper → spell_ function) and the per-class
rows in world/CLASSES (level, difficulty, guild max, mana, source P/M,
prereqs, components); 253 spell numbers, ~450 functions. do_cast: form,
NO_MAGIC, class entry, position, level/silence/confusion, cost (×(1+
difficulty) without reagents, ÷ remort efficiency), delay = ¼ s +
4 s×(beats−1) − haste, d101 vs learned% (+ iron power_penalty), failure
costs half mana and may improve the spell; EVT_SPELL after delay, say_spell
syllables. Completion deducts cost and resolves the target then. Spell
shapes: damage (dice by level → damage() with GetSpellType damage type),
affect (affected_type: duration ticks, APPLY_ location, modifier, bits;
aged per tick with wear-off messages), direct (heal/dispel/teleport/
create). Saves: CalcResistanceCheck blends stats per damage type, d100 ≤
min(95, …). Pulse affects: wall-clock procs every second (DoT/HoT/shield),
cooldowns; a partly wired data-driven Effect system (effects.tran).
Items: potions/scrolls/wands/staves/weapon spells via SPELL_TYPE_;
components by vnum. Learning: practice at guildmasters with
spells_to_learn, use raises %, remort zeroes. Mobs: mob_attack on strikes,
act_caster/eval_spells on thinks.

**JSONL + pydantic coherence (2026-10-06).** `py_json` now extracts 25
types; new: spells (spell_info/skill_info rows from spell_func.h joined
with names, wear-off messages and GetSpellType damage types), commands
(inter.h), applies and name_tables (names.json), messages
(world/MISC/messages), socials (world/MISC/actions), help
(world/HELP/help_table with .usage/.xrefs split out), lockers
(lib/LockerSave), worldsave (lib/WorldSave/zone.N incl. saved mobs,
exits, items), limited (limited.obj), boards (lib/*.board). Options
`-s src`, `-l lib`, `--raw`. The canonical JSONL shape IS the py-pr
model's `model_dump_json(by_alias=True, exclude_unset=True)`: the CLI
passes every record through the model (`prworld/canon.py`, importing
`../py-pr/src` and its .venv's pydantic) so load→dump is the identity;
`py-pr/tools/roundtrip.py` proves it for every line of every file (all
25 pass; `validate_jsonl.py` too). py-pr: `PRRecord` base gives every
top-level record a UOP-style `id` (fixed 6-char base-62 class id in
`CLASS_IDS` + 11-char instance part; deterministic from the natural key
at extraction, random in a live system), eq/hash by id; `SavedMob`,
`SavedExit`, `WorldSaveRoom`, `SparseResistances`, `Regens` added;
`SpellDefinition`, `CommandDefinition`, `Social`, `DamageMessage`,
`HelpEntry`, `Board`, `Locker` reshaped to the extractor; item-type
fields are `SerializeAsAny` and saved spell/charged/trap variants carry
`saved: true` so dumps re-validate to the same class; untyped slots
survive. Findings while doing it: mob.save.c and room.save.c each have
their own tag numbering (WEAR is 251 in a mob save, END_OF_LIST in a
player file); SaveMob writes time_t as 8 bytes while the player file
uses 32-bit times; WriteA on s32 arrays writes the real byte count, so
the "sh_int" in the macro call is a lie the reader must ignore;
SaveZone starts each file with a u16 252 header. Local lib: 115 zone
saves, 12,918 rooms, 8,455 saved mobs, 3,339 items.

**Models moved to pr-be (2026-10-06).** `py-pr/src/{classes,names}.py` and
its tools now live in the separate repo `pr-be` (github sjatkins/pr-be):
`src/pr_be/classes.py`, `src/pr_be/names.py`, `tools/{validate_jsonl,
roundtrip,gen_enums}.py`; py-pr keeps only a pointer README. Identity
reworked to Sam's spec: `from sjasoft.utils.index import make_id`
(the package is `sjasoft.utils`, plural); every PRRecord subclass has
`class_id: ClassVar[str]` set once to a literal `make_id(48)` value
(30 classes), and `id: str = Field(default_factory=...)` yielding
`f"{class_id}.{make_id(64)}"`, bound per subclass in
`__pydantic_init_subclass__`; an after-validator marks the minted id as
set so `exclude_unset` dumps carry it; a record loaded from JSONL keeps
its id, so ids are assigned once at first extraction. `py_json`'s
canon.py imports `pr_be.classes` from `../pr-be` (and its .venv for
pydantic/sjasoft-utils). All 25 JSONL files regenerated with ids;
validate and roundtrip both exit 0. pr-be/.venv came from uv; pydantic
was already in its pyproject.

**Mongo store (2026-10-06).** Local MongoDB 7 in Docker (`pr-mongo`
container, volume `pr-mongo-data`, bound to 127.0.0.1:27017, restart
unless-stopped; Docker needed `systemctl enable --now docker` and the
user in the `docker` group — done). `pr-be/src/pr_be/store.py`: Store
with one collection per record class named after the class; document =
`model_dump(mode="json", by_alias=True, exclude_unset=True)` + `_id` =
record id; `from_doc` = `cls(**doc)`; upsert by id, find/load/count/
delete/drop. `tools/load_mongo.py --drop` loaded all 25 JSONL files into
db `pr` (26,287 rooms ... 115 zone saves) and verified 50 docs per
collection come back equal. `.dict()` is pydantic v1 naming; v2's
`model_dump(mode="json")` is what gives the Mongo-safe form (flags as
name lists, enums as strings).

**Relations in the store (2026-10-06).** pr-be: `Role` (id = bare
make_id(48), no class prefix; name, reverse_name, description) and
`Related` (PRRecord; subject, role, object — all required strings; the
triple store, one triple per record) in `STORE_ONLY_MODELS`. Store
helpers: define_role, relate (idempotent), unrelate, objects_of,
subjects_of, ensure_indexes (unique subject+role+object). First role
defined in the db: `located_in` / `contains`. Direction: stop working
from JSONL; pydantic classes + Mongo are the source going forward;
refactoring (Item hierarchy with Weapon/Armor/... subclasses,
ItemInstance, rename SpellDefinition→Spell etc., fold limited counts
into the prototype, drop the one-record Skill and the reference-table
collections) is under consideration, not started.
`pr-be/docs/role-considerations.org` is the working document for which
roles to adopt, with candidate roles, what each replaces in the C
fields, the qualifier question (slot, direction, rank, percent, expiry:
proposal is a single optional qualifier field for one-value cases and
a separate record for multi-field ones), what stays a field, and a
first-steps order (character_of, located_in for inventories/warehouses,
worn_by, member_of, instance_of).
`Related.qualifier` is an optional dict ("role specialisation data",
Sam's term): e.g. `{"slot": "wield"}` on `worn_by`; uniqueness is
(subject, role, object) and `relate` on an existing triple replaces the
qualifier; `related(role=..., object=..., slot="head")` filters on
qualifier keys. Roles defined in the db: `located_in`/`contains`,
`worn_by`/`wears`. Decisions recorded in role-considerations.org.
**Decision 2026-10-08 (supersedes the qualifier dict):** `Related` is
exactly three ids, subject/role/object, RDF style, nothing else ever.
Specificity lives in the role: `Role.specializes` (parent role id);
`worn_on_<slot>` (22, generated from WearPosition) specialize `worn_by`;
`Store.related(role=...)` expands a role to its specializations
transitively (`role_ids`), `relations_of(id)` returns everything
related either way keyed by role id in one query. Values that are not
kinds (learned %, expiry, load count) are records keyed by the two ids,
not triples. Roles in the db: located_in, worn_by + 22; no Related
rows yet. Rationale recorded in role-considerations.org.

**How builder work reaches the game (2026-10-08).** Nothing automatic;
no cron job touches the world repo. Rooms: in game `redit`, then
`rsave` writes a binary room file to `lib/Area/<builder>` (+ `.bak`;
BUILD.LOG records each save; production has files 2010–2026, Nitemare
1,493 rooms last 2026-01-29). Getting that into the repo is a hand
step: `src/room2tran` converts an Area file to tran text in
`TextSave/`, or `tsave`/`save_world` write text to `lib/WORLD/`; then
copy into `world/ROOM/<zone>.room` and commit. Production has neither
`TextSave` nor `WORLD`, so that step has not been run there. Mobs,
objects, zone resets: no in-game editor at all (`load`/`set`/`oedit`
only touch live instances, never prototypes); the only route is editing
`world/MOB`, `OBJ`, `ZONE` text by hand, commit, `world/compile`,
restart. The Oct 2026 world commits (Grass_Barrows mobs and zone,
CemeteryOfHell room, MOTD) are that route. For what a builder actually
did on a given change, ask them; the files only show where things
landed.

### live/ survey from src (2026-10-08)

`explorations/live-directory.org`: every file under `live/lib` the game
reads or writes, attributed from the I/O call sites through the graphify
call graph to boot / command / login / link-loss / 10 s pulse / signal.
Headlines: the process `chdir`s to `live/lib` and all paths are relative;
`logs/` is only the redirected stderr; the compiled world and all display
text come from `world/compile` (`world/lib` is a symlink to `live/lib`);
`account.list` is never written by the game (new accounts are counted
after the next restart's `rebuild_indexes`); `skills.out` and
`lockers.save` have no reader in src; `maxplayers` has no reader;
`WorldSave/zone.N` is one saveable zone per 10 s round robin, read and
unlinked at boot then rewritten; AUTOSAVE rooms and lockers are written
synchronously on the triggering command; builder definitions reach disk
only via `rsave` (binary `Area/`) or `tsave` (`WORLD/`) and the repo only
by hand. Only-in-live: stash/account (players tar), WorldSave/RoomSave/
LockerSave, boards, auctions, Area/WORLD/UPDATE/TextSave/BUILD.LOG, the
admin lists, ideas/typos/bugs, StoryFiles, PURGED, logs.

### UPDATE/ refresh at boot (2026-10-09)

`refresh_update_dir` in `scripts/pr_functions.sh`, called from the
`PR_SERVER_SCRIPT` loop before every boot: for each file already in
`lib/UPDATE/`, copy the newer `lib/Area/<same name>` over it. Opt-in per
builder (first copy into UPDATE/ stays a human act). Fixes the stale-copy
trap where the game applied an old UPDATE/ file and the builder had to
`rload`. Also clarified in live-directory.org: creatives' hand-loaded
mobs persist only through WorldSave, not as zone reset rules.
