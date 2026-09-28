# Perilous Realms — Project State and Handoff

**Last updated:** 2026-09-28 (built master here with production players; use-after-free fix merged; production host surveyed)
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
├── transcript.md
└── SUMMARY.md   (this file)
```

`pr-stuff/` is itself a git repo (`origin/main`). `src/`, `world/`, `live/`
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
`Zone`). One new trap: **`Zone/makefile.linux` calls gcc with no `-std`**,
and gcc 15+ defaults to C23, where `bool` is a keyword and
`h/compat.h:27` `typedef char bool;` is an error. The main makefile pins a
standard so `pr3` is unaffected. Worked around by running the Zone
makefile's own commands with `-std=gnu11`; the makefile is not changed.

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
- **None of `~pr/scripts/` is under version control** (restart script,
  backup scripts, check-and-restart). Only copies are on that host. Worth
  committing to the repo or an ops repo.

### What live/lib holds beyond the player tar

The tar covers `stash/`, `account/` and the two indexes only. Also player
state, not in the tar: `LockerSave/` (clan lockers), `WorldSave/zone.N`
and `RoomSave/` (room contents), board files, the auction file, and
`PURGED/` (deleted characters/accounts, moved there by a shell `mv` the
server never creates the directory for). `full_backup_*.tar.gz` covers all
of it.
