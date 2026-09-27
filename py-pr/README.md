# py-pr: pydantic models for the Perilous Realms game data

`src/classes.py` defines one pydantic model per game data type.

The first group mirrors the JSONL that `../py_json` extracts, record for
record: `Room`, `Mob`, `ObjectPrototype`, `Shop`, `Race`, `Sector`, `Clan`,
`ItemSet`, `Effect`, `Skill`, `Zone`, `CharacterClass`, `Player`, `Account`,
plus the shared pieces they embed (`Exit`, `SavedObject`, `Affect`,
`ZoneLoad`, ...). `JSONL_MODELS` maps each output file name to its model.

The second group covers structures the game persists but nothing extracts
yet: `Locker`, `Storage`, `WorldSaveRoom`, `LimitedItemCount`, `Board`,
`Auction`, `HelpEntry`, `Social`, `DamageMessage`, `StoryTeller`, and the
reference tables `NameTable`, `ApplyDefinition`, `SpellDefinition`,
`CommandDefinition`.

Numbers that are really codes are resolved to names by the extractor and
typed accordingly: equipment slots (`WearPosition`), pulse affect kinds
(`PulseType`), clan rank (`ClanRank`), player config and log bits
(`ConfigFlag`, `LogFlag`), apply locations (`ApplyLocation`), and every
"damage type" or affect type, which in this game is one shared attack-type
numbering (spells, weapon TYPE_*, room hazards, remort flags, skills,
markers) and is carried as an `AttackType` `{number, kind, name}`.

`src/names.py` holds `StrEnum` classes for the game's fixed vocabularies
(sex, position, rarity, material, weapon class, damage type, drink, item
kind, race, class, and every flag set), generated from the C name tables by
`tools/gen_enums.py`; a member's position is the numeric code or bit index.
Fields with a fixed vocabulary use them. Two deliberate exceptions: mob
`sex` also accepts a plain string because the sources contain values the
server silently accepts, and player affect bit lists accept `bitN` for the
three bits whose names are blank in `constants.c`. Zero/one fields that the
code treats as flags are `bool`.

Conventions: fields the source may leave unset are `Optional` with default
`None`; list-valued fields default to `[]`; nested blocks carry only what
was written; enum and flag values are the server's canonical names; unknown
keys are rejected (`extra="forbid"`) so drift between the extractor and the
models is caught. `class` is exposed as `class_` with an alias.

```
uv sync
uv run python tools/validate_jsonl.py      # every line of ../py_json/out/*.jsonl
```

All fourteen JSONL files validate cleanly.
