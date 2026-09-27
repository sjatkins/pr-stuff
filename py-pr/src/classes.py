"""Pydantic models for the Perilous Realms game data.

The first group mirrors the JSONL produced by ``py_json`` (``world2jsonl``)
record for record: every line of ``out/<type>.jsonl`` validates against the
matching model. Field names and shapes follow the extractor, which in turn
follows the schema tables in ``src/PRLib/fields.c`` and the hand-coded
readers in ``player.save.c`` / ``account.c`` / ``objdb.c``.

The second group covers the game's other persistent structures that have no
extractor yet (lockers, boards, auctions, help, socials, damage messages,
world save, story files) and a few reference tables, modelled from the C
structs in ``src/h/structs.h`` and the loaders that read them.

Conventions:
- A top-level record field that the source may leave unset is ``Optional``
  with default ``None``; list-valued fields default to ``[]``.
- Nested blocks only carry what was written, so their fields are all
  ``Optional``.
- Enum and flag values are the server's canonical name strings.
- ``vnum`` is the object/mob/room number; ``source`` is ``file:line``.
- Fixed-length int lists in the JSONL (dice, hit-location pairs, saving
  throws, the ``value[]`` slots of a saved item ...) become small named
  models here; see ``Positional`` and the ``mode="before"`` validators on
  ``Mob``, ``Player`` and ``SavedObject``. The models are a typed view of the
  extractor's output and do not serialise back to the same shape.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from names import (  # generated vocabularies, see tools/gen_enums.py
    AccountFlag, Direction, AffectBit, ApplyLocation, BoardFlag, ClanFlag, ClanRank, ClassName, ConfigFlag,
    ContainerFlag, DamageType, Drink, ExitFlag, Form, Immunity, Intrinsic, ItemKind,
    LogFlag, Material, MobAction, ObjectFlag, PlayerFlag, Position, PulseType, RaceName, Rarity,
    RoomFlag, SectorFlag, Sex, TrapEffect, WeaponClass, WearFlag, WearPosition,
)


class PRModel(BaseModel):
    """Base: unknown keys are an error so drift between extractor and models shows up."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Positional(PRModel):
    """A small record that the source files and the extractor write as a
    fixed-length list of ints (the tran field types T32, DIC and V32, and the
    fixed C arrays in the player file).

    Subclasses declare their fields in slot order. A list input is mapped onto
    the fields by position; a dict input is taken as-is, so the models
    round-trip through their own JSON too.
    """

    @model_validator(mode="before")
    @classmethod
    def _from_list(cls, data: Any) -> Any:
        if isinstance(data, (list, tuple)):
            names = list(cls.model_fields)
            if len(data) != len(names):
                raise ValueError(f"{cls.__name__} takes {len(names)} values ({', '.join(names)}), got {len(data)}")
            return dict(zip(names, data))
        return data


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------

class ExtraDescription(PRModel):
    """``extra { keywords {} desc {} }`` on rooms and objects."""

    keywords: Optional[str] = None
    description: Optional[str] = None


class Dice(Positional):
    """A dice roll, ``number`` d ``sides`` + ``bonus`` (tran type DIC, ``dice()`` in the C)."""

    number: int
    sides: int
    bonus: int


class BodyPartDefense(Positional):
    """Protection of one hit location: the T32 pair on a mob's ``head`` ..
    ``feet`` lines and the ``armor[]`` / ``stopping[]`` slots of a character.

    ``armor`` is the location's armour class on the game's internal scale,
    -100..100 with 100 meaning unarmoured and lower being better; it lowers
    the attacker's chance to land a blow on that location (fight.c). ``stopping``
    is the stopping power of what is worn there: a blow that does land has
    0..``stopping`` subtracted from its damage.
    """

    armor: int
    stopping: int


class Defense(PRModel):
    """Defence of the five hit locations, LOCATION_FEET .. LOCATION_HEAD in const.h.

    A location the mob file leaves out stays ``None``; the server then uses its
    defaults of 100 armour and 0 stopping.
    """

    head: Optional[BodyPartDefense] = None
    body: Optional[BodyPartDefense] = None
    arms: Optional[BodyPartDefense] = None
    legs: Optional[BodyPartDefense] = None
    feet: Optional[BodyPartDefense] = None


# name -> C array index. Slot 0 is LOCATION_UNKNOWN, never a hit location.
_LOCATION_SLOTS = {"feet": 1, "legs": 2, "arms": 3, "body": 4, "head": 5}


class OpenHours(Positional):
    """When a shop trades: the game hours (0..23) it opens and closes."""

    open: int
    close: int


class MinAvgMax(Positional):
    """A range with its typical value (tran type V32), e.g. a race's height or weight."""

    min: int
    avg: int
    max: int


class SavingThrows(Positional):
    """One value per saving-throw type, in SAVING_* order (spells.h):
    paralyzation, rod, petrification, breath, spell."""

    paralyzation: int
    rod: int
    petrification: int
    breath: int
    spell: int


class Conditions(Positional):
    """``conditions[3]`` of a character: hours of drunkenness, hunger and thirst
    left (DRUNK, HUNGER, THIRST in const.h)."""

    drunk: int
    hunger: int
    thirst: int


class Resistances(Positional):
    """Elemental resistances in *_DAMAGE order (const.h): fire, cold,
    electricity, water, acid, poison, force, magic, light, darkness.

    The class files list the first eight; the loader (skills.c boot_class)
    reads ten and the two missing ones become 0, which is what a short list
    is padded with here.
    """

    fire: int
    cold: int
    electricity: int
    water: int
    acid: int
    poison: int
    force: int
    magic: int
    light: int
    darkness: int

    @model_validator(mode="before")
    @classmethod
    def _from_list(cls, data: Any) -> Any:
        if isinstance(data, (list, tuple)) and 8 <= len(data) <= 10:
            data = list(data) + [0] * (10 - len(data))
            return dict(zip(cls.model_fields, data))
        return Positional._from_list.__func__(cls, data)


class Stats(PRModel):
    """The seven primary attributes. Accepts the class file's short keys
    (str, int, wis, dex, con, chr, lck) as well as the full names."""

    strength: Optional[int] = Field(default=None, validation_alias=AliasChoices("strength", "str"))
    intelligence: Optional[int] = Field(default=None, validation_alias=AliasChoices("intelligence", "int"))
    wisdom: Optional[int] = Field(default=None, validation_alias=AliasChoices("wisdom", "wis"))
    dexterity: Optional[int] = Field(default=None, validation_alias=AliasChoices("dexterity", "dex"))
    constitution: Optional[int] = Field(default=None, validation_alias=AliasChoices("constitution", "con"))
    charisma: Optional[int] = Field(default=None, validation_alias=AliasChoices("charisma", "chr"))
    luck: Optional[int] = Field(default=None, validation_alias=AliasChoices("luck", "lck"))


class ExtraStatPoints(Stats):
    """A class's ``extr`` line: how many points above base a new character may
    put into each stat, and ``max_total`` across all of them (class_entry.extra[8])."""

    max_total: Optional[int] = None


# apply blocks: name -> number, or name -> list of names for enum/bit applies
ApplyValue = Union[int, float, list[str]]
Applies = dict[str, ApplyValue]

class AttackType(PRModel):
    """A number in the game's single attack-type space, resolved to a name.

    Spells (< 240), weapon proficiencies (5000+), skills (10000+), the weapon
    TYPE_* codes 906-918, room hazards 921-930, affect markers 998/999, and
    negative specials (traps: -2 teleport, -3 sleep). This is what damage()
    and the combat messages file are keyed by.
    """

    number: int
    kind: Literal["spell", "weapon", "room", "marker", "remort", "skill", "proficiency", "special", "unknown"]
    name: str


# ---------------------------------------------------------------------------
# Rooms  (world/ROOM, rooms.jsonl)
# ---------------------------------------------------------------------------

class RoomRiver(PRModel):
    """Current in a water room: everyone in it is pushed one room in ``direction`` every ``speed`` pulses (handler.c)."""

    direction: Optional[Direction] = None
    direction_num: Optional[int] = None
    speed: Optional[int] = None


class RoomTeleport(PRModel):
    """Timed teleport out of a room (handler.c char_to_room / utils.c event_teleport).

    ``time`` is the delay after entering, in quarter seconds; ``look`` says
    whether the player sees the destination on arrival; ``target`` equal to
    the room itself means "message only, no move" (the message is the room's
    ``_teleport`` extra description).
    """

    time: Optional[int] = None
    look: Optional[bool] = None
    target: Optional[int] = None
    target_raw: str


class Exit(PRModel):
    """One exit of a room: the direction, the destination room and the door on it, if any."""

    direction: Optional[Direction] = None
    direction_num: Optional[int] = None
    to: Optional[int] = None
    to_raw: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    info: list[ExitFlag] = Field(default_factory=list)
    start: list[ExitFlag] = Field(default_factory=list)   # default door state
    key: Optional[int] = None
    reset: Optional[int] = None


class Room(PRModel):
    """A room prototype from world/ROOM. Static world data; contents and occupants are runtime state."""

    vnum: int
    area: Optional[str] = None
    local_number: int
    source: str
    name: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    flags: list[RoomFlag] = Field(default_factory=list)
    river: Optional[RoomRiver] = None
    teleport: Optional[RoomTeleport] = None
    max_people: Optional[int] = None
    size: Optional[list[float]] = None
    map: Optional[list[str]] = None
    extra_descriptions: list[ExtraDescription] = Field(default_factory=list)
    exits: list[Exit] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mobs  (world/MOB, mobs.jsonl)
# ---------------------------------------------------------------------------

class Mob(PRModel):
    """A mob (NPC) prototype from world/MOB. Copied into a live character each time a zone loads it."""

    vnum: int
    source: str
    name: Optional[str] = None
    namelist: Optional[str] = None
    shortdesc: Optional[str] = None
    longdesc: Optional[str] = None
    description: Optional[str] = None
    race: Optional[RaceName] = None
    class_: Optional[ClassName] = Field(default=None, alias="class")
    sex: Optional[Sex] = None
    level: Optional[int] = None
    alignment: Optional[int] = None
    gold: Optional[int] = None
    experience: Optional[int] = None
    hp: Optional[Dice] = None
    mana: Optional[int] = None
    move: Optional[int] = None
    power: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    hit_bonus: Optional[int] = None
    dam_bonus: Optional[int] = None
    attacks_per_round: Optional[float] = None
    damage: Optional[Dice] = None
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    constitution: Optional[int] = None
    intelligence: Optional[int] = None
    wisdom: Optional[int] = None
    charisma: Optional[int] = None
    luck: Optional[int] = None
    defense: Optional[Defense] = None                  # the file's head/body/arms/legs/feet lines
    immune: list[Immunity] = Field(default_factory=list)
    resistant: list[Immunity] = Field(default_factory=list)
    susceptible: list[Immunity] = Field(default_factory=list)
    rod: Optional[int] = None
    spell: Optional[int] = None
    breath: Optional[int] = None
    petrification: Optional[int] = None
    paralyzation: Optional[int] = None
    affected: list[AffectBit] = Field(default_factory=list)
    act: list[MobAction] = Field(default_factory=list)
    caster: Optional[int] = None
    skills: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    group_with: Optional[int] = None
    world_limit: Optional[int] = None
    story_teller: Optional[str] = None
    resist_fire: Optional[int] = None
    resist_cold: Optional[int] = None
    resist_electricity: Optional[int] = None
    resist_water: Optional[int] = None
    resist_acid: Optional[int] = None
    resist_poison: Optional[int] = None
    resist_force: Optional[int] = None
    resist_magic: Optional[int] = None
    resist_light: Optional[int] = None
    resist_darkness: Optional[int] = None
    resist_energy: Optional[int] = None
    resist_all: Optional[int] = None
    armor_penetration: Optional[float] = None
    fire_penetration: Optional[int] = None
    cold_penetration: Optional[int] = None
    electricity_penetration: Optional[int] = None
    water_penetration: Optional[int] = None
    acid_penetration: Optional[int] = None
    poison_penetration: Optional[int] = None
    force_penetration: Optional[int] = None
    magic_penetration: Optional[int] = None
    light_penetration: Optional[int] = None
    dark_penetration: Optional[int] = None
    spell_power: Optional[int] = None
    life_steal: Optional[float] = None
    penetrate_all: Optional[int] = None
    spell_vamp: Optional[float] = None
    hp_regen: Optional[int] = None
    mana_regen: Optional[int] = None
    power_regen: Optional[int] = None
    moves_regen: Optional[int] = None
    hit_shield: Optional[int] = None
    remort_count: Optional[int] = None
    rage: Optional[int] = None
    energy: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def _gather_defense(cls, data: Any) -> Any:
        """Fold the extractor's top-level ``head`` .. ``feet`` pairs into ``defense``."""
        if isinstance(data, dict) and "defense" not in data and any(k in data for k in _LOCATION_SLOTS):
            data = dict(data)
            parts = {k: data.pop(k) for k in _LOCATION_SLOTS if k in data}
            parts = {k: v for k, v in parts.items() if v is not None}
            data["defense"] = parts or None
        return data


# ---------------------------------------------------------------------------
# Objects  (world/OBJ, objects.jsonl)
# ---------------------------------------------------------------------------

class LightType(PRModel):
    """light: hours of light left (-1 permanent)."""
    duration: Optional[int] = None


class SpellItemType(PRModel):
    """scroll and potion: up to three spells cast at ``level``."""
    level: Optional[int] = None
    spell1: Optional[str] = None
    spell2: Optional[str] = None
    spell3: Optional[str] = None


class ChargedItemType(PRModel):
    """wand and staff: one spell with charges."""
    level: Optional[int] = None
    max_charges: Optional[int] = None
    charges: Optional[int] = None
    spell: Optional[str] = None


class TreasureType(PRModel):
    """treasure and money: worth in coins."""
    value: Optional[int] = None


class ContainerType(PRModel):
    """container and pouch: capacity, closed/locked flags, key vnum, decay timer."""
    max_hold: Optional[int] = None
    flags: list[ContainerFlag] = Field(default_factory=list)
    key: Optional[int] = None
    timer: Optional[int] = None


class DrinkContainerType(PRModel):
    """drink_container: capacity, current amount, liquid, poison."""
    max_units: Optional[int] = None
    amount: Optional[int] = None
    type: Optional[Drink] = None
    poisoned: Optional[int] = None


class ArmorType(PRModel):
    """armor: armour class and the force/stopping/absorb protections."""
    effective_ac: Optional[int] = None
    force: Optional[int] = None
    stopping: Optional[int] = None
    absorb: Optional[int] = None
    timer: Optional[int] = None


class WeaponType(PRModel):
    """weapon: weapon class, damage dice, damage type, speed."""
    wtype: Optional[WeaponClass] = None
    no_dice: Optional[int] = None
    size_dice: Optional[int] = None
    type: Optional[DamageType] = None
    speed: Optional[int] = None


class FoodType(PRModel):
    """food: hours of fullness, poison."""
    fullness: Optional[int] = None
    poisoned: Optional[int] = None


class UsesType(PRModel):
    """key and component: remaining uses."""
    uses: Optional[int] = None


class AudioType(PRModel):
    """audio: sound frequency."""
    frequency: Optional[int] = None


class TrapType(PRModel):
    """trap: effect flags, what it does when sprung, level, charges.

    ``damage_type`` is an attack type: a spell to cast (fireball, frost
    breath ...), a weapon TYPE_* for blunt/pierce/slash, or a negative special
    (-2 teleport, -3 sleep); see TRAP_DAM_* in const.h.
    """
    effect_type: list[TrapEffect] = Field(default_factory=list)
    damage_type: Optional[AttackType] = None
    level: Optional[int] = None
    charges: Optional[int] = None


class BoardType(PRModel):
    """board: who may read, write and remove (board_bits)."""
    flags: list[BoardFlag] = Field(default_factory=list)


class SocketGemType(PRModel):
    """socket: a gem that can be inserted into socketed items."""
    combine: Optional[int] = None
    combine_to: Optional[int] = None
    removable: Optional[bool] = None
    unique: Optional[bool] = None


class SpellGemType(PRModel):
    """spellgem: multipliers applied to spells cast through it."""
    effect_multiplier: Optional[float] = None
    power_mana_multiplier: Optional[float] = None
    casting_time: Optional[float] = None
    failure_modifier: Optional[float] = None


class ItemType(PRModel):
    """The ``type { <kind> { ... } }`` block of an object prototype.

    Exactly one field is set: the object's item type, keyed by its name as in
    ``item_types``. Marker types (other, book, worn, trash, note, pen, boat,
    missile, fireweapon) carry no data and appear as ``null``; hierarchical
    and item_set carry a list of vnums. ``kind`` gives the set key.
    """

    light: Optional[LightType] = None
    scroll: Optional[SpellItemType] = None
    potion: Optional[SpellItemType] = None
    wand: Optional[ChargedItemType] = None
    staff: Optional[ChargedItemType] = None
    treasure: Optional[TreasureType] = None
    money: Optional[TreasureType] = None
    container: Optional[ContainerType] = None
    pouch: Optional[ContainerType] = None
    drink_container: Optional[DrinkContainerType] = None
    armor: Optional[ArmorType] = None
    weapon: Optional[WeaponType] = None
    food: Optional[FoodType] = None
    key: Optional[UsesType] = None
    component: Optional[UsesType] = None
    audio: Optional[AudioType] = None
    trap: Optional[TrapType] = None
    board: Optional[BoardType] = None
    socket: Optional[SocketGemType] = None
    spellgem: Optional[SpellGemType] = None
    hierarchical: Optional[list[int]] = None
    item_set: Optional[list[int]] = None
    other: None = None
    book: None = None
    worn: None = None
    trash: None = None
    note: None = None
    pen: None = None
    boat: None = None
    missile: None = None
    fireweapon: None = None

    @property
    def kind(self) -> Optional[str]:
        """The item type name: the one key that was present in the source."""
        keys = self.model_fields_set
        return next(iter(keys)) if keys else None


class Dimensions(PRModel):
    """Physical size of an object in centimetres, used for container fitting."""

    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class Touch(PRModel):
    """What happens when an object with a touch trigger is touched: transport and messages."""

    transport_room: Optional[int] = None
    msg_to_room: Optional[str] = None
    msg_to_char: Optional[str] = None
    msg_to_dest: Optional[str] = None


class ObjectPrototype(PRModel):
    """An object prototype from world/OBJ. Live items are SavedObject copies of these."""

    vnum: int
    source: str
    name: Optional[str] = None
    namelist: Optional[str] = None
    longdesc: Optional[str] = None
    action: Optional[str] = None
    type: Optional[ItemType] = None
    weight: Optional[int] = None
    value: Optional[int] = None
    rent: Optional[int] = None
    real_cost: Optional[int] = None
    qpvalue: Optional[int] = None
    bits: list[ObjectFlag] = Field(default_factory=list)
    wear: list[WearFlag] = Field(default_factory=list)
    material: Optional[Material] = None
    rarity: Optional[Rarity] = None
    tier: Optional[int] = None
    min_level: Optional[int] = None
    max_exist: Optional[int] = None
    max_player: Optional[int] = None
    mass: Optional[int] = None
    volume: Optional[int] = None
    dimensions: Optional[Dimensions] = None
    apply: Applies = Field(default_factory=dict)
    sockets: Optional[int] = None
    item_set: Optional[int] = None
    piece_of_set: Optional[list[int]] = None
    use_cooldown: Optional[int] = None
    ws_cooldown: Optional[int] = None
    item_ability: Applies = Field(default_factory=dict)
    item_ability_duration: Optional[int] = None
    item_ability_msg: Optional[str] = None
    item_ability_desc: Optional[str] = None
    touch: Optional[Touch] = None
    owner: Optional[str] = None
    extra_descriptions: list[ExtraDescription] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Shops  (world/SHOP, shops.jsonl)
# ---------------------------------------------------------------------------

class ShopMessages(PRModel):
    """The shopkeeper's stock phrases for the buy/sell edge cases."""

    dont_have: Optional[str] = None
    no_item: Optional[str] = None
    dont_buy: Optional[str] = None
    shop_cant_afford: Optional[str] = None
    player_cant_afford: Optional[str] = None
    buy: Optional[str] = None
    sell: Optional[str] = None


class Shop(PRModel):
    """A shop from world/SHOP: which mob sells what, where, and at what multipliers."""

    vnum: int
    source: str
    shopkeeper: Optional[int] = None
    location: Optional[int] = None
    buy_type: list[ItemKind] = Field(default_factory=list)
    sell: Optional[list[int]] = None
    buy: Optional[list[int]] = None
    sell_mult: Optional[float] = None
    buy_mult: Optional[float] = None
    hours: Optional[OpenHours] = None
    messages: Optional[ShopMessages] = None
    temper_player: Optional[int] = None
    temper_attacked: Optional[int] = None


# ---------------------------------------------------------------------------
# Races  (world/RACE, races.jsonl)
# ---------------------------------------------------------------------------

class StatAdjust(PRModel):
    """Per-stat adjustments a race applies at creation."""

    strength: Optional[int] = None
    intelligence: Optional[int] = None
    wisdom: Optional[int] = None
    dexterity: Optional[int] = None
    constitution: Optional[int] = None
    charisma: Optional[int] = None
    luck: Optional[int] = None


class Race(PRModel):
    """A playable or mob race from world/RACE, indexed by vnum in the race table."""

    vnum: int
    source: str
    name: Optional[str] = None
    abbrev: Optional[str] = None
    height: Optional[MinAvgMax] = None
    weight: Optional[MinAvgMax] = None
    adjust: Optional[StatAdjust] = None
    intrinsic: list[Intrinsic] = Field(default_factory=list)
    immune: list[Immunity] = Field(default_factory=list)
    resistant: list[Immunity] = Field(default_factory=list)
    susceptible: list[Immunity] = Field(default_factory=list)
    track: Optional[int] = None
    form: list[Form] = Field(default_factory=list)
    move: Optional[int] = None
    power_gain: Optional[int] = None
    refresh: Optional[int] = None
    resist_fire: Optional[int] = None
    resist_cold: Optional[int] = None
    resist_electricity: Optional[int] = None
    resist_water: Optional[int] = None
    resist_acid: Optional[int] = None
    resist_poison: Optional[int] = None
    resist_force: Optional[int] = None
    resist_magic: Optional[int] = None
    resist_light: Optional[int] = None
    resist_darkness: Optional[int] = None
    resist_all: Optional[int] = None


# ---------------------------------------------------------------------------
# Sectors  (world/SECT, sectors.jsonl)
# ---------------------------------------------------------------------------

class MoveCost(PRModel):
    """Movement cost through a sector for one mode (normal, fly, boat)."""

    moves: Optional[int] = None
    delay: Optional[int] = None
    tracks: Optional[int] = None
    damage: Optional[int] = None
    damage_type: Optional[AttackType] = None           # e.g. room_thicket, room_bracken


class SectorMap(PRModel):
    """Glyphs and colour codes used to draw rooms of this sector on the ASCII map."""

    room: Optional[str] = None
    walls: Optional[str] = None
    exits: Optional[str] = None
    doors: Optional[str] = None
    odoors: Optional[str] = None
    room_color: Optional[str] = None
    detail_color: Optional[str] = None
    dark_color: Optional[str] = None
    wall_color: Optional[str] = None
    exit_color: Optional[str] = None
    door_color: Optional[str] = None
    odoor_color: Optional[str] = None
    fill_color: Optional[str] = None
    pc_color: Optional[str] = None
    mob_color: Optional[str] = None


class Sector(PRModel):
    """A terrain type from world/SECT; rooms reference it by name."""

    vnum: int
    source: str
    name: Optional[str] = None
    flags: list[SectorFlag] = Field(default_factory=list)
    boat: Optional[MoveCost] = None
    fly: Optional[MoveCost] = None
    normal: Optional[MoveCost] = None
    map: Optional[SectorMap] = None
    default_sizes: Optional[list[float]] = None


# ---------------------------------------------------------------------------
# Clans  (world/CLAN, clans.jsonl)
# ---------------------------------------------------------------------------

class Clan(PRModel):
    """A clan from world/CLAN. Membership lives on the player record (clan, clan_rank)."""

    vnum: int
    source: str
    name: Optional[str] = None
    flags: list[ClanFlag] = Field(default_factory=list)
    xp_mult: Optional[float] = None
    min_join_level: Optional[int] = None
    max_join_level: Optional[int] = None
    clanmaster: Optional[str] = None
    deputy: Optional[str] = None


# ---------------------------------------------------------------------------
# Item sets  (world/ITEM_SETS, item_sets.jsonl)
# ---------------------------------------------------------------------------

class SetBonus(PRModel):
    """Bonuses an item set grants once N pieces are worn, plus its activated ability."""

    apply: Applies = Field(default_factory=dict)
    set_ability: Applies = Field(default_factory=dict)
    set_ability_duration: Optional[int] = None
    set_ability_msg: Optional[str] = None


class ItemSet(PRModel):
    """A gear set from world/ITEM_SETS whose bonuses scale with pieces worn."""

    vnum: int
    source: str
    declared_vnum: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    rarity: Optional[Rarity] = None
    use_cooldown: Optional[int] = None
    ws_cooldown: Optional[int] = None
    one_set_bonus: Optional[SetBonus] = None
    two_set_bonus: Optional[SetBonus] = None
    three_set_bonus: Optional[SetBonus] = None
    four_set_bonus: Optional[SetBonus] = None
    five_set_bonus: Optional[SetBonus] = None
    six_set_bonus: Optional[SetBonus] = None
    seven_set_bonus: Optional[SetBonus] = None
    eight_set_bonus: Optional[SetBonus] = None
    nine_set_bonus: Optional[SetBonus] = None
    ten_set_bonus: Optional[SetBonus] = None


# ---------------------------------------------------------------------------
# Effects and skills, the 2011 effect system  (world/SKILL)
# ---------------------------------------------------------------------------

class Modifier(PRModel):
    """How an effect changes its target value: a fixed value, dice, or extra values."""

    value: Optional[float] = None
    dice: Optional[Dice] = None
    extra_values: Optional[list[float]] = None


class EffectFields(PRModel):
    """Fields shared by a top-level effect and an effect nested in a skill."""

    name: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    modify: Optional[Modifier] = None
    pulse_modify: Optional[Modifier] = None
    custom_modify: Optional[Modifier] = None
    min: Optional[float] = None
    max: Optional[float] = None
    duration: Optional[float] = None
    pulse: Optional[float] = None
    modifier_join: Optional[str] = None                # effect_join_styles
    messages: Optional[dict[str, str]] = None          # message key -> text
    procs: Optional[dict[str, str]] = None             # phase -> procedure name


class Effect(EffectFields):
    """A top-level effect definition from world/SKILL/effects.tran (2011 effect system)."""

    vnum: int
    source: str


class Skill(PRModel):
    """A skill from world/SKILL/skills.tran: a name bundling several effects."""

    vnum: int
    source: str
    name: Optional[str] = None
    effects: list[EffectFields] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Zones  (world/ZONE, zones.jsonl)
# ---------------------------------------------------------------------------

class IntList(PRModel):
    """A vnum/room list from the zone grammar.

    ``and_range``/``or_range`` hold [lo, hi]; the list types hold the values.
    """

    type: Literal["and_list", "or_list", "chain_list", "and_range", "or_range"]
    values: list[int]


class ZoneReset(PRModel):
    """When a zone re-runs its load commands: never, when empty, or always, every ``frequency`` ticks."""

    type: Literal["never", "empty", "always"]
    frequency: int                                     # zone ticks, one minute by default


class ZoneLimit(PRModel):
    """Cap on how many of some mobs may exist in the zone at once (object caps are inert)."""

    kind: Literal["mob", "obj"]
    max: int
    vnums: IntList


class ZoneLoad(PRModel):
    """One load spec: a mob, an object, or a fallback chain of specs.

    ``op`` is set on the top-level spec of a sub-command (load / loadgroup).
    Room-level specs carry probability and count; nested ones under
    ``inventory`` / ``contents`` / ``requires`` are objects.
    """

    op: Optional[Literal["load", "loadgroup"]] = None
    kind: Literal["mob", "obj", "chain"]
    probability: Optional[int] = None
    count: Optional[int] = None
    count_type: Optional[Literal["atmost", "upto"]] = None
    vnums: Optional[IntList] = None
    inventory: list[ZoneLoad] = Field(default_factory=list)   # mob
    contents: list[ZoneLoad] = Field(default_factory=list)    # obj
    requires: list[ZoneLoad] = Field(default_factory=list)    # obj, inert at runtime
    items: list[ZoneLoad] = Field(default_factory=list)       # chain


class ZoneCommand(PRModel):
    """One ``in <rooms> load ...`` line: which rooms (relative to the range start) get which loads, ``repeat`` times."""

    repeat: int = 1
    rooms: IntList                                     # relative to the zone's range start
    loads: list[ZoneLoad] = Field(default_factory=list)


class Zone(PRModel):
    """A zone from world/ZONE: a vnum range plus the commands that populate it at boot and on reset."""

    name: str
    source: str
    range: Optional[IntList] = None
    save: Optional[IntList] = None
    reset: ZoneReset
    zone_limit: list[ZoneLimit] = Field(default_factory=list)
    boot_only: list[ZoneCommand] = Field(default_factory=list)
    commands: list[ZoneCommand] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Classes  (world/CLASSES/classes, classes.jsonl)
# ---------------------------------------------------------------------------

class ClassSkillRow(PRModel):
    """One row of a class's SKILLS or PROF table: when and at what cost the skill can be learned."""

    name: str
    min_level: int = 0
    difficulty: int = 0
    cost: int = 0
    max_at_guild: int = 0
    max_learn: int = 0
    prereqs: list[str] = Field(default_factory=list)


class ClassSpellRow(ClassSkillRow):
    """One row of a class's SPELLS table; adds mana cost, mana/power source and component vnums."""

    mana: int = 0
    source: Optional[Literal["mana", "power"]] = None
    components: list[int] = Field(default_factory=list)


class Thac0(PRModel):
    """To-hit progression: the level step and the minimum value."""

    level: int
    min: int


class Speed(PRModel):
    """Attack speed progression: the level step and the maximum."""

    level: int
    max: int


class CharacterClass(PRModel):
    """A character class from world/CLASSES/classes (skills.c boot_class):
    stat limits, saving throws, flags and learnable skills and spells."""

    index: int
    source: str
    classname: Optional[str] = None
    abbrv: Optional[str] = None
    align: list[Literal["neutral", "good", "evil"]] = Field(default_factory=list)
    hp: Optional[Dice] = None                          # hit points gained per level
    min: Optional[Stats] = None                        # lowest each stat may be rolled
    max: Optional[Stats] = None                        # highest each stat may be rolled
    base: Optional[Stats] = None                       # starting stats in "char gen mode"
    extr: Optional[ExtraStatPoints] = None             # points a new character may add
    races: list[str] = Field(default_factory=list)     # two-letter abbreviations
    resists: Optional[Resistances] = None              # scaled by level/500 in play
    items: list[int] = Field(default_factory=list)     # vnums of the starting kit
    thac0: Optional[Thac0] = None
    speed: Optional[Speed] = None
    mult: float = 1.0                                  # experience multiplier
    flags: list[str] = Field(default_factory=list)
    build: Optional[str] = None
    desc: Optional[str] = None
    title: Optional[str] = None
    prof: Optional[str] = None
    saves: Optional[SavingThrows] = None               # base saving throws, 100 based
    decrease: Optional[SavingThrows] = None            # levels per one-point improvement
    minsave: Optional[SavingThrows] = None             # floor each save can reach
    skills: list[ClassSkillRow] = Field(default_factory=list)
    spells: list[ClassSpellRow] = Field(default_factory=list)
    profs: list[ClassSkillRow] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Saved objects: item instances in player, account, locker, auction and
# world-save files  (objdb.c ReadObject)
# ---------------------------------------------------------------------------

class SavedApply(PRModel):
    """One stat modification carried by a saved object."""

    location: Optional[ApplyLocation] = None
    modifier: Optional[int] = None
    qualifier: Optional[int] = None


class SocketApply(PRModel):
    """A gem socketed into an object and the bonus it gives."""

    vnum: Optional[int] = None
    location: Optional[ApplyLocation] = None
    modifier: Optional[int] = None
    name: Optional[str] = None
    identifier: Optional[int] = None
    removable: Optional[bool] = None
    unique: Optional[bool] = None


class SavedSpellItemType(PRModel):
    """scroll and potion as saved: up to three spells, by number, cast at ``level``."""
    level: Optional[int] = None
    spell1: Optional[int] = None
    spell2: Optional[int] = None
    spell3: Optional[int] = None


class SavedChargedItemType(PRModel):
    """wand and staff as saved: one spell, by number, with charges."""
    level: Optional[int] = None
    max_charges: Optional[int] = None
    charges: Optional[int] = None
    spell: Optional[int] = None


class SavedTrapType(PRModel):
    """trap as saved; ``damage_type`` is the raw attack-type number (see TrapType)."""
    effect_type: list[TrapEffect] = Field(default_factory=list)
    damage_type: Optional[int] = None
    level: Optional[int] = None
    charges: Optional[int] = None


class UntypedValues(PRModel):
    """The five ``value[]`` slots of an item whose type gives them no fixed
    meaning: the marker types (other, worn, note, pen, boat, trash, book,
    missile, fire weapon, hierarchical, set item), spell gems (which keep their
    real data in ``dvalue[]``), and items with no type."""
    slots: list[int]


SavedItemValues = Union[
    LightType, SavedSpellItemType, SavedChargedItemType, TreasureType, ContainerType,
    DrinkContainerType, ArmorType, WeaponType, FoodType, UsesType, AudioType, BoardType,
    SocketGemType, SavedTrapType, UntypedValues,
]

# How the game reads ``obj->value[0..4]`` for each item type: the field ids of
# the type block in fields.c minus one (weapon: no_dice is value[1] and so on,
# as fight.c and cmds1.c use them). Enum and flag slots hold numeric codes.
_VALUE_LAYOUT: dict[ItemKind, tuple[type[PRModel], dict[str, tuple[int, Any]]]] = {
    ItemKind.light: (LightType, {"duration": (2, None)}),
    ItemKind.scroll: (SavedSpellItemType, {"level": (0, None), "spell1": (1, None), "spell2": (2, None), "spell3": (3, None)}),
    ItemKind.potion: (SavedSpellItemType, {"level": (0, None), "spell1": (1, None), "spell2": (2, None), "spell3": (3, None)}),
    ItemKind.wand: (SavedChargedItemType, {"level": (0, None), "max_charges": (1, None), "charges": (2, None), "spell": (3, None)}),
    ItemKind.staff: (SavedChargedItemType, {"level": (0, None), "max_charges": (1, None), "charges": (2, None), "spell": (3, None)}),
    ItemKind.treasure: (TreasureType, {"value": (0, None)}),
    ItemKind.money: (TreasureType, {"value": (0, None)}),
    ItemKind.container: (ContainerType, {"max_hold": (0, None), "flags": (1, ContainerFlag.from_bits), "key": (2, None), "timer": (3, None)}),
    ItemKind.pouch: (ContainerType, {"max_hold": (0, None), "flags": (1, ContainerFlag.from_bits), "key": (2, None), "timer": (3, None)}),
    ItemKind.liquid_container: (DrinkContainerType, {"max_units": (0, None), "amount": (1, None), "type": (2, Drink.from_code), "poisoned": (3, None)}),
    ItemKind.armor: (ArmorType, {"effective_ac": (0, None), "force": (1, None), "stopping": (2, None), "absorb": (3, None), "timer": (4, None)}),
    ItemKind.weapon: (WeaponType, {"wtype": (0, WeaponClass.from_code), "no_dice": (1, None), "size_dice": (2, None), "type": (3, DamageType.from_code), "speed": (4, None)}),
    ItemKind.food: (FoodType, {"fullness": (0, None), "poisoned": (3, None)}),
    ItemKind.key: (UsesType, {"uses": (0, None)}),
    ItemKind.component: (UsesType, {"uses": (0, None)}),
    ItemKind.audio: (AudioType, {"frequency": (0, None)}),
    ItemKind.board: (BoardType, {"flags": (0, BoardFlag.from_bits)}),
    ItemKind.socket: (SocketGemType, {"combine": (0, None), "combine_to": (1, None), "removable": (2, bool), "unique": (3, bool)}),
    ItemKind.trap: (SavedTrapType, {"effect_type": (0, TrapEffect.from_bits), "damage_type": (1, None), "level": (2, None), "charges": (3, None)}),
}


def typed_item_values(kind: Optional[str], slots: list[int]) -> PRModel:
    """Give a saved object's ``value[]`` slots the meaning its type gives them."""
    try:
        layout = _VALUE_LAYOUT.get(ItemKind(kind)) if kind is not None else None
    except ValueError:
        layout = None
    if layout is None or len(slots) != 5:
        return UntypedValues(slots=slots)
    model, fields = layout
    return model(**{name: (conv(slots[i]) if conv else slots[i]) for name, (i, conv) in fields.items()})


class SavedObject(PRModel):
    """An item instance. Strings that are None fall back to the prototype's text."""

    vnum: Optional[int] = None
    name: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    action_description: Optional[str] = None
    contents: list[SavedObject] = Field(default_factory=list)
    values: Optional[SavedItemValues] = None           # the file's value[5], read per ``type``
    wear_flags: list[WearFlag] = Field(default_factory=list)
    extra_flags: list[ObjectFlag] = Field(default_factory=list)
    affects: list[AffectBit] = Field(default_factory=list)   # granted while worn
    xtra_bits: Optional[int] = None
    intrinsic_weight: Optional[int] = None
    intrinsic_volume: Optional[int] = None
    contents_weight: Optional[int] = None
    contents_volume: Optional[int] = None
    cost: Optional[int] = None
    cost_per_day: Optional[int] = None
    real_cost: Optional[int] = None
    timer: Optional[int] = None
    timer2: Optional[int] = None
    eq_pos: Optional[WearPosition] = None              # None when not worn
    in_room: Optional[int] = None
    type: Optional[ItemKind] = None
    min_level: Optional[int] = None
    time_stamp: Optional[int] = None                   # deposit time for warehouse rent
    material: Optional[Material] = None
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    apply: list[SavedApply] = Field(default_factory=list)
    pulse_apply: list[SavedApply] = Field(default_factory=list)
    socket_apply: list[SocketApply] = Field(default_factory=list)
    msg_to_room: Optional[str] = None
    msg_to_char: Optional[str] = None
    msg_to_dest: Optional[str] = None
    touch_to_room: Optional[int] = None
    extra_descriptions: list[ExtraDescription] = Field(default_factory=list)
    owner: Optional[str] = None                        # NODROP binding
    held_for: Optional[str] = None                     # insurance salesman / corpse owner
    rarity: Optional[Rarity] = None
    mutation_count: Optional[int] = None
    fixed: Optional[bool] = None
    use_cooldown: Optional[int] = None
    ws_cooldown: Optional[int] = None
    last_use_time: Optional[int] = None
    loaded_by_imm: Optional[str] = None
    edited_by_imm: Optional[str] = None
    mutated_by_imm: Optional[str] = None
    stringed_by_imm: Optional[str] = None
    created_date: Optional[int] = None
    pulse_duration: Optional[int] = None
    pulse_finish_msg: Optional[str] = None
    item_set: Optional[int] = None
    item_ability_desc: Optional[str] = None
    mm_crack_code: Optional[int] = None
    mm_crack_attempts: Optional[int] = None
    tier: Optional[int] = None
    sockets: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def _type_values(cls, data: Any) -> Any:
        """Turn the extractor's raw ``value`` list into ``values`` typed by ``type``."""
        if isinstance(data, dict) and "value" in data and "values" not in data:
            data = dict(data)
            raw = data.pop("value")
            data["values"] = typed_item_values(data.get("type"), raw) if raw is not None else None
        return data


# ---------------------------------------------------------------------------
# Players  (stash/<a-z>/<name>, players.jsonl)
# ---------------------------------------------------------------------------

class Affect(PRModel):
    """A spell affect currently on a character: which spell, how long, what it modifies."""

    type: Optional[int] = None                         # spell number
    type_name: Optional[str] = None
    duration: Optional[int] = None
    modifier: Optional[int] = None
    location: Optional[ApplyLocation] = None
    bitvector: list[AffectBit] = Field(default_factory=list)


class PulseAffect(PRModel):
    """A periodic (damage-over-time style) affect on a character, from player.save.c."""

    type: Optional[int] = None
    type_name: Optional[str] = None
    damage_type: Optional[AttackType] = None
    proc_type: Optional[PulseType] = None
    initial_type: Optional[PulseType] = None
    finish_type: Optional[PulseType] = None
    can_stack: Optional[int] = None
    stack_multiplier: Optional[float] = None
    stack_counter: Optional[int] = None
    start_time: Optional[int] = None
    last_update: Optional[int] = None
    pulse_message: Optional[str] = None
    initial_message: Optional[str] = None
    finish_message: Optional[str] = None
    pulse_proc_delay: Optional[int] = None
    pulse_proc_frequency: Optional[int] = None
    duration: Optional[int] = None
    proc_counter: Optional[int] = None
    total_procs: Optional[int] = None
    location: Optional[ApplyLocation] = None
    location_initial: Optional[ApplyLocation] = None
    location_finish: Optional[ApplyLocation] = None
    modifier: Optional[float] = None
    modifier_initial: Optional[float] = None
    modifier_finish: Optional[float] = None
    caster: Optional[str] = None
    is_npc: Optional[bool] = None
    total_dam: Optional[float] = None
    total_heal: Optional[float] = None
    total_length: Optional[int] = None
    cooldown: Optional[int] = None
    total_hp_victim: Optional[float] = None
    finishing_spell: Optional[int] = None
    finishing_spell_stack_limit: Optional[int] = None
    finishing_proc_stack_limit: Optional[int] = None
    finish_on_caster: Optional[bool] = None
    reset_timer_on_hit: Optional[bool] = None
    finish_spell_lvl_limit: Optional[int] = None
    finish_spell_remort_limit: Optional[int] = None
    can_stack_initial: Optional[int] = None
    stack_counter_initial: Optional[int] = None
    stack_multiplier_initial: Optional[float] = None
    initial_dam_aoe: Optional[float] = None
    pulse_dam_aoe: Optional[float] = None
    finish_dam_aoe: Optional[float] = None
    total_dam_aoe: Optional[float] = None
    aoe_dam_multiplier: Optional[float] = None
    aoe_dam_multiplier_initial: Optional[float] = None
    aoe_dam_multiplier_finish: Optional[float] = None
    is_item_set_ability: Optional[bool] = None
    is_item_ability: Optional[bool] = None
    no_msg: Optional[bool] = None
    proc_modifier_cap: Optional[float] = None
    bitvector: list[AffectBit] = Field(default_factory=list)
    finish_aoe_dam_as_target: Optional[int] = None
    initial_aoe_dam_as_target: Optional[int] = None
    pulse_aoe_dam_as_target: Optional[int] = None
    immune_dispel_magic: Optional[bool] = None
    initial_modifier_cap: Optional[float] = None


class PulseCooldown(PRModel):
    """Cooldown before a pulse affect can be applied to the character again."""

    type: Optional[int] = None
    type_name: Optional[str] = None
    cooldown_expire: Optional[int] = None
    bitvector: list[AffectBit] = Field(default_factory=list)


class ItemSetAbility(PRModel):
    """Runtime state of an activated item-set ability on a character."""

    item_set: Optional[int] = None
    set_name: Optional[str] = None
    ability: Optional[int] = None
    last_use_time: Optional[int] = None
    last_ws_time: Optional[int] = None
    modifier: Optional[int] = None
    cooldown_expire: Optional[int] = None
    bonus_level: Optional[int] = None
    use_duration: Optional[int] = None


class LearnedSkill(PRModel):
    """A skill, spell or weapon proficiency the character has learned and how well."""

    number: int
    kind: Literal["skill", "spell", "proficiency"]
    name: str                                          # "#<n>" when beyond the name table
    learned: int


class RemortBonus(PRModel):
    """A permanent bonus chosen at remort."""

    remort_flag: int
    remort_count: int
    stat_modifier: int
    stat_bonus: int


class Kill(PRModel):
    """Kill count against one mob vnum, from the character's kill table."""

    vnum: int
    count: int


class PlayerTimes(PRModel):
    """Unix times from the player file; ``played`` is accumulated seconds."""

    birth: Optional[int] = None
    logon: Optional[int] = None
    logout: Optional[int] = None
    motd: Optional[int] = None
    password: Optional[int] = None
    played: Optional[int] = None


class Player(PRModel):
    """A player character as saved in stash/<a-z>/<name>; one file per character, owned by an Account."""

    name: Optional[str] = None
    source: str
    file_version: int = 0
    account_name: Optional[str] = None
    account: Optional[int] = None
    pw: Optional[str] = None                           # only with --include-secrets
    sex: Optional[Sex] = None
    class_: Optional[ClassName] = Field(default=None, alias="class")
    race: Optional[RaceName] = None
    level: Optional[int] = None
    max_level: Optional[int] = None
    remort_count: Optional[int] = None
    title: Optional[str] = None
    shortdesc: Optional[str] = None
    longdesc: Optional[str] = None
    description: Optional[str] = None
    namelist: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    plan: Optional[str] = None
    prompt: Optional[str] = None
    base_stats: Stats = Field(default_factory=Stats)
    stats: Stats = Field(default_factory=Stats)
    hit: Optional[int] = None
    max_hit: Optional[int] = None
    mana: Optional[int] = None
    max_mana: Optional[int] = None
    move: Optional[int] = None
    max_move: Optional[int] = None
    power: Optional[int] = None
    max_power: Optional[int] = None
    rage: Optional[int] = None
    energy: Optional[int] = None
    hit_shield: Optional[int] = None
    gold: Optional[int] = None
    bankgold: Optional[int] = None
    exp: Optional[int] = None
    apex_exp: Optional[int] = None
    questpoints: Optional[int] = None
    alignment: Optional[int] = None
    base_alignment: Optional[int] = None
    position: Optional[Position] = None
    act: list[PlayerFlag] = Field(default_factory=list)
    config: list[ConfigFlag] = Field(default_factory=list)
    log: list[LogFlag] = Field(default_factory=list)
    affected_by: list[AffectBit] = Field(default_factory=list)
    resist: list[Immunity] = Field(default_factory=list)
    immune: list[Immunity] = Field(default_factory=list)
    susceptible: list[Immunity] = Field(default_factory=list)
    hit_bonus: Optional[int] = None
    dam_bonus: Optional[int] = None
    attacks_per_round: Optional[float] = None
    assassinate: Optional[int] = None
    defense: Optional[Defense] = None                  # the file's armor[6] and stopping[6]
    base_defense: Optional[Defense] = None             # base_armor[6] and base_stopping[6]
    armor_legacy: Optional[int] = None                 # one AC value, from older player files
    apply_saving_throw: Optional[SavingThrows] = None  # bonuses from equipment and spells
    conditions: Optional[Conditions] = None
    fullness: Optional[int] = None
    weight: Optional[int] = None
    height: Optional[int] = None
    bindpoint: Optional[int] = None
    was_in_room: Optional[int] = None
    worldzone: Optional[int] = None
    offset: Optional[int] = None
    build_lo: Optional[int] = None
    build_hi: Optional[int] = None
    test_lo: Optional[int] = None
    test_hi: Optional[int] = None
    clan: Optional[int] = None
    clan_rank: Optional[ClanRank] = None
    invis_level: Optional[int] = None
    whimpy_level: Optional[int] = None
    spells_to_learn: Optional[int] = None
    skills: list[LearnedSkill] = Field(default_factory=list)
    spells: list[LearnedSkill] = Field(default_factory=list)
    remort_bonuses: list[RemortBonus] = Field(default_factory=list)
    kills: list[Kill] = Field(default_factory=list)
    affects: list[Affect] = Field(default_factory=list)
    pulse_affects: list[PulseAffect] = Field(default_factory=list)
    pulse_cooldowns: list[PulseCooldown] = Field(default_factory=list)
    item_set_abilities: list[ItemSetAbility] = Field(default_factory=list)
    granted: list[str] = Field(default_factory=list)   # command names
    revoked: list[str] = Field(default_factory=list)
    legacy_granted: Optional[list[int]] = None
    legacy_revoked: Optional[list[int]] = None
    mail: list[str] = Field(default_factory=list)
    time: PlayerTimes = Field(default_factory=PlayerTimes)
    first_login: Optional[int] = None
    last_site: Optional[str] = None
    lockout_till: Optional[int] = None
    lockout_message: Optional[str] = None
    new_notes: Optional[int] = None
    page_size: Optional[int] = None
    page_width: Optional[int] = None
    page_min_width: Optional[int] = None
    rent_disable: Optional[int] = None
    carry_weight: Optional[int] = None
    carry_volume: Optional[int] = None
    carry_items: Optional[int] = None
    timer: Optional[int] = None
    equipment: dict[WearPosition, Union[SavedObject, list[SavedObject]]] = Field(default_factory=dict)
    inventory: list[SavedObject] = Field(default_factory=list)
    warehouse: list[SavedObject] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _pair_defense(cls, data: Any) -> Any:
        """Zip the file's parallel ``armor[]`` / ``stopping[]`` arrays into one
        ``BodyPartDefense`` per hit location. Slot 0 (LOCATION_UNKNOWN) is never
        hit and only ever holds the boot default, so it is dropped."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for armor_key, stopping_key, target in (("armor", "stopping", "defense"),
                                                ("base_armor", "base_stopping", "base_defense")):
            if armor_key not in data and stopping_key not in data:
                continue
            armor, stopping = data.pop(armor_key, None), data.pop(stopping_key, None)
            if target in data:
                continue
            if armor is None or stopping is None:
                data[target] = None
                continue
            if len(armor) != 6 or len(stopping) != 6:
                raise ValueError(f"{armor_key}/{stopping_key} must have 6 slots (LOCATION_UNKNOWN..LOCATION_HEAD)")
            data[target] = {name: [armor[i], stopping[i]] for name, i in _LOCATION_SLOTS.items()}
        return data


# ---------------------------------------------------------------------------
# Accounts  (account/<a-z>/<name>, accounts.jsonl)
# ---------------------------------------------------------------------------

class Account(PRModel):
    """A login account as saved in account/<a-z>/<name>; owns one or more Players and a shared warehouse."""

    name: Optional[str] = None
    source: str
    pw: Optional[str] = None                           # only with --include-secrets
    real_name: Optional[str] = None
    maiden_name: Optional[str] = None
    email_address: Optional[str] = None
    characters: list[str] = Field(default_factory=list)
    account: Optional[int] = None                      # balance
    flags: list[AccountFlag] = Field(default_factory=list)
    term_type_id: Optional[int] = None
    last_site: Optional[str] = None
    last_site1: Optional[str] = None
    last_site2: Optional[str] = None
    last_site3: Optional[str] = None
    last_login: Optional[int] = None
    last_logout: Optional[int] = None
    motd: Optional[int] = None
    vote_time: Optional[int] = None
    last_roll_start: Optional[int] = None
    num_rolls: Optional[int] = None
    last_class_char: Optional[int] = None
    granted: list[str] = Field(default_factory=list)
    revoked: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    ignore_list: list[str] = Field(default_factory=list)
    warehouse: list[SavedObject] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Structures with no extractor yet
# ---------------------------------------------------------------------------

class Locker(PRModel):
    """LockerSave/locker.<room>.room: the communal chest in one room."""

    room: int
    source: Optional[str] = None
    items: list[SavedObject] = Field(default_factory=list)


class Storage(PRModel):
    """One document per item store, whatever kind: the shape warehouses and
    lockers share (see explorations/warehouse.org)."""

    kind: Literal["character", "account", "locker"]
    owner: Optional[str] = None                        # character or account name
    room: Optional[int] = None                         # locker room vnum
    items: list[SavedObject] = Field(default_factory=list)


class WorldSaveRoom(PRModel):
    """One room's persisted contents from WorldSave/zone.<n> or RoomSave."""

    vnum: int
    items: list[SavedObject] = Field(default_factory=list)


class WorldSaveZone(PRModel):
    """WorldSave/zone.<n>: the persisted contents of every room in one zone's save range."""

    zone: int
    rooms: list[WorldSaveRoom] = Field(default_factory=list)


class LimitedItemCount(PRModel):
    """WorldSave/Misc/limited.obj: world_count per limited object vnum."""

    vnum: int
    count: int


class BoardMessage(PRModel):
    """One message on a bulletin board."""

    header: str                                        # "date author title"
    body: str


class Board(PRModel):
    """board.c: one file per board object vnum."""

    vnum: int
    messages: list[BoardMessage] = Field(default_factory=list)


class AuctionSale(PRModel):
    """auction.c sale_data."""

    seller: Optional[str] = None
    seller_acct: Optional[str] = None
    bidder: Optional[str] = None
    forsale: Optional[SavedObject] = None
    sold_description: Optional[str] = None
    start_time: Optional[int] = None
    last_update: Optional[int] = None
    bid: Optional[int] = None
    min: Optional[int] = None
    count: Optional[int] = None
    have_sale: bool = False


class Auction(PRModel):
    """<auctioneer>-<room>.auction: the sales held by one auctioneer."""

    auctioneer: str
    room: int
    sales: list[AuctionSale] = Field(default_factory=list)
    inventory: list[SavedObject] = Field(default_factory=list)


class HelpEntry(PRModel):
    """help_table (help.c build_help_index): keywords share one text."""

    keywords: list[str]
    topics: list[str] = Field(default_factory=list)
    min_level: int = 0
    text: str


class Social(PRModel):
    """actions file (social.c social_messg)."""

    command: str
    hide: bool = False
    min_victim_position: Optional[str] = None
    char_no_arg: Optional[str] = None
    others_no_arg: Optional[str] = None
    char_found: Optional[str] = None
    others_found: Optional[str] = None
    vict_found: Optional[str] = None
    not_found: Optional[str] = None
    char_auto: Optional[str] = None
    others_auto: Optional[str] = None


class Msg(PRModel):
    """A three-way combat message: to attacker, to victim, to the room."""

    attacker_msg: Optional[str] = None
    victim_msg: Optional[str] = None
    room_msg: Optional[str] = None


class DamageMessage(PRModel):
    """messages file (fight.c): one alternative for one attack type."""

    attack_type: int
    die: Msg
    miss: Msg
    hit: Msg
    god: Msg
    sanctuary: Optional[Msg] = None


class Story(PRModel):
    """A [keywords] section of a story-teller file (spec_mob.c)."""

    keywords: list[str]
    text: str


class StoryTeller(PRModel):
    """The stories a story-telling mob can recite, from its file."""

    mob_vnum: int
    file: str
    stories: list[Story] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reference tables compiled into the C (names.json in py_json)
# ---------------------------------------------------------------------------

class NameTable(PRModel):
    """A ``char *name[]`` table: position is the numeric code or bit index."""

    name: str
    values: list[str]


class ApplyDefinition(PRModel):
    """apply_fields row in constants.c."""

    index: int
    name: str
    type: Literal["S32", "BIT", "E32"]
    list: Optional[str] = None                         # name table for BIT/E32 values


class SpellDefinition(PRModel):
    """A spell or skill number and its name from spell_list.h."""

    number: int
    name: str


class CommandDefinition(PRModel):
    """cmd_info[] row (interpreter.h command_info)."""

    cmd: str
    minimum_position: str
    minimum_level: int
    priority: int = 0
    flags: list[str] = Field(default_factory=list)
    handler: Optional[str] = None                      # C function name
    num: int = 0


# Mapping from py_json output file to model, for validation and loading.
JSONL_MODELS: dict[str, type[PRModel]] = {
    "rooms": Room, "mobs": Mob, "objects": ObjectPrototype, "shops": Shop,
    "races": Race, "sectors": Sector, "clans": Clan, "item_sets": ItemSet,
    "effects": Effect, "skills": Skill, "zones": Zone, "classes": CharacterClass,
    "players": Player, "accounts": Account,
}
