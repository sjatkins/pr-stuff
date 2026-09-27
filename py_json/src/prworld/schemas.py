"""Schema tables for the tran brace-block formats.

Transcribed from ``src/PRLib/fields.c`` and ``src/PRLib/Effect.c``. Each
field carries the tran field type code (STR, S32, BIT, SUB ...), the source
token(s) that select it, the name table used to validate enum / bitvector
values, and how repeated occurrences are treated in the JSON output.

Field type meanings (see ``src/h/Schema.h`` and ``tran.c:parse_block``):

    STR   free text, surrounding quote stripped
    U8 S8 S16 U16 S32 U32   integers (atoi semantics)
    IDX   integer index into a table, emitted as the table entry's name
    ATK   attack-type number, emitted as {number, kind, name} (see attack.py)
    DBL   double
    E8 E32   one name from a table (canonical spelling emitted)
    ESTR  one name from a table, emitted as written
    BIT IDV L16   comma separated names from a table -> list
    SET ASTR   comma separated strings (optionally validated) -> list
    HASH  ``key => value`` pairs -> dict
    A32 ADBL   sequence of numbers -> list
    T32 DIC V32 VEC   2 / 3 / 3 ints, 3 doubles -> list
    RVR TEL EXI ROM   room-specific compound values
    SUB   nested block with its own schema -> dict
    ASUB  array of anonymous nested blocks -> list of dicts
    HOL   marker with no value -> null
    PROC  procedure name -> string
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

NAMES = json.loads((Path(__file__).with_name("names.json")).read_text(encoding="utf-8"))
TABLES: dict[str, list[str]] = NAMES["tables"]
ITEM_TYPE_IDS: dict[str, int] = NAMES["item_type_ids"]


@dataclass(frozen=True)
class F:
    id: int
    type: str
    name: str
    list: str | None = None        # key into TABLES (or a dynamic table)
    sub: tuple["F", ...] | None = None
    aliases: tuple[str, ...] = ()
    out: str | None = None         # JSON key, defaults to name
    policy: str = "one"            # one | list | pairs | applies | exits

    @property
    def key(self) -> str:
        return self.out or self.name

    def matches(self, token: str) -> bool:
        t = token.lower()
        return t == self.name.lower() or any(t == a.lower() for a in self.aliases)


Schema = tuple[F, ...]


def find_field(schema: Schema, token: str) -> F | None:
    for f in schema:
        if f.matches(token):
            return f
    return None


# --------------------------------------------------------------------------
# shared sub-schemas
# --------------------------------------------------------------------------

EXTRA_DESC: Schema = (
    F(1, "STR", "keywords"),
    F(2, "STR", "desc", out="description"),
)

EXIT_FIELDS: Schema = (
    F(1, "EXI", "to"),
    F(2, "STR", "description", aliases=("desc",)),
    F(3, "STR", "keywords"),
    F(4, "BIT", "info", "exit_bits"),
    F(5, "U32", "key"),
    F(6, "BIT", "start", "exit_bits"),
    F(7, "U16", "reset"),
)

ROOM_FIELDS: Schema = (
    F(4, "STR", "name"),
    F(5, "STR", "description", aliases=("desc",)),
    F(13, "E32", "sector", "sector_types"),
    F(9, "BIT", "flags", "room_bits"),
    F(2, "RVR", "river"),
    F(3, "TEL", "teleport", aliases=("tele",)),
    F(12, "S8", "max_people"),
    F(13, "VEC", "size"),
    F(14, "ASTR", "map"),
    F(6, "SUB", "extra", sub=EXTRA_DESC, out="extra_descriptions", policy="pairs"),
    F(7, "SUB", "exits", sub=EXIT_FIELDS, policy="exits"),
)

SHOP_MESSAGES: Schema = (
    F(1, "STR", "dont_have"),
    F(2, "STR", "no_item"),
    F(3, "STR", "dont_buy"),
    F(4, "STR", "shop_cant_afford"),
    F(5, "STR", "player_cant_afford"),
    F(6, "STR", "buy"),
    F(7, "STR", "sell"),
)

SHOP_FIELDS: Schema = (
    F(0, "S32", "shopkeeper", aliases=("keeper",)),
    F(1, "S32", "location"),
    F(2, "L16", "buy_type", "item_types"),
    F(3, "A32", "sell"),
    F(12, "A32", "buy"),
    F(6, "DBL", "sell_mult"),
    F(7, "DBL", "buy_mult"),
    F(8, "T32", "hours"),
    F(9, "SUB", "messages", sub=SHOP_MESSAGES),
    F(10, "U32", "temper_player"),
    F(11, "U32", "temper_attacked"),
)

ADJUST_FIELDS: Schema = (
    F(0, "S8", "strength", aliases=("str",)),
    F(1, "S8", "intelligence", aliases=("int",)),
    F(2, "S8", "wisdom", aliases=("wis",)),
    F(3, "S8", "dexterity", aliases=("dex",)),
    F(4, "S8", "constitution", aliases=("con",)),
    F(5, "S8", "charisma", aliases=("chr",)),
    F(6, "S8", "luck", aliases=("lck",)),
)

RACE_FIELDS: Schema = (
    F(1, "STR", "name"),
    F(2, "STR", "abbrev"),
    F(3, "V32", "height"),
    F(4, "V32", "weight"),
    F(5, "SUB", "adjust", sub=ADJUST_FIELDS),
    F(6, "BIT", "intrinsic", "intrinsics"),
    F(7, "BIT", "immune", "immunity_names"),
    F(8, "BIT", "resistant", "immunity_names"),
    F(9, "BIT", "susceptible", "immunity_names"),
    F(10, "S8", "track"),
    F(11, "BIT", "form", "forms"),
    F(12, "S16", "move"),
    F(13, "S16", "power_gain"),
    F(14, "S16", "refresh"),
    F(15, "S32", "resist_fire"),
    F(16, "S32", "resist_cold"),
    F(17, "S32", "resist_electricity"),
    F(18, "S32", "resist_water"),
    F(19, "S32", "resist_acid"),
    F(20, "S32", "resist_poison"),
    F(21, "S32", "resist_force"),
    F(22, "S32", "resist_magic"),
    F(23, "S32", "resist_light"),
    F(24, "S32", "resist_darkness"),
    F(25, "S32", "resist_all"),
)

MOVE_COST_FIELDS: Schema = (
    F(1, "S16", "moves"),
    F(2, "S16", "delay"),
    F(3, "U8", "tracks"),
    F(4, "U8", "damage"),
    F(5, "ATK", "damage_type"),   # U16 attack type (messages file number)
)

SECTOR_MAP_FIELDS: Schema = tuple(
    F(i, "STR", n) for i, n in enumerate((
        "room", "walls", "exits", "doors", "odoors",
        "room_color", "detail_color", "dark_color", "wall_color", "exit_color",
        "door_color", "odoor_color", "fill_color", "pc_color", "mob_color",
    ))
)

SECTOR_FIELDS: Schema = (
    F(1, "STR", "name"),
    F(2, "BIT", "flags", "sector_bits"),
    F(3, "SUB", "boat", sub=MOVE_COST_FIELDS),
    F(4, "SUB", "fly", sub=MOVE_COST_FIELDS),
    F(5, "SUB", "normal", sub=MOVE_COST_FIELDS),
    F(6, "SUB", "map", sub=SECTOR_MAP_FIELDS),
    F(6, "VEC", "default_sizes"),
)

CLAN_FIELDS: Schema = (
    F(1, "STR", "name"),
    F(2, "BIT", "flags", "clan_flags"),
    F(3, "DBL", "xp_mult"),
    F(4, "U16", "min_join_level"),
    F(5, "U16", "max_join_level"),
    F(6, "STR", "clanmaster"),
    F(7, "STR", "deputy"),
)

MOB_FIELDS: Schema = (
    F(0, "STR", "name"),
    F(1, "STR", "namelist"),
    F(2, "STR", "shortdesc", aliases=("short",)),
    F(3, "STR", "longdesc", aliases=("long",)),
    F(4, "STR", "description"),
    F(5, "E32", "race", "race_list"),
    F(46, "E8", "class", "class_list"),
    F(47, "E8", "sex", "sexes"),
    F(9, "S32", "level"),
    F(10, "S32", "alignment"),
    F(11, "U32", "gold"),
    F(39, "S32", "experience"),
    F(37, "DIC", "hp"),
    F(6, "U32", "mana"),
    F(38, "U32", "move"),
    F(45, "U32", "power"),
    F(7, "S32", "height"),
    F(8, "S32", "weight"),
    F(12, "S32", "hit_bonus"),
    F(13, "S32", "dam_bonus"),
    F(14, "DBL", "attacks_per_round"),
    F(40, "DIC", "damage"),
    F(16, "U8", "strength"),
    F(17, "U8", "dexterity"),
    F(18, "U8", "constitution"),
    F(19, "U8", "intelligence"),
    F(20, "U8", "wisdom"),
    F(21, "U8", "charisma"),
    F(22, "U8", "luck"),
    F(23, "T32", "head"),
    F(24, "T32", "body"),
    F(25, "T32", "arms"),
    F(27, "T32", "legs"),
    F(28, "T32", "feet"),
    F(29, "BIT", "immune", "immunity_names"),
    F(30, "BIT", "resistant", "immunity_names"),
    F(31, "BIT", "susceptible", "immunity_names"),
    F(32, "S32", "rod"),
    F(33, "S32", "spell"),
    F(34, "S32", "breath"),
    F(35, "S32", "petrification"),
    F(36, "S32", "paralyzation"),
    F(41, "IDV", "affected", "affected_bits"),
    F(42, "BIT", "act", "action_bits"),
    F(43, "U8", "caster"),
    F(15, "L16", "skills", "skills"),
    F(44, "L16", "spells", "spells"),
    F(48, "U32", "group_with"),
    F(49, "S32", "world_limit"),
    F(50, "STR", "story_teller"),
    F(51, "S32", "resist_fire"),
    F(52, "S32", "resist_cold"),
    F(53, "S32", "resist_electricity"),
    F(54, "S32", "resist_water"),
    F(55, "S32", "resist_acid"),
    F(56, "S32", "resist_poison"),
    F(57, "S32", "resist_force"),
    F(58, "S32", "resist_magic"),
    F(59, "S32", "resist_light"),
    F(60, "S32", "resist_darkness"),
    F(60, "S32", "resist_energy"),
    F(61, "S32", "resist_all"),
    F(62, "DBL", "armor_penetration"),
    F(63, "S32", "fire_penetration"),
    F(64, "S32", "cold_penetration"),
    F(65, "S32", "electricity_penetration"),
    F(66, "S32", "water_penetration"),
    F(67, "S32", "acid_penetration"),
    F(68, "S32", "poison_penetration"),
    F(69, "S32", "force_penetration"),
    F(70, "S32", "magic_penetration"),
    F(71, "S32", "light_penetration"),
    F(72, "S32", "dark_penetration"),
    F(73, "S32", "spell_power"),
    F(74, "DBL", "life_steal"),
    F(75, "S32", "penetrate_all"),
    F(76, "DBL", "spell_vamp"),
    F(77, "S32", "hp_regen"),
    F(78, "S32", "mana_regen"),
    F(79, "S32", "power_regen"),
    F(80, "S32", "moves_regen"),
    F(81, "S32", "hit_shield"),
    F(82, "S32", "remort_count"),
    F(83, "S32", "rage"),
    F(84, "S32", "energy"),
)

# apply_fields comes from constants.c; the numeric ids are APPLY_* constants
# which the JSON never needs, so the row index stands in for them.
APPLY_FIELDS: Schema = tuple(
    F(i, row["type"], row["name"], row["list"]) for i, row in enumerate(NAMES["apply_fields"])
)

_LIGHT: Schema = (F(3, "S32", "duration"),)
_SCROLL: Schema = (
    F(1, "S32", "level"),
    F(2, "E32", "spell1", "spells"),
    F(3, "E32", "spell2", "spells"),
    F(4, "E32", "spell3", "spells"),
)
_WAND: Schema = (
    F(1, "S32", "level"),
    F(2, "S32", "max_charges"),
    F(3, "S32", "charges"),
    F(4, "E32", "spell", "spells"),
)
_TREASURE: Schema = (F(1, "S32", "value"),)
_CONTAINER: Schema = (
    F(1, "S32", "max_hold"),
    F(2, "BIT", "flags", "container_bits"),
    F(3, "S32", "key"),
    F(4, "S32", "timer"),
)
_DRINKCON: Schema = (
    F(1, "S32", "max_units"),
    F(2, "S32", "amount"),
    F(3, "E32", "type", "drinks"),
    F(4, "S32", "poisoned"),
)
_ARMOR: Schema = (
    F(1, "S32", "effective_ac"),
    F(2, "S32", "force"),
    F(3, "S32", "stopping"),
    F(4, "S32", "absorb"),
    F(5, "S32", "timer"),
)
_WEAPON: Schema = (
    F(1, "E32", "wtype", "weapon_types"),
    F(2, "S32", "no_dice"),
    F(3, "S32", "size_dice"),
    F(4, "E32", "type", "damage_types"),
    F(5, "S32", "speed"),
)
_DIMENSION: Schema = (F(1, "S32", "length"), F(2, "S32", "width"), F(3, "S32", "height"))
_TOUCH: Schema = (
    F(1, "S32", "transport_room"),
    F(2, "STR", "msg_to_room"),
    F(3, "STR", "msg_to_char"),
    F(4, "STR", "msg_to_dest"),
)
_FOOD: Schema = (F(1, "S32", "fullness"), F(4, "S32", "poisoned"))
_KEY: Schema = (F(1, "S32", "uses"),)
_AUDIO: Schema = (F(1, "S32", "frequency"),)
_TRAP: Schema = (
    F(1, "BIT", "effect_type", "trap_eff_flags"),
    F(2, "ATK", "damage_type"),   # S32 attack type: spell, weapon TYPE_*, or negative special
    F(3, "S32", "level"),
    F(4, "S32", "charges"),
)
_COMPONENT: Schema = (F(1, "S32", "uses"),)
_SOCKET_ITEM: Schema = (
    F(1, "S32", "combine"),
    F(2, "S32", "combine_to"),
    F(3, "S32", "removable"),
    F(4, "S32", "unique"),
)
_SPELLGEM: Schema = (
    F(1, "DBL", "effect_multiplier"),
    F(2, "DBL", "power_mana_multiplier"),
    F(3, "DBL", "casting_time"),
    F(4, "DBL", "failure_modifier"),
)
_BOARD: Schema = (F(1, "BIT", "flags", "board_bits"),)

_I = ITEM_TYPE_IDS
ITEM_FIELDS: Schema = (
    F(_I["ITEM_LIGHT"], "SUB", "light", sub=_LIGHT),
    F(_I["ITEM_SCROLL"], "SUB", "scroll", sub=_SCROLL),
    F(_I["ITEM_WAND"], "SUB", "wand", sub=_WAND),
    F(_I["ITEM_STAFF"], "SUB", "staff", sub=_WAND),
    F(_I["ITEM_TREASURE"], "SUB", "treasure", sub=_TREASURE),
    F(_I["ITEM_POTION"], "SUB", "potion", sub=_SCROLL),
    F(_I["ITEM_CONTAINER"], "SUB", "container", sub=_CONTAINER),
    F(_I["ITEM_SPELL_POUCH"], "SUB", "pouch", sub=_CONTAINER),
    F(_I["ITEM_DRINKCON"], "SUB", "drink_container", sub=_DRINKCON),
    F(_I["ITEM_MONEY"], "SUB", "money", sub=_TREASURE),
    F(_I["ITEM_ARMOR"], "SUB", "armor", sub=_ARMOR),
    F(_I["ITEM_WEAPON"], "SUB", "weapon", sub=_WEAPON),
    F(_I["ITEM_FOOD"], "SUB", "food", sub=_FOOD),
    F(_I["ITEM_AUDIO"], "SUB", "audio", sub=_AUDIO),
    F(_I["ITEM_OTHER"], "HOL", "other"),
    F(_I["ITEM_BOOK"], "HOL", "book"),
    F(_I["ITEM_BOARD"], "SUB", "board", sub=_BOARD),
    F(_I["ITEM_FIREWEAPON"], "HOL", "fireweapon"),
    F(_I["ITEM_MISSILE"], "HOL", "missile"),
    F(_I["ITEM_NOTE"], "HOL", "note"),
    F(_I["ITEM_PEN"], "HOL", "pen"),
    F(_I["ITEM_WORN"], "HOL", "worn"),
    F(_I["ITEM_BOAT"], "HOL", "boat"),
    F(_I["ITEM_TRASH"], "HOL", "trash"),
    F(_I["ITEM_KEY"], "SUB", "key", sub=_KEY),
    F(_I["ITEM_TRAP"], "SUB", "trap", sub=_TRAP),
    F(_I["ITEM_COMPONENT"], "SUB", "component", sub=_COMPONENT),
    F(_I["ITEM_HIERARCHICAL"], "A32", "hierarchical"),
    F(_I["ITEM_SPELL_GEM"], "SUB", "spellgem", sub=_SPELLGEM),
    F(_I["ITEM_GEAR_SET"], "A32", "item_set"),
    F(_I["ITEM_SOCKET"], "SUB", "socket", sub=_SOCKET_ITEM),
)

OBJ_FIELDS: Schema = (
    F(0, "STR", "name"),
    F(1, "STR", "namelist"),
    F(2, "STR", "longdesc", aliases=("long",)),
    F(3, "STR", "action", aliases=("special",)),
    F(45, "SUB", "type", sub=ITEM_FIELDS),
    F(7, "S32", "weight"),
    F(43, "S32", "value"),
    F(44, "S32", "rent"),
    F(56, "S32", "real_cost"),
    F(63, "S32", "qpvalue"),
    F(47, "BIT", "bits", "extra_bits"),
    F(48, "BIT", "wear", "wear_bits"),
    F(52, "E32", "material", "material_types"),
    F(61, "E32", "rarity", "rarity_types"),
    F(81, "S32", "tier"),
    F(50, "S32", "min_level"),
    F(51, "S32", "max_exist"),
    F(55, "S32", "max_player"),
    F(53, "S32", "mass"),
    F(54, "S32", "volume"),
    F(57, "SUB", "dimensions", sub=_DIMENSION),
    F(49, "SUB", "apply", sub=APPLY_FIELDS, policy="applies"),
    F(82, "S32", "sockets"),
    F(77, "S32", "item_set"),
    F(62, "A32", "piece_of_set"),
    F(65, "S32", "use_cooldown"),
    F(72, "S32", "ws_cooldown"),
    F(74, "SUB", "item_ability", sub=APPLY_FIELDS, policy="applies"),
    F(75, "S32", "item_ability_duration"),
    F(76, "STR", "item_ability_msg"),
    F(78, "STR", "item_ability_desc"),
    F(58, "SUB", "touch", sub=_TOUCH),
    F(59, "STR", "owner"),
    F(46, "SUB", "extras", sub=EXTRA_DESC, out="extra_descriptions", policy="pairs"),
)

SET_BONUS_FIELDS: Schema = (
    F(1, "SUB", "apply", sub=APPLY_FIELDS, policy="applies"),
    F(2, "SUB", "set_ability", sub=APPLY_FIELDS, policy="applies"),
    F(3, "S32", "set_ability_duration"),
    F(4, "STR", "set_ability_msg"),
)

ITEM_SET_FIELDS: Schema = (
    F(1, "S32", "vnum", out="declared_vnum"),
    F(2, "STR", "name"),
    F(16, "STR", "description"),
    F(13, "E32", "rarity", "rarity_types"),
    F(14, "S32", "use_cooldown"),
    F(15, "S32", "ws_cooldown"),
    F(3, "SUB", "one_set_bonus", sub=SET_BONUS_FIELDS),
    F(4, "SUB", "two_set_bonus", sub=SET_BONUS_FIELDS),
    F(5, "SUB", "three_set_bonus", sub=SET_BONUS_FIELDS),
    F(6, "SUB", "four_set_bonus", sub=SET_BONUS_FIELDS),
    F(7, "SUB", "five_set_bonus", sub=SET_BONUS_FIELDS),
    F(8, "SUB", "six_set_bonus", sub=SET_BONUS_FIELDS),
    F(9, "SUB", "seven_set_bonus", sub=SET_BONUS_FIELDS),
    F(10, "SUB", "eight_set_bonus", sub=SET_BONUS_FIELDS),
    F(11, "SUB", "nine_set_bonus", sub=SET_BONUS_FIELDS),
    F(12, "SUB", "ten_set_bonus", sub=SET_BONUS_FIELDS),
)

MODIFY_FIELDS: Schema = (
    F(0, "DBL", "value"),
    F(1, "DIC", "dice"),
    F(2, "ADBL", "extra_values"),
)

EFFECT_FIELDS: Schema = (
    F(0, "STR", "name"),
    F(1, "STR", "description"),
    F(2, "SET", "tags"),
    F(3, "STR", "location"),
    F(4, "SUB", "modify", sub=MODIFY_FIELDS),
    F(5, "SUB", "pulse_modify", sub=MODIFY_FIELDS),
    F(6, "SUB", "custom_modify", sub=MODIFY_FIELDS),
    F(7, "DBL", "min"),
    F(8, "DBL", "max"),
    F(9, "DBL", "duration"),
    F(10, "DBL", "pulse"),
    F(11, "ESTR", "modifier_join", "effect_join_styles"),
    F(12, "HASH", "messages", "effect_message_keys"),
    F(13, "HASH", "procs", "effect_proc_keys"),
)

SKILL_FIELDS: Schema = (
    F(0, "STR", "name"),
    F(1, "ASUB", "effects", sub=EFFECT_FIELDS),
)

# tran type name -> (schema, source file relative to the world dir)
TRAN_TYPES: dict[str, tuple[Schema, str]] = {
    "rooms": (ROOM_FIELDS, "ROOM/ALLROOMS"),
    "mobs": (MOB_FIELDS, "MOB/ALLMOB"),
    "objects": (OBJ_FIELDS, "OBJ/ALLOBJS"),
    "shops": (SHOP_FIELDS, "SHOP/shops.current"),
    "races": (RACE_FIELDS, "RACE/races.current"),
    "sectors": (SECTOR_FIELDS, "SECT/sectors.current"),
    "clans": (CLAN_FIELDS, "CLAN/clans.current"),
    "item_sets": (ITEM_SET_FIELDS, "ITEM_SETS/item_sets.current"),
    "effects": (EFFECT_FIELDS, "SKILL/effects.tran"),
    "skills": (SKILL_FIELDS, "SKILL/skills.tran"),
}
