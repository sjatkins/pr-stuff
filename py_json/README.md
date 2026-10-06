# py-json: Perilous Realms world sources to JSONL

Converts the text world sources in `../world` into one JSONL file per type,
one JSON object per record. No dependencies beyond the standard library.

```
uv sync
uv run world2jsonl                 # everything -> ./out/*.jsonl
uv run world2jsonl -t rooms,mobs   # a subset
uv run world2jsonl --strict        # any warning is fatal, like tran
uv run rooms -o rooms.jsonl        # the original rooms-only command
```

| type      | source                          | output            |
|-----------|---------------------------------|-------------------|
| sectors   | `SECT/sectors.current`          | `sectors.jsonl`   |
| rooms     | `ROOM/ALLROOMS` (+ area.list)   | `rooms.jsonl`     |
| mobs      | `MOB/ALLMOB`                    | `mobs.jsonl`      |
| objects   | `OBJ/ALLOBJS`                   | `objects.jsonl`   |
| shops     | `SHOP/shops.current`            | `shops.jsonl`     |
| races     | `RACE/races.current`            | `races.jsonl`     |
| clans     | `CLAN/clans.current`            | `clans.jsonl`     |
| item_sets | `ITEM_SETS/item_sets.current`   | `item_sets.jsonl` |
| effects   | `SKILL/effects.tran`            | `effects.jsonl`   |
| skills    | `SKILL/skills.tran`             | `skills.jsonl`    |
| zones     | `ZONE/zone.list` -> `*.zon`     | `zones.jsonl`     |
| classes   | `CLASSES/classes`               | `classes.jsonl`   |
| players   | backup tar `stash/<a-z>/<name>` | `players.jsonl`   |
| accounts  | backup tar `account/<a-z>/<name>` | `accounts.jsonl` |
| spells    | `src/h/spell_func.h` + `spells.h` + `constants.c` + `fight.c` | `spells.jsonl` |
| commands  | `src/h/inter.h`                 | `commands.jsonl`  |
| applies   | `names.json` apply_fields       | `applies.jsonl`   |
| name_tables | `names.json` tables           | `name_tables.jsonl` |
| messages  | `MISC/messages`                 | `messages.jsonl`  |
| socials   | `MISC/actions`                  | `socials.jsonl`   |
| help      | `HELP/help_table`               | `help.jsonl`      |
| lockers   | lib `LockerSave/locker.<room>.room` | `lockers.jsonl` |
| worldsave | lib `WorldSave/zone.<n>`        | `worldsave.jsonl` |
| limited   | lib `WorldSave/Misc/limited.obj` | `limited.jsonl`  |
| boards    | lib `<vnum>.board`              | `boards.jsonl`    |

The C sources default to `<world>/../src` (`-s`), the game's lib directory to
`<world>/../live/lib` (`-l`). The lib-derived files describe whatever lib
is there: for the checked-in `out/` that is this machine's local game, not
production.

## Canonical shape

Unless `--raw` is given, every record is passed through its pydantic model
in `../py-pr` (`prworld/canon.py` imports `../py-pr/src` and, when the
running interpreter has no pydantic, that package's `.venv`) and written as
`model_dump_json(by_alias=True, exclude_unset=True)`. So the JSONL *is*
the model's own JSON: every record carries its `id`, grouped fields
(`defense`, `hit`, typed `values`) are in their model form, and flags are
in bit order. Loading a line with the model and dumping it again is the
identity, and `py-pr/tools/roundtrip.py` checks exactly that for every
line of every file. `--raw` writes the extractor's own dict shape, which
the models also accept.

Players and accounts are read from a player backup, either a `.tar` or an
extracted directory, given with `-p`; the default is the newest
`players_*.tar` beside the `world` directory. Password hashes are dropped
unless `--include-secrets` is passed. Email addresses, real names and last
login sites are kept, so treat `accounts.jsonl` as private.

## How it works

`src/prworld/tranparse.py` reimplements the text side of `src/tran/tran.c`:
`#include` / `#define` / `#offset`, `@macro` definitions and expansion, and
the brace-block tokenizer. Field meaning comes from `src/prworld/schemas.py`,
a transcription of the schema tables in `src/PRLib/fields.c` and
`src/PRLib/Effect.c`. Name tables (flags, races, spells, ...) are extracted
from the C sources into `src/prworld/names.json` by `tools/gen_names.py`.

Zones have their own grammar (`src/Zone/parser.y`) in `src/prworld/zones.py`;
the class table (`skills.c:boot_class`) is in `src/prworld/classes.py`.

Player and account files are the hand-coded binary formats of
`src/player.save.c`, `src/account.c` and `src/objdb.c` (carried objects).
`src/prworld/players.py` transcribes those readers. Field sizes and
signedness come from `src/prworld/player_layout.json`, which
`tools/layout.c` generates by compiling against the server headers:

```
cd ../src && gcc -std=gnu11 -fsigned-char -Ih -DNO_RUBY -D_GNU_SOURCE -w \
    -o /tmp/layout ../py_json/tools/layout.c && /tmp/layout > ../py_json/src/prworld/player_layout.json
```

Re-run it if `structs.h` changes. The version upgrades in `finish_char` are
applied so every player record has current (version 6) semantics.

## Output conventions

- Every top-level record has `vnum` and `source` (`file:line`). Rooms also
  carry `area` and `local_number`. Zones and classes use `name` / `index`.
- Every schema key is present on every record of a type; absent values are
  `null`, or `[]` for list-valued fields. Nested blocks only carry what was
  written.
- Enum and flag values are emitted with the server's canonical spelling
  (case-insensitive exact or prefix match, as tran does). Unknown values are
  kept as written and reported.
- `apply`, `item_ability` and `set_ability` blocks are dicts keyed by apply
  name. Numeric applies repeated in one block are summed (the server stacks
  them); name-valued applies such as `spell_affect` are lists.
- A value in parentheses, `field ( 10 )`, is accepted as if braced. tran
  loses these, so the JSON is more complete than the compiled binary there.
- `extra` / `extras` blocks become `extra_descriptions`, a list of
  `{keywords, description}` pairs.
- An object's `type` is `{"<item type>": {...}}`; marker types such as
  `other` map to `null`.
- Room exits are a list; each `to` line starts a new exit and following
  lines attach to it. Exit and teleport targets are resolved to absolute
  vnums with the original text kept in `to_raw` / `target_raw`.
- Player records: flag words become name lists, skills carry `kind`
  (skill / spell / proficiency) and a resolved `name`, affects carry both the
  numeric `type` and `type_name`, and equipment is a dict keyed by wear slot.
  Saved objects are stored in full (players can hold modified items) with
  `vnum` for joining against `objects.jsonl`; an empty saved string means
  "use the prototype's text" and is emitted as `null`.
- Scalar fields written twice keep the last value and produce a warning,
  which is what the server ends up with.

## Checking against the compiled binaries

`tools/check_bin.py` walks the `.out` files tran produced using the same
schema tables and compares vnum sets with the JSONL:

```
uv run python tools/check_bin.py out
```

A wrong field type in the schema shows up as a stream desync, so a clean
walk validates the transcription as well as the record set.
