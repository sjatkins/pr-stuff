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

`src/names.py` holds the game's fixed vocabularies, generated from the C name
tables by `tools/gen_enums.py`. Code tables (sex, position, rarity, material,
weapon class, damage type, drink, item kind, race, class ...) are `StrEnum`
classes whose members carry the numeric `code`. Bit tables (room, exit,
object and wear flags, mob actions, affect bits, immunities, intrinsics,
forms, player, account, config and log flags ...) are `enum.Flag` classes:
a field holding a set of them is one integer, so `RoomFlag.dark in
room.flags`, `mob.immune & (Immunity.fire | Immunity.cold)` and
`flags & wanted == wanted` are single AND operations rather than list scans.
Each flag member carries the game's `label` string and its bit `code`; the
list of labels the JSONL carries is the boundary form, converted by
`from_names` / `.names`, which pydantic applies on validation and
serialisation. Fields with a fixed vocabulary use these classes, without
exceptions: bits the C table leaves unnamed are generated as `bitN` members
(the extractor spells them the same way), and an enum word the source
misspells is dropped by the extractor with a warning, since `tran` writes the
failed lookup into the binary and the game never sees a value either.
Zero/one fields that the code treats as flags are `bool`.

Lists whose positions carry meaning are named models, not `list[int]`:
`Dice(number, sides, bonus)`; `BodyPartDefense(armor, stopping)` grouped per
hit location in `Defense`, on both `Mob` and `Player`; `OpenHours`;
`MinAvgMax`; `SavingThrows` in `SAVING_*` order; `Conditions(drunk, hunger,
thirst)`; `Resistances` in `*_DAMAGE` order; `Stats` for the class stat
tables. A player's `hit` is `HitPoints(current, rolled)`, since the C's
`max_hit` is the sum of level-up rolls rather than the maximum, and `mana`,
`power` and `move` are `Pool(current, bonus)`, since their stored `max_*` is
the apply bonus the limit functions add to a level-and-class formula.

An object's kind is a class hierarchy: `ItemType` is the base, with one
subclass per kind or per group of kinds sharing a layout (`WeaponType`,
`ArmorType`, `SpellItemType` for scroll and potion, `MarkerType` for the
kinds with no data, ...). `ObjectPrototype.type` is an `ItemType`; validating
the extractor's `{"weapon": {...}}` block against it yields the subclass,
picked by `kind`. A saved item's five `value[]` slots become the same
subclass, read the way the game reads them (spell items keep spell numbers,
so `SavedSpellItemType` and friends subclass the prototype types), or
`UntypedValues` for kinds that give the slots no meaning. Equipment slots are
always lists. These are a typed view of the JSONL: `Positional` maps a list
onto its fields by slot, and `mode="before"` validators on `Mob`, `Player`
and `SavedObject` regroup the flat keys, so the models do not serialise back
to the extractor's shape.

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
