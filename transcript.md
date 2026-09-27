# Perilous Realms (pr) — Session Transcript

Turn-by-turn record of the `pr` / `pr-world` work from a session on
2026-09-18/19. Non-`pr` turns from that session (Common Lisp questions,
Mullvad, age-verification law, Claude Code session storage) are omitted.

The session ran with its working directory rooted at
`~/private/local-projects`, not `~/work/pr-stuff` — everything below was done
via absolute paths.

---

## 1. Missing `<ruby.h>` in a makefile

**User:** "have an error in a makefile from no `<ruby.h>`. ruby is installed. dev package?"

Checked the local machine: Ruby 3.4.10 with headers present at
`/usr/include/ruby-3.4.0/`, owned by the base `ruby` package (Arch ships no
separate `-dev`), and `pkg-config --cflags ruby-3.4` returning
`-I/usr/include/ruby-3.4.0/x86_64-linux -I/usr/include/ruby-3.4.0`.

Explained that on Arch no dev package is needed — the headers live in a
versioned subdirectory not on the default include path — and that on Fedora it
would be `ruby-devel`. Gave `pkg-config` and `RbConfig`-based Makefile
snippets.

*(This later turned out to be a red herring: the real cause was using the
macOS makefile. See turn 13.)*

---

## 2. OpenSSL version check

**User:** "do I have openssl installed and if so what version?"

`OpenSSL 3.6.4` (25 Aug 2026), package `openssl 3.6.4-1`, headers present,
`pkg-config --modversion openssl` → 3.6.4. Noted that no `openssl-1.1` compat
package is installed, which matters for code using APIs removed in 3.x.

---

## 3. Two GitHub accounts in `~/.git-credentials`

**User:** "how do I set up git-credential for both my github accounts. see ~/.git-credentials"

Inspected the file with tokens redacted. **I misread my own redacted output**
and reported two `github.com` entries (`sjatkins` and `sjasoft`) when there was
only one. Gave `includeIf` / `useHttpPath` advice built on that wrong premise.

---

## 4. Clone fails

**User:** pasted

```
git clone https://sjatkins@github.com/cabarius/pr.git
remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed for 'https://github.com/cabarius/pr.git/'
```

Byte-exact re-check of `~/.git-credentials` showed **one** `github.com` line,
for `sjasoft`. `sjatkins` appeared only inside the hostname
`git.sjatkins.consulting`.

---

## 5. "Is something overwriting my git-credentials?"

**User:** "because I have put in an extra line for sjatkins twice now and saved it."

Yes — `git-credential-store` implements `erase`. When a credential it supplied
is rejected, git calls `erase` and the helper **rewrites the file without that
line**, silently. Evidence: the file was 752 bytes at 21:18 and 683 bytes at
21:31, one line lighter, across a failed clone.

**User:** "that is very unexpected and absurd behavior" — agreed; it is
indistinguishable from data loss when the file is one users are told to
hand-edit. Workarounds: validate the token with `curl` before git touches it,
or `chattr +i` while debugging.

---

## 6. Root cause of the clone failure

New `sjatkins` classic PAT was added and still failed, without being erased.
API checks showed the token was valid:

```
login:  sjatkins
scopes: repo
cabarius/pr: HTTP 200        ← access confirmed
```

The failing prompt read `https://sjatkins@github.com/cabarius/pr.git` — **with
the path**. Cause: `credential.usehttppath=true` had been set in
`~/.gitconfig` (from my own earlier suggestion). With it on, `store` matches on
protocol + host + username + **path**, so a host-only credential line no longer
matches.

Fix applied:

```sh
git config --global --unset credential.useHttpPath
```

Clone then succeeded. Both credential lines left intact.

---

## 7. `./pr3` dies at boot

**User:** "ran into this problem and I remember vaguely some dance is needed with ../pr-world stuff"

```
Boot db -- BEGIN.
termcap: No such file or directory
```

Traced it:

- `main.c:110` → `dir = DFLT_DIR`; `h/const.h:1439` → `#define DFLT_DIR "lib"`
- `main.c:250` → `chdir(dir)`
- `termcap.c:82` → `fopen("termcap","r")`

`pr/lib` is a stub containing only `motd.c`. The real data directory is
`pr-stuff/live/lib`, which **did not exist**. `pr-world/lib -> ../live/lib` was
a dangling symlink, and `pr-world/compile` copies everything (including
`MISC/termcap`) to `../../live/lib/`.

---

## 8. The build/run "dance", performed

**User:** "do the things you think are needed though I don't see why we need a ../live separate directory. Seems quite nuts"

1. `mkdir -p pr-stuff/live/lib`
2. Built `tran` — `cd pr/tran && make -f makefile.linux` — it was missing
   (gitignored) and `pr-world/compile` calls it. Built clean; **no Ruby
   required**.
3. `cd pr-world && ./compile` → populated `live/lib` with `world.out`,
   `zone.out`, `mob.out`, `obj.out`, `shop.out`, `classes`, `help`, `MISC/*`
   including `termcap`.
4. Created `live/lib/RoomSave` and `live/lib/WorldSave/Misc` — both opened with
   plain `fopen()` and never created by the server (`room.save.c:151`,
   `world.save.c:115`).

Server then booted to `Boot db -- DONE` / `Entering game loop`.

---

## 9. Second run died: `No player files.`

`db.c:288-292`:

```c
if (bypass_scan) {
    if (!(f=fopen(PLAYER_FILE,"r"))) {
      vlog(LOG_DEBUG,"No player files.");
      exit(1);
    }
```

`bypass_scan = LoadLimitCount()`, which returns 1 only when
`WorldSave/Misc/limited.obj` exists — written on every clean shutdown. So the
*first* run worked and the *second* exited. `PLAYER_FILE` is `"players.new"`
(`h/const.h:1455`).

---

## 10. "Why is that a fix? what of preexisting players?"

Correct challenge — `touch players.new` is right only for an empty world.
Found two backups in `pr/backup/`:

- `PR-players-120829.tgz` (1.6 MB) — **self-contained**: `lib/stash/` (555
  characters), `lib/account/` (136 accounts), `lib/LockerSave`,
  `lib/stash/players.new`, `lib/account/account.list`
- `PR-lib-20120829.tgz` (34 MB) — full 2012 `lib` snapshot **including
  2012-vintage `world.out`/`mob.out`/`obj.out`**; must NOT be untarred over
  freshly compiled world data

*(I initially said the players tarball lacked account files. Wrong — it has
them.)*

---

## 11. Accounts vs characters

**User:** "what is relationship between account and players?"

- **Account** — `acct_data` (`h/structs.h:783`), stored at
  `account/<first-letter>/<name>` (`account.c:21`). Holds password, email,
  balance, warehouse, ignore list, and `char_list[]` + `num_chars`.
- **Character** — stored at `stash/<first-letter>/<name>`
  (`player.save.c:49`), points back via `account_name` (`h/structs.h:742`).
- `char_account_valid()` (`account.c:298`) requires both directions to agree.
- Login password is account-side, so characters and accounts must be restored
  together.
- Indexes: `players.new` (characters, read at `db.c:317`) and `account.list`
  (accounts, `db.c:589`, plus `popen("wc -l < account.list")` at `db.c:187`).

---

## 12. Player restore

Extracted `PR-players-120829.tgz` into `live/`, then moved the two index files
up one level — the tarball stores them at `lib/stash/players.new` and
`lib/account/account.list`, but the server opens them bare from `lib/` root.

Result on boot: **554 players loaded**, no version errors, no
`Invalid account` warnings — the 2012 files load fine against
`CURRENT_PLAYER_FILE_VERSION 6`.

Discrepancy: 556 index entries, 554 loaded. One entry (`suzie`) has no file in
`stash/s/`; one more is unaccounted and was not chased down.

---

## 13. README

**User:** "now can you put a README.md in pr directory for all the steps that are needed to build it from source"

Before writing, established the real build story:

- The default `makefile` is the **macOS** build — `-framework Ruby`,
  `/System/Library/Frameworks/Ruby.framework/Headers`. **This was the source of
  the `ruby.h` error in turn 1.**
- `makefile.linux` compiles with `-DNO_RUBY` and needs no Ruby.
- `make -f makefile.linux all` builds `pr3` fine but then **fails** in
  `subproj` at `trident_client`, whose Makefile hardcodes
  `/usr/local/liboqs/lib64` (only valid on the host named `demon`):
  `/usr/bin/ld: cannot find -loqs`. Harmless — `pr3` is already linked.
- `pr3` links the bundled `trident_libs/*.so` via
  `-Wl,-rpath,'$ORIGIN/trident_libs'`, so no system liboqs is needed.

Wrote `pr/README.md` covering prerequisites, build, `live/lib` creation, world
compile, the `players.new` decision, running, and a troubleshooting section
keyed to each error actually hit.

---

## 14. Branches, commit, push

**User:** "created new branch called sam_build in both pr and pr-world. add the README to pr. commit and push all to that branch"

No `sam_build` existed in either repo, locally or on the remotes after a fresh
`git fetch` — created them.

- `pr` → `7732ab5` "Add Linux build/run README; drop -L/usr/lib from
  makefile.linux". Included a pre-existing uncommitted change to
  `makefile.linux` (removal of `-L/usr/lib` from `LIBS`) that was already in
  the working tree.
- `pr-world` → branch created and pushed with **no commit**; working tree was
  clean.

---

## 15. The other README

**User:** "What is the README file (vs README.md) from"

A macOS/Xcode setup doc by Simon, last touched **February 2014**: Swig ≥1.8,
Ruby ≥2.0, Xcode command line tools, `pr.xcodeproj`, `swig -ruby ruby/pr.i`,
symlinking `pr-world/tran` and `pr-world/syntax` into Xcode's Derived Data.

It confirms the `live/` layout predates everything — step 1 refers to "the 3
required folders" and the Xcode launch args include `-d /Users/simon/live/lib`.
Step 3 reads, in full: *"live folder required?"*

Renamed to `README.macos-xcode-2014` (`git mv`, so history follows) and added a
pointer to it from `README.md`. Commit `c70b7dd`, pushed.

---

## 16. Game name

**User:** "what is the full name of this game?"

**Perilous Realms** — the ASCII banner in `live/lib/welcome`, and `credits`
opens "Current Perilous Realms coding and design team." `pr3` is version 3 of
the server.

---

## 17. Dockerfile

**User:** asked whether a Dockerfile would build from source or ship a binary,
then: "it has to pull everything it needs to build itself not depend on host
things", then noted builds would run in GitHub Actions "already within the
trusted repo space".

Agreed the Actions context removes the need for in-Dockerfile cloning and
secrets: check both repos out side by side, build with the workspace root as
context, `COPY` in the builder stage.

**User:** "so what would be best first? github actions to pr or building a
Dockerfile for pr?" → Dockerfile first, since Actions would only invoke it,
iteration is far faster locally, and it can be verified by actually booting.

**User:** "I don't want with no players. This is attempt to revive the game as
an installable docker for its maintainer who definitely will want to keep
existing players."

Redesigned around **seed-on-first-run**: the image carries an unpacked player
snapshot; the entrypoint seeds `/data/lib` only when it has no player database,
so upgrades never clobber live data.

Wrote `pr/Dockerfile` and `pr/docker-entrypoint.sh`. **Not yet built** — the
session's user is not in the `docker` group and `sudo` requires a password.
