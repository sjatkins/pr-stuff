# Perilous Realms — Future Architecture

Design notes from a conversation on 2026-09-19. **Out of scope for the current
remit** (Docker packaging for a single maintainer — see `SUMMARY.md` §11), kept
here so the thinking is not re-derived.

Starting point: a 2023 Python effort captured everything that is *data* in
`pr-world` into Mongo — rooms (with full descriptions), mobs, objects, etc. —
with a standard UUID per thing whose encoding identifies its class and so its
collection. What was not done: the game *dynamics* in `pr`. The Python project
is not on this machine.

---

## 1. Data model: a property graph

Everything is a node with a class-typed UUID. Relationships are triples in one
dynamic table:

```
(subject-id, role, object-id)
```

Almost everything a MUD does at runtime is a relationship, not an attribute:
player *in* room, sword *carried-by* player, mob *in* room, exit *connects*
room to room, spell *affecting* character, player *following* leader.
The `SUB` entries in the C schema tables (`PRLib/fields.c`: `room_fields` →
`exit_fields`, `char_data` → inventory) are exactly the edges.

- Index the table **both directions**. "What's in this room" is a lookup on
  `(object-id, role)`; the hot path is the reverse query.
- The class prefix in the target UUID removes the polymorphic-foreign-key
  problem ("a container can be a room, a player, a corpse or a locker").
- Rigid typed records (stats, flags) fit SQL-shaped documents; the nested
  shapes (room + exits + extras, character + inventory) fit documents. It may
  split rather than go one way.

### Prototype vs instance

The C conflates these via `index_data`: `obj.out` / `mob.out` hold
**prototypes**; a spawned sword or the Demi-Lich on his throne is an
**instance** with its own hp, condition, contents, affects, pointing back at
the prototype. The data capture naturally saw only prototypes — instances did
not exist in `pr-world` to be captured. Where instances live, what they carry
versus inherit, and how they reference the prototype is the first decision the
dynamics depend on.

### Rules as data

`nosummon` (a player refusing to be summoned), `NO_TELEPORT` room flags, clan
halls admitting only members — today scattered across bitfields in three
structs — are all the same shape: a fact about the target that a rule consults
before permitting someone else's action. `(player, refuses, summon)`.

---

## 2. One primitive, many policies

Nearly every action is **moving one edge**:

```
drop:      (sword, contained-by, player) → (sword, contained-by, room)
get/give/put/loot/sell: the same edge, different target
walk/goto/transfer/summon/follow: (character, in, room-A) → (character, in, room-B)
```

What differs is the **policy** wrapped around the move:

| who | gate |
|---|---|
| walking | an exit exists, it is not closed, I can move |
| `follow` | the leader moved and I am linked to them |
| `summon` | mana, level, target has not set `nosummon` |
| immortal `goto` / `transfer` | rank |
| builder `redit` / `rdig` | rank |

Derived counts (limited items, `world_count`, who is online, auction house)
become queries over edges instead of hand-maintained tallies that drift.

---

## 3. The two heads: global view and session view

This is **not** a multi-tenant app. There is one shared world; the whole game
is people affecting each other's slice of it.

- **Global view** — one owner (the equivalent of `pr3`'s single-threaded game
  loop), the graph, all mutations serialised through it. The only truth. This
  is what wants the store underneath.
- **Session view** — a cursor plus a perception filter, per connection,
  holding almost no state of its own (which character, which room, what they
  typed). Derived; needs no persistence.

The C blurs them: `char_data` is both a world object and the session identity,
which is why it is the biggest schema table and `player.save.c` the gnarliest
loader. Splitting "character as world object" from "account's session" is
likely the first refactor the model pushes toward.

`at <player> <cmd>` is a pure session-side operation — re-point the cursor,
run one command, point it back. A good example of why the session should be a
lightweight cursor.

### Perception and radius

Actions feed **up** into the global view (the mutation) and **out** to whoever
can perceive them (the event). `CAN_SEE(viewer, target)` in the C is a pure
pair predicate — invisibility, light, blindness, level — with no notion of
location; room scope comes from the caller walking `rp->people`. So:

- Passive perception is **room-only**. An open doorway gives nothing for free.
- **Radius belongs to the event/action, not the viewer.** The game has a small
  fixed set of radii and they are the same operation with different parameters:

| scope | radius | note |
|---|---|---|
| room | 0 | the only passive one |
| `scan` | 1 hop, skips closed doors | active, skill-checked, probabilistic (`cmds1.c:1032`) |
| shout / sound | 1 hop | |
| zone channels | zone | |
| gossip, `who` | world | |
| `pwhere` (I4), `where` (I5) | world, filter ≈ identity | the Global View handed out as a session |

Keep radius and filter as parameters; every later feature (locate-object
spell, clairvoyance, a web admin map) is a new point on the same dial.

Fan-out cost scales with radius × population; the tick loop's serialisation
is the natural batch boundary. Keep it.

### The privilege ladder is shaped for helpers

`goto` is `I1` — the very first thing a new immortal gets is the ability to
reach a player who needs help. `at` is `I2`, `transfer` and `pwhere` are `I4`.
A junior helper can go to someone who asked; they cannot yet go looking.
Mortals get the same primitive gated by cost and consent: `summon`,
`nosummon`, `follow`.

---

## 4. Loading and resets

- **Load by room, on demand, by proximity.** A player's footprint is their
  room plus one hop of exits (for `scan`/shout) — six to eight rooms, not a
  zone. Both-direction indexes make each step a lookup. Cold rooms cost
  nothing.
- **Reset by zone, against the store.** The `.zon` file is already a
  declarative desired state: `in 0 load atmost 15 obj 1000`, door states, mob
  load chains with equipment. A reset is a batch of idempotent upserts —
  "ensure `count(X in R) ≤ N`, add instances from the prototype until true" —
  which can run on cold rooms without loading them. Reset never removes
  anything; `atmost` is the safety valve.

Replace the cron (`zone_update`, `zone.c:930`, which sweeps every zone every
tick and recounts every prototype in the world) with:

| C mode | replacement |
|---|---|
| `ifempty` | **reconcile on load** — when a room comes off disk and the zone's interval has elapsed, top up, close doors, stamp the time. Observationally identical; nobody was there. |
| `always` | **per-instance respawn timer** — when a mob dies, schedule its replacement at now + freq. A row in the time-indexed timers table. Preserves camping and learned reset rhythms. |
| `never` | no desired state recorded |
| `boot_only` | a one-time seed applied when the zone is first imported |

The only zone-level state needed in memory is "last reconcile time" and
`zone_empty()` — one indexed query on `in` edges within the range.

### Memory / store boundary

Write-through for edges that matter if the process dies (location,
containment, hp). Don't persist the ones that don't (fighting, following —
rebuilt or dropped on reconnect). This is the distinction the C makes
implicitly by only saving players and `AUTOSAVE` rooms; make it explicit per
edge type.

---

## 5. Builders are privileged users

With the store in place there is no "edit the source and rebuild" versus
"edit in-game and hope the room is flagged `AUTOSAVE`". A builder change is
one write with a **propagation policy** — a property of the edit, not the
architecture:

| policy | behaviour | use |
|---|---|---|
| on next visit | cached room invalidated; next load gets the new version | description tweaks |
| when empty | applied when the last player leaves | structural changes |
| immediate | occupants see it now, optionally with an event | live events, GM work |

The loaded room is a subscriber like any player in it; a builder commit is the
same fan-out as a dropped sword with a different actor. Prototype changes can
propagate "immediate" (rebalance a monster mid-game) or "on respawn" — the C
can only do the latter, after a restart.

The C already models builders this way: `redit`, `rdig`, `zreset`, `zpurge`
are ordinary entries in the command table (`h/inter.h`) differing only in the
level column. So the builder UI is the same command menu with more verbs when
you are `I4`.

Carry across on purpose what git gave builders for free: **history and
review**. Versions per document, or edits as commits a senior builder merges.

---

## 6. Web interface (htmx)

A MUD is already a server-rendered, push-based text UI — telnet is a stream of
server-generated fragments. That is htmx's model exactly; nothing has to be
re-thought as an API for a JS app.

- Session view → one SSE/websocket per player delivering fragments.
- `act()` room events → out-of-band swaps: a line in the log *and* an update
  to the "things here" panel, rendered server-side per viewer through the same
  perception filter. Invisible players are simply absent from the fragment.
- Exits → links; `scan` → a button; inventory, equipment, group, who → panels
  that re-render when their edges change.
- **Keep the command line.** A text input posting to the same parser the
  telnet path uses. Never two command implementations.
- **Right-click menu** = "what can I do to this, given who I am" — a server
  `hx-get` computed from (what it is: `obj_fields` type) × (where it is
  relative to me: the edge) × (what I can do: skills, class, rank). Client
  knows no rules. The menu *is* the tutorial for new players (`wield` vs
  `wear`, `recite` vs `quaff`). Builders get a few more verbs in the command
  section; nothing else changes.
- Server-side rendering keeps `CAN_SEE` in one place; a JSON API would leak
  invisible players and re-implement the filter in JavaScript.

Prior art in the codebase: `mxp.c` / `live/lib/mxp_elements` — MXP, the
early-2000s telnet markup for clickable exits and item menus. Same idea, worse
transport, no browser. This is what it was reaching for.

### Room images

The descriptions are finished prompts (see the Demi-Lich in `MOB/`). Since the
room collection in Mongo has the full text, an image agent can iterate over it
directly — the C server never needs to know.

- Store a **hash of the description** with the image reference; skip unchanged
  rooms on re-run.
- Store a **reference, not bytes** (GridFS or object storage + path). Serve as
  static files.
- Store the **prompt, style, model and seed** on the document; `rejected: true`
  plus a note feeds the next run.
- **Style per zone**, three-level inheritance: world default → zone → room
  override. Home for it is the `.zon` metadata (or a sidecar, to avoid touching
  the bison grammar in `Zone/`). Contrast between zones does narrative work.
- Extra descriptions (`extra { keywords {...} }`) are the detail shots — inset
  images with the keyword list naming the hotspot.
- Dynamic contents (who and what is here) stay in the panels, not the image.
- Honour the builders' own rule (see the Asgard room text): no copyrighted
  material. Steer the style prompt away from "in the style of"; review the
  first batch.

---

## 7. Porting the dynamics

The mass of the C: `fight.c`, `offensive.c`, `mobrank.c` (combat);
`spells1/2/3.c`, `magic*.c`, `spell_parser.c` (magic); `ticks.c`, `limits.c`,
`weather.c`, `events.c` (the tick); `mobact.c`, `spec_*.c` (behaviour hooks);
`zone.c` (resets); `interpreter.c`, `handler.c` (parser and `act()`).

Some "data" is code in disguise and should be read first: the `.zon` reset
commands (a tiny imperative language) and `GEN_proc_table.c` / `Proc.c`
(special procedures bound to vnums).

**Four decisions gate the dynamics**; everything else is arithmetic over
fields whose home is settled:

1. Prototype vs instance (§1).
2. The triple table's shape, its two indexes, and which edges persist.
3. Affects and timers as a **time-indexed** table ("find things whose expiry ≤
   now"), not lists hanging off each character as `affected_type` does. The
   tick becomes one query; respawn timers live here too.
4. The unit of work. The C's answer is "single-threaded, so everything";
   pick "one command = one transaction; the tick is a series of small ones".

### Strangler path

The dynamics need not be finished before the store becomes the home of the
data. `pr3` reads `world.out`; an **exporter** (Mongo → brace-syntax text, or
straight to binary via the same field tables) keeps the C server running
unchanged while the source of truth moves. `pr-world` disappears as a repo of
hand-edited files; the web interface and Python dynamics grow beside the C
engine against the same store; the C is retired subsystem by subsystem — or
never, if combat is fine where it is.

This also retires the `pr3-dev` "edit sources in a container" workflow: the
maintainer's loop becomes edit in the store → export → restart.

### The packed binaries are derived

Every `.out` is produced by `tran` from text; a port never needs to read them.
The only binary-only data is players and accounts (`stash/`, `account/`,
written by `player.save.c`, described by `char_data_fields`) — one careful
decoder, run once as a migration for 554 characters and 136 accounts, then
never again. Note the password lives account-side.

---

## Pointers into the C

| concept | where |
|---|---|
| schema tables (17) | `PRLib/fields.c`; engine in `PRLib/Schema.c` |
| half-done schema migration | `sector.c:37` (hand `switch` with `InitWithSchema` grafted in) |
| `CAN_SEE` | `h/utils.h` ~300–400 |
| `scan` | `cmds1.c:1032` |
| `pwhere` / `where` | `cmds3.c:1682`; levels in `h/inter.h` |
| command table with level column | `h/inter.h` |
| zone reset tick and modes | `zone.c:930`, `:1428` |
| room autosave and zone save | `room.save.c`, `world.save.c` |
| MXP | `mxp.c`, `live/lib/mxp_elements` |
| builder docs | `pr-world/DOCS/` |
