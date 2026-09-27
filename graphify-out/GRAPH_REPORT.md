# Graph Report - pr-stuff  (2026-09-27)

## Corpus Check
- 198 files · ~433,937 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 631 file(s) not represented in the graph (top: .room 149, .zon 131, .obj 122)

## Summary
- 4254 nodes · 19174 edges · 158 communities (129 shown, 29 thin omitted)
- Extraction: 54% EXTRACTED · 46% INFERRED · 0% AMBIGUOUS · INFERRED: 8739 edges (avg confidence: 0.85)
- Token cost: 91,595 input · 3,983 output

## Community Hubs (Navigation)
- Character Data Struct
- Spell Implementations
- Object Data Struct
- Player Commands (misc)
- AMPL Scanner & Symtab
- PRLib Headers & Types
- Login & Char Creation
- Reception & Includes
- Nanny Account Menus
- Damage & Area Spells
- Mob Special Procs
- Protection Spells
- Account Management
- Berserk & Affects
- Offensive Combat Commands
- Fight Engine
- Death & Score
- Pulse Affect Struct
- Object Examine & Identify
- Object Editor (oedit)
- Network Comm Layer
- Boards & Bounty Hunter
- Player Save Files
- Clan & Race Boot
- Room Exits & Movement
- Auction System
- Utility & Summon Tables
- rooms.py Converter
- Zone Reset Loader
- Object DB & Corpses
- Relocation & Goto
- Wizard Commands
- Apex & Arena Commands
- Affect Handler
- Connection Data
- Char Skill/Spell Data
- Summoning Spells
- Generic Find & Interpreter
- Pulse Cooldown Struct
- Dimension & Regen Struct
- Equip & Item Set Bonuses
- Signals & World Save
- Room Data Struct
- Clan Commands
- Weapon Spell Skills
- Class Entry Struct
- Look & Listings
- AMPL Parser
- tran World Compiler
- PRLib Memory & Callbacks
- Room Editor (redit)
- Char Description & Prototype
- Purge Utility
- Who & Skill Listings
- Affected Type Struct
- PRLib Array/Hash IO
- PRLib Object Core
- Char Stats Struct
- Damage Calc Commands
- Event Queue
- Account Chat Commands
- At/Form/Weather Commands
- Shop Data Struct
- Mob AI (mobact)
- tran_ruby Compiler
- Effect Procedures
- Save Utility Tools
- Cleric & Fort Procs
- Zone Listing
- Apex Level Struct
- Racial Info Struct
- Limits & Regen
- Schema Reader
- Spell Parser & Followers
- Item Set Struct
- DB Alloc & Nuke
- Object DB Mutation
- PRLib Array Ops
- fetch_mud_chars Script
- Resistances Struct
- Sector Map Strings
- Help Topics
- PRLib Utility & Time
- Sale Data Struct
- Mob Ranking
- Skills & Class Boot
- Command Tree
- MXP & Prompt
- Builder Areas
- Mob Lookup & Shout
- Object Get/Carry
- Apply Stats Struct
- Int Queue
- room2tran Tool
- Spell Entry Struct
- Map Rendering
- String List
- Rage & Energy
- Event Struct
- Class Build Struct
- Remort Options Struct
- Board Files
- Mob Editor (medit)
- Item Set Ability Struct
- Hash Table
- Mob Buff Spell Struct
- Sector Info Struct
- Shop Keeper Logic
- Future Architecture Docs
- Time Data Struct
- Object Apply Editing
- Socket Apply Struct
- Object Size Utils
- Submit Tool
- Zone Binary Readers
- Hate List Struct
- Maze Generator
- Session Transcript Docs
- Trap Damage Struct
- Description Rec Struct
- Char/Account Helpers
- PRLib Free Helpers
- genlist Tool
- strip Code Generator
- Room Reload
- Time Formatting
- Extra Descr Struct
- Ershteep Zone Notes
- Class & Spell Docs
- Developer Guide Doc
- Object Update
- new Script
- update Script
- world/compile Script
- Config Flags Doc
- Old Maps Doc
- MOB compile Script
- OBJ compile Script
- ROOM compile Script
- SHOP compile Script
- ZONE compile Script
- Khull Help Mob Doc
- Uniform Persistence Doc
- py-json Project
- Session View Doc
- Backplot Doc
- Backup Case Note
- Mage Scaling Idea
- Tournament Idea

## God Nodes (most connected - your core abstractions)
1. `char_data` - 1822 edges
2. `obj_data` - 740 edges
3. `vlog()` - 537 edges
4. `act()` - 498 edges
5. `sendf()` - 476 edges
6. `sendc()` - 442 edges
7. `get_rp()` - 331 edges
8. `affected_by_pulse_affect()` - 295 edges
9. `affected_by_pulse_affect_cooldown()` - 241 edges
10. `connection_data` - 221 edges

## Surprising Connections (you probably didn't know these)
- `Perilous Realms — Future Architecture` --semantically_similar_to--> `PR3 Server`  [INFERRED] [semantically similar]
  FUTURE.md → SUMMARY.md
- `check_reconnect()` --calls--> `str_cmp()`  [INFERRED]
  world/HELP/nanny.c → src/PRLib/utility.c
- `state_CHANGE_PNAME()` --calls--> `str_cmp()`  [INFERRED]
  world/HELP/nanny.c → src/PRLib/utility.c
- `state_DELETE_C()` --calls--> `str_cmp()`  [INFERRED]
  world/HELP/nanny.c → src/PRLib/utility.c
- `state_DFLT_TERM()` --calls--> `str_cmp()`  [INFERRED]
  world/HELP/nanny.c → src/PRLib/utility.c

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **MUD Rearchitecture Pattern** — data_model_graph, global_view, session_view, persistence_layer [EXTRACTED 0.90]
- **World Narrative Framework** — unrending_war, pr_world, spell_revamp [INFERRED 0.70]
- **PR Build and Run Process** — makefile_linux, pr_world_compile, pr3_server [EXTRACTED 1.00]
- **Spell and Combat Balance Discussion** — world_docs_skills_spells_profs_txt, world_docs_spells_txt, world_docs_classabilities_txt [INFERRED 0.90]
- **World Geography and Zones** — world_backup_ershteep_road_and_city, world_docs_oldmaps_arandia, world_docs_oldmaps_pharsica [INFERRED 0.70]

## Communities (158 total, 29 thin omitted)

### Community 0 - "Character Data Struct"
Cohesion: 0.01
Nodes (219): do_offset(), special_boot_check(), SkipImmortals(), char_data, account, account_name, act, act_ptr (+211 more)

### Community 1 - "Spell Implementations"
Cohesion: 0.05
Nodes (170): affected_by_pulse_affect(), affected_by_pulse_affect_cooldown(), spell_Create_Monster(), funcp, generic_area_room(), u32, vlog(), shadow() (+162 more)

### Community 2 - "Object Data Struct"
Cohesion: 0.02
Nodes (113): purge_one_obj(), obj_data, action_description, activate_thresholds, apply, bitvector, carried_by, contains (+105 more)

### Community 3 - "Player Commands (misc)"
Cohesion: 0.05
Nodes (99): do_save_range(), do_zone(), slong, do_aggr(), do_consent(), do_report(), do_split(), raw_split() (+91 more)

### Community 4 - "AMPL Scanner & Symtab"
Cohesion: 0.05
Nodes (85): inttypes, FILE, if(), input(), scanner_init(), yy_create_buffer(), yy_delete_buffer(), yy_fatal_error() (+77 more)

### Community 5 - "PRLib Headers & Types"
Cohesion: 0.02
Nodes (83): getGroupCount(), acct_edit, name, str, babble_list, babbles, length, name (+75 more)

### Community 6 - "Login & Char Creation"
Cohesion: 0.07
Nodes (83): can_roll(), bprintf(), create_entry(), get_pchar(), clear_char(), d_mxp_close(), d_mxp_secure(), d_mxp_tag() (+75 more)

### Community 7 - "Reception & Includes"
Cohesion: 0.09
Nodes (35): assert, ctype, dmalloc, fcns, hash, interpreter, kill_data, limits (+27 more)

### Community 8 - "Nanny Account Menus"
Cohesion: 0.08
Nodes (82): add_char_to_account(), can_bypass_menu(), create_char_with_class(), enumerate_classes(), hello_new_conn(), list_chars_to_d(), missing_info(), nanny() (+74 more)

### Community 9 - "Damage & Area Spells"
Cohesion: 0.04
Nodes (80): damage(), spell_acid_cloud(), spell_bloodspines(), spell_burning_hands(), spell_chain_lightn(), spell_clinging_vines(), spell_cone_of_cold(), spell_earthquake() (+72 more)

### Community 10 - "Mob Special Procs"
Cohesion: 0.04
Nodes (79): shoutf(), act_state(), event_mobile(), maintain_pos(), do_wake(), stop_running(), sports_cast(), do_flee() (+71 more)

### Community 11 - "Protection Spells"
Cohesion: 0.06
Nodes (78): send_to_char(), CheckResistanceDamageTypeWithMinScale(), affect_to_char(), affected_by_spell(), spell_armour_as_air(), spell_familiar(), spell_fly(), spell_ineptitude() (+70 more)

### Community 12 - "Account Management"
Cohesion: 0.05
Nodes (76): acct_name_to_path(), char_account_valid(), clear_acct(), delete_account(), free_acct(), get_account(), is_ignoring_acct(), load_acct() (+68 more)

### Community 13 - "Berserk & Affects"
Cohesion: 0.13
Nodes (76): berserk_setBerserk(), berserk_setRecover(), do_berserk(), actf(), update_pos(), add_confuse(), add_hit_shield_to_char(), add_spell_or_ability_cooldown() (+68 more)

### Community 14 - "Offensive Combat Commands"
Cohesion: 0.15
Nodes (73): do_throw(), do_consider(), find_criminal(), make_criminal(), base_attack_damage(), check_peaceful(), CheckResistanceAttackType(), HeightClass() (+65 more)

### Community 15 - "Fight Engine"
Cohesion: 0.06
Nodes (67): do_hitall(), gain_apex_points(), set_mock(), ability_damage_message(), AdjustedResistanceDamage(), appear(), ApplyResistance(), s32 (+59 more)

### Community 16 - "Death & Score"
Cohesion: 0.08
Nodes (59): do_score(), save_all(), rem_char_events(), death_cry(), dieWithXPPenalty(), raw_kill(), raw_kill_no_move(), time (+51 more)

### Community 17 - "Pulse Affect Struct"
Cohesion: 0.03
Nodes (60): affected_pulse_type, aoe_dam_multiplier, aoe_dam_multiplier_finish, aoe_dam_multiplier_initial, bitvector, can_stack, can_stack_initial, caster (+52 more)

### Community 18 - "Object Examine & Identify"
Cohesion: 0.07
Nodes (53): do_examine(), identify_new(), get_and_set_gem_removal_costs(), get_item_set_by_name_in_list_vis(), get_item_set_in_list_vis(), get_obj_in_list(), get_obj_vis_accessible(), get_obj_vis_equ() (+45 more)

### Community 19 - "Object Editor (oedit)"
Cohesion: 0.14
Nodes (51): oedit, bit_vector(), PRE_HDR, STATE_HDR, u32, generic_affect(), list_list(), my_search() (+43 more)

### Community 20 - "Network Comm Layer"
Cohesion: 0.07
Nodes (48): file, in, inet, netdb, socket, boot_idle_conn(), game_loop(), init_socket() (+40 more)

### Community 21 - "Boards & Bounty Hunter"
Cohesion: 0.09
Nodes (51): board_display_msg(), board_remove_msg(), bountyhunter_victory(), special_mob_mail(), do_purge(), do_aid(), do_appraise(), do_puke() (+43 more)

### Community 22 - "Player Save Files"
Cohesion: 0.08
Nodes (41): errno, fcntl, ruby, load_auc_data(), set_boot_clean(), cmd_list, list, num (+33 more)

### Community 23 - "Clan & Race Boot"
Cohesion: 0.07
Nodes (43): boot_clans(), FILE, read_one_clan(), boot_db(), boot_disable(), boot_variables(), init_hash_table(), boot_item_sets() (+35 more)

### Community 24 - "Room Exits & Movement"
Cohesion: 0.08
Nodes (48): bountyhunter_master(), do_scan(), do_exits(), send_to_room(), room_exit, default_state, exit_info, general_description (+40 more)

### Community 25 - "Auction System"
Cohesion: 0.09
Nodes (47): auc_instructions(), auc_list(), Auctioneer(), clean_auc(), do_auc(), formatedBidString(), free_auc_data(), free_sale() (+39 more)

### Community 26 - "Utility & Summon Tables"
Cohesion: 0.06
Nodes (46): reset_time(), summon_entry, max, prob_weight, vnum, check_garlic_placements_debuff(), count_buntavic(), do_moveto() (+38 more)

### Community 27 - "rooms.py Converter"
Cohesion: 0.09
Nodes (43): Any, argparse, dataclasses, Exception, json, Path, pathlib, Context (+35 more)

### Community 28 - "Zone Reset Loader"
Cohesion: 0.13
Nodes (43): mobile, mobobj, object, scommand, command, do_form(), boot_reset(), u32 (+35 more)

### Community 29 - "Object DB & Corpses"
Cohesion: 0.11
Nodes (44): do_potion_make(), InitABoard(), bountyhunter_death(), do_slice(), make_corpse(), apply_ac(), combine_socket(), create_money() (+36 more)

### Community 30 - "Relocation & Goto"
Cohesion: 0.16
Nodes (43): bountyhunter(), do_foreach(), do_goto(), purge_one_room(), do_touch(), completely_cleanout_room(), add_event(), ok_to_fight() (+35 more)

### Community 31 - "Wizard Commands"
Cohesion: 0.08
Nodes (43): send_to_all(), get_char_vis(), ItemSpell(), half_chop(), get_account_char(), add_list(), s32, calc_cents() (+35 more)

### Community 32 - "Apex & Arena Commands"
Cohesion: 0.06
Nodes (37): add_apex_point(), arena_who_string(), s32, compare_strings(), describe_conn(), describe_obj_location(), describe_object(), describe_socketed_object() (+29 more)

### Community 33 - "Affect Handler"
Cohesion: 0.07
Nodes (39): byte, add_rage(), affect_modify(), affect_resist_bits(), affect_total(), affected_by_specific_initial_pulse_affect(), affected_by_specific_item_buff_with_message(), affected_by_specific_pulse_affect() (+31 more)

### Community 34 - "Connection Data"
Cohesion: 0.05
Nodes (41): process_negotiation(), connection_data, acct, buf, char_in_buf, char_list, character, connected (+33 more)

### Community 35 - "Char Skill/Spell Data"
Cohesion: 0.05
Nodes (40): char_skill_data, learned, skill_number, char_spell_data, learned, spell_number, dex_app_type, defensive (+32 more)

### Community 36 - "Summoning Spells"
Cohesion: 0.07
Nodes (38): find_random_mob(), max_follow(), setup_mirror_names(), setup_replicant_names(), spell_cacaodemon(), spell_conjure_elemental(), spell_detect_charm(), spell_dispel_good() (+30 more)

### Community 37 - "Generic Find & Interpreter"
Cohesion: 0.09
Nodes (37): do_potion_add(), do_turn(), do_wcalc(), create_mm_code(), generic_find(), get_obj_vis(), validate_mm_code(), do_list_locker() (+29 more)

### Community 38 - "Pulse Cooldown Struct"
Cohesion: 0.06
Nodes (37): affected_pulse_cooldown, bitvector, cooldown_expire, next, type, u32, item_set_bonus, apply (+29 more)

### Community 39 - "Dimension & Regen Struct"
Cohesion: 0.05
Nodes (37): dimension_info, height, length, width, s32, regen_bonuses, hp, mana (+29 more)

### Community 40 - "Equip & Item Set Bonuses"
Cohesion: 0.18
Nodes (37): add_socket_to_item(), remove_object(), reset_affected_by(), reset_affects(), reset_and_apply_item_set_bonuses(), unequip_char(), ev_update_obj(), ObjFromCorpse() (+29 more)

### Community 41 - "Signals & World Save"
Cohesion: 0.08
Nodes (34): dirent, SIG_RET, signal, free_boards(), free_area_list(), free_messages(), destroy_hash_table(), free_port_list() (+26 more)

### Community 42 - "Room Data Struct"
Cohesion: 0.06
Nodes (35): find_entrances_t, find_entrances(), room_data, contents, dark, description, ex_description, exits (+27 more)

### Community 43 - "Clan Commands"
Cohesion: 0.10
Nodes (34): add_ignore(), is_ignoring_char(), clan_info, clan_flags(), do_clan_evict(), do_clan_invite(), do_clan_join(), do_clan_leave() (+26 more)

### Community 44 - "Weapon Spell Skills"
Cohesion: 0.14
Nodes (33): get_spell_or_skill_name(), event_strike(), fireItemSetWeaponSpell(), ItemSetWeaponSpell(), mob_attack(), WeaponSpell(), affect_from_char(), get_player_remort_statBonus() (+25 more)

### Community 45 - "Class Entry Struct"
Cohesion: 0.06
Nodes (33): class_entry, abbrev, alignment, base, build, class_name, decrease, extra (+25 more)

### Community 46 - "Look & Listings"
Cohesion: 0.13
Nodes (31): do_info2(), do_listcommands(), do_listsocials(), do_listhelp(), SaveLocker(), appendObjectKeyword(), char_condition(), describe_flags() (+23 more)

### Community 47 - "AMPL Parser"
Cohesion: 0.09
Nodes (19): alloca, libintl, malloc, FILE, main(), save_prog(), yy_reduce_print(), yy_symbol_print() (+11 more)

### Community 48 - "tran World Compiler"
Cohesion: 0.13
Nodes (26): FILE, Schema, dump_as_ruby(), dump_block(), dump_list(), field_type(), arg_subst(), BlockParserProc (+18 more)

### Community 49 - "PRLib Memory & Callbacks"
Cohesion: 0.15
Nodes (28): Callbacks, Calloc(), Free(), MallocDebug(), Realloc(), u32, vlog(), ArrayInitWithCapacityAndCallbacks() (+20 more)

### Community 50 - "Room Editor (redit)"
Cohesion: 0.19
Nodes (28): bit_vector(), u32, dir_lookup(), do_rdig(), do_redit(), get_element(), list_list(), redit_choose() (+20 more)

### Community 51 - "Char Description & Prototype"
Cohesion: 0.14
Nodes (27): describe_char(), FindAnAttacker(), list_char_in_room(), look_room(), sprintbit(), sprinttype(), s32, u32 (+19 more)

### Community 52 - "Purge Utility"
Cohesion: 0.12
Nodes (24): main(), main(), should_delete(), find_skill(), find_spell(), finish_obj(), free_char(), free_obj() (+16 more)

### Community 53 - "Who & Skill Listings"
Cohesion: 0.22
Nodes (27): do_mort_who(), do_proficiencies(), do_skills(), do_spells(), do_events(), init_string_block(), page_string_block(), reset_string_block() (+19 more)

### Community 54 - "Affected Type Struct"
Cohesion: 0.07
Nodes (27): affected_type, bitvector, duration, location, modifier, next, type, old_obj_affected_type (+19 more)

### Community 55 - "PRLib Array/Hash IO"
Cohesion: 0.14
Nodes (26): ArrayInitFromFile(), ArrayWriteToFile(), FILE, Hash, HashFree(), HashInitFromFile(), HashReadFromFile(), HashSetValueForKey() (+18 more)

### Community 56 - "PRLib Object Core"
Cohesion: 0.17
Nodes (24): Data, Dictionary, Range, ArrayCopyInto(), CreateRange(), DataAppendBytes(), DataAppendData(), DataCreateWithCapacity() (+16 more)

### Community 57 - "Char Stats Struct"
Cohesion: 0.08
Nodes (26): s8, char_stats_data, charisma, constitution, dexterity, intelligence, luck, strength (+18 more)

### Community 58 - "Damage Calc Commands"
Cohesion: 0.16
Nodes (24): calc_average_weapon_damage(), calc_damage_reduction_rating(), calc_weapon_rating(), ComputeHashValueForKey(), do_map(), do_priority(), grid_expand(), in_group_and_room() (+16 more)

### Community 59 - "Event Queue"
Cohesion: 0.12
Nodes (22): cancel_fight_events(), clean_event_queue(), do_cancel(), event_tick(), free_event_queue(), init_event_queue(), rem_obj_events(), schedule() (+14 more)

### Community 60 - "Account Chat Commands"
Cohesion: 0.13
Nodes (23): ch_acct(), ch_acct_actual(), clear_away(), do_away(), do_gsay(), clear_visited(), do_ask(), do_beep() (+15 more)

### Community 61 - "At/Form/Weather Commands"
Cohesion: 0.13
Nodes (24): do_at(), do_form(), do_mat(), prop_mess(), propagate_message(), do_weather(), get_char_room(), get_char_vis_zone() (+16 more)

### Community 62 - "Shop Data Struct"
Cohesion: 0.08
Nodes (24): shop_data, do_not_buy, in_room, index, keeper, message_buy, message_sell, missing_cash1 (+16 more)

### Community 63 - "Mob AI (mobact)"
Cohesion: 0.19
Nodes (21): act_caster(), discard_items(), eval_spells(), find_best(), find_good_pos(), find_items(), mob_start(), mobile_healer() (+13 more)

### Community 64 - "tran_ruby Compiler"
Cohesion: 0.21
Nodes (21): arg_subst(), BlockParserProc, FILE, Schema, u32, CountSubBlocks(), error(), get_arg() (+13 more)

### Community 65 - "Effect Procedures"
Cohesion: 0.17
Nodes (21): Effect, Procedure, ProcTableEntry, FILE, proc_effect_BuffCharisma(), proc_effect_BuffConstitution(), proc_effect_BuffDexerity(), proc_effect_BuffIntelligence() (+13 more)

### Community 66 - "Save Utility Tools"
Cohesion: 0.13
Nodes (20): FILE, fread_string(), load_messages(), main(), FILE, slong, do_ocreate(), do_oload() (+12 more)

### Community 67 - "Cleric & Fort Procs"
Cohesion: 0.21
Nodes (22): spell_remove_curse(), spell_remove_poison(), cleric(), fort_auor(), fort_elder(), fort_morina(), fort_priest(), pyrpriest() (+14 more)

### Community 68 - "Zone Listing"
Cohesion: 0.21
Nodes (21): intlist, limit, append_to_string_block(), sb_cat(), spaces(), do_zlist(), int_in_list(), mob_vnum_desc() (+13 more)

### Community 69 - "Apex Level Struct"
Cohesion: 0.10
Nodes (21): apex_level_data, armor_penetration, charisma, constitution, damroll, dexterity, hitpoints, hitroll (+13 more)

### Community 70 - "Racial Info Struct"
Cohesion: 0.10
Nodes (21): racial_info, abbrev, adj, form, hate, height, immune, intrinsic (+13 more)

### Community 71 - "Limits & Regen"
Cohesion: 0.28
Nodes (20): calc_speed_percent(), ev_update_player(), graf(), hit_gain(), hit_limit(), hp_cap(), mana_gain(), mana_limit() (+12 more)

### Community 72 - "Schema Reader"
Cohesion: 0.25
Nodes (18): ID_TYPE, FILE, Integer, Schema, CreateOrInitWithSchema(), FieldWithIdentifier(), FieldWithName(), InitWithSchema() (+10 more)

### Community 73 - "Spell Parser & Followers"
Cohesion: 0.14
Nodes (17): sh_int, max_followers(), do_make_leader(), affect_update(), count_followers(), count_following(), count_pc_followers(), ImpSaveSpell() (+9 more)

### Community 74 - "Item Set Struct"
Cohesion: 0.11
Nodes (19): get_highest_setbonus_for_set(), item_set_info, description, eight_set_bonus, five_set_bonus, four_set_bonus, name, nine_set_bonus (+11 more)

### Community 75 - "DB Alloc & Nuke"
Cohesion: 0.12
Nodes (17): cleanout_room(), nuke_mob_db_entry(), nuke_obj_db_entry(), nuke_room_db_entry(), mob_by_name(), index_mem, game_count, max_exist (+9 more)

### Community 76 - "Object DB Mutation"
Cohesion: 0.18
Nodes (17): FILE, do_mutate_object(), generate_short_description(), index_to_mutate(), init_obj(), isPrevLoc(), mutate_object(), obj_to_acct_warehouse() (+9 more)

### Community 77 - "PRLib Array Ops"
Cohesion: 0.18
Nodes (18): adjustArrayCapacity(), appendObject(), ArrayAppendObject(), ArrayCreate(), ArrayCreateCopy(), ArrayCreateWithCapacityAndCallbacks(), ArrayCreateWithCapacty(), ArrayDescription() (+10 more)

### Community 78 - "fetch_mud_chars Script"
Cohesion: 0.18
Nodes (14): CHARS, check_commands(), FAILED_CHARS, log_verbose(), main(), MISSING_CHARS, on_exit(), print_summary() (+6 more)

### Community 79 - "Resistances Struct"
Cohesion: 0.14
Nodes (17): append_apex_point_bonuses(), resistances_data, acid, cold, darkness, electricity, fire, force (+9 more)

### Community 80 - "Sector Map Strings"
Cohesion: 0.12
Nodes (17): SectorMapStrings, dark_color, detail_color, door_color, doors, exit_color, exits, fill_color (+9 more)

### Community 81 - "Help Topics"
Cohesion: 0.18
Nodes (16): topic_entry, keyword, min_level, next, topic_list_node, list, next, topic (+8 more)

### Community 82 - "PRLib Utility & Time"
Cohesion: 0.19
Nodes (14): PRAbsoluteTime, u32, dice(), gettimeofday(), is_abbrev_strict(), number(), PRAbsoluteTimeFromTimeval(), PRAbsoluteTimeGetCurrent() (+6 more)

### Community 83 - "Sale Data Struct"
Cohesion: 0.12
Nodes (16): FILE, ReadSale(), sale_data, bid, bidder, count, forsale, have_sale (+8 more)

### Community 84 - "Mob Ranking"
Cohesion: 0.24
Nodes (15): calc_avg_speed_percent(), purity_bonus_for_class(), resist_modifier_for_class(), get_avg_resist(), get_avg_spell_penetration(), get_avg_stop(), get_mob_exp_string(), get_mob_gold_ratio() (+7 more)

### Community 85 - "Skills & Class Boot"
Cohesion: 0.19
Nodes (15): exact_search(), boot_class(), boot_classes(), FILE, find_or_add_remort_bonus_data(), find_or_add_skill_data(), find_or_add_spell_data(), find_remort_bonus() (+7 more)

### Community 86 - "Command Tree"
Cohesion: 0.22
Nodes (14): command_node, add_command(), build_command_tree(), free_commands(), free_tree(), insert_cmd(), new_node(), register_command() (+6 more)

### Community 87 - "MXP & Prompt"
Cohesion: 0.26
Nodes (14): show_board(), do_auction(), do_gossip(), append_time_stamp(), get_max_combo_for_target(), d_mxp_open(), mxp_close(), mxp_escape() (+6 more)

### Community 88 - "Builder Areas"
Cohesion: 0.25
Nodes (14): add_area(), bin_write_room(), boot_areas(), FILE, u32, do_rsave(), print_bitv(), room_number() (+6 more)

### Community 89 - "Mob Lookup & Shout"
Cohesion: 0.22
Nodes (15): do_shout(), make_group(), slong, get_mob(), real_mobp(), get_mob_alive_by_vnum(), do_mcreate(), god() (+7 more)

### Community 90 - "Object Get/Carry"
Cohesion: 0.28
Nodes (14): do_attribute(), do_get_locker(), can_carry(), can_get_unbound_nodrop(), can_shift(), carried_iron_weight(), do_get(), do_put() (+6 more)

### Community 91 - "Apply Stats Struct"
Cohesion: 0.14
Nodes (15): apply_stats, apply_info, avgMod, count, maxMod, minMod, numSubCounts, subCounts (+7 more)

### Community 92 - "Int Queue"
Cohesion: 0.20
Nodes (15): iqnode, next, x, iqueue, head, tail, create_iqueue(), destroy_iqueue() (+7 more)

### Community 93 - "room2tran Tool"
Cohesion: 0.25
Nodes (13): area_node, name, next, offset, best_fit(), FILE, u32, main() (+5 more)

### Community 94 - "Spell Entry Struct"
Cohesion: 0.14
Nodes (14): spell_entry, components, cost, difficulty, mana, max_at_guild, max_learn, min_level (+6 more)

### Community 95 - "Map Rendering"
Cohesion: 0.18
Nodes (13): MapRoom, RoomList, CreateRoomFromEntrance(), CreateRoomWithFrame(), MapExpand(), render_map(), Point, x (+5 more)

### Community 96 - "String List"
Cohesion: 0.26
Nodes (13): string_list, head, tail, boot_lock_list(), add_string(), create_string_list(), destroy_string_list(), remove_string() (+5 more)

### Community 97 - "Rage & Energy"
Cohesion: 0.31
Nodes (13): consume_rage(), gain_energy(), energy_limit(), find_skill_entry(), find_spell_entry(), get_class(), getTotalAvailableRemortsCount(), getTotalRemortsCount() (+5 more)

### Community 98 - "Event Struct"
Cohesion: 0.17
Nodes (12): reset_door(), event_death(), event_t, args, ch, next, obj, room (+4 more)

### Community 99 - "Class Build Struct"
Cohesion: 0.18
Nodes (12): ClassBuild, build, choiceCount, choices, classCount, classes, flags, begins_with() (+4 more)

### Community 100 - "Remort Options Struct"
Cohesion: 0.17
Nodes (12): remort_options, ability_flag, apex_cost, description, enabled, incrementBy, maxUpgrade, maxValue (+4 more)

### Community 101 - "Board Files"
Cohesion: 0.42
Nodes (10): Board, board(), board_reply_msg(), BoardFileName(), FindBoard(), load_board(), post_message(), reply_subject() (+2 more)

### Community 102 - "Mob Editor (medit)"
Cohesion: 0.42
Nodes (10): medit, PRE_HDR, STATE_HDR, medit_prompt(), pre_DESCRIPTION(), pre_DONE(), pre_SHORT(), state_DESCRIPTION() (+2 more)

### Community 103 - "Item Set Ability Struct"
Cohesion: 0.18
Nodes (11): item_set_ability, ability, bonus_level, cooldown_expire, item_set, last_use_time, last_ws_time, modifier (+3 more)

### Community 104 - "Hash Table"
Cohesion: 0.36
Nodes (9): do_entrances(), _hash_enter(), hash_find(), hash_find_or_create(), hash_iterate(), hash_iterate3(), hash_iterate_range(), hash_remove() (+1 more)

### Community 105 - "Mob Buff Spell Struct"
Cohesion: 0.20
Nodes (10): breather, breaths, cost, vnum, funcp, mob_buff_spell, name, price (+2 more)

### Community 106 - "Sector Info Struct"
Cohesion: 0.20
Nodes (10): sector_info, default_size, flags, map, mc, name, Size, depth (+2 more)

### Community 107 - "Shop Keeper Logic"
Cohesion: 0.40
Nodes (9): is_ok(), merchant_scaling(), ratio(), shop_keeper(), shop_producing(), shopping_kill(), shopping_list(), shopping_sell() (+1 more)

### Community 108 - "Future Architecture Docs"
Cohesion: 0.22
Nodes (9): Property Graph Data Model, Docker Packaging, Perilous Realms — Future Architecture, Global View (Single Writer), HTMX Web Interface, PR3 Server, PR-World Data, Spell System Revamp (+1 more)

### Community 109 - "Time Data Struct"
Cohesion: 0.22
Nodes (9): time_t, time_data, birth, logon, logout, motd, password, played (+1 more)

### Community 110 - "Object Apply Editing"
Cohesion: 0.36
Nodes (9): apply_info_for_location(), Schema, describe_apply(), do_oedit(), fix_applies(), oedit_add(), oedit_list(), oedit_remove() (+1 more)

### Community 111 - "Socket Apply Struct"
Cohesion: 0.25
Nodes (8): obj_socket_apply_type, identifier, location, modifier, name, removable, unique, vnum

### Community 112 - "Object Size Utils"
Cohesion: 0.32
Nodes (8): finish_obj(), object_has_smaller_dimensions(), s32, max_of_three(), max_of_two(), mid_of_three(), min_of_three(), min_of_two()

### Community 113 - "Submit Tool"
Cohesion: 0.50
Nodes (7): FILE, dump_file(), extract_from(), file_to_file(), main(), to_lower(), valid_type()

### Community 114 - "Zone Binary Readers"
Cohesion: 0.67
Nodes (7): modifier, FILE, ReadMobList(), ReadMobObjList(), ReadMod(), ReadSCommandList(), ZReadObjList()

### Community 115 - "Hate List Struct"
Cohesion: 0.29
Nodes (7): hate_list_entry, delete, hatred, name, next, prev, vnum

### Community 116 - "Maze Generator"
Cohesion: 0.53
Nodes (5): cell_type, create_maze(), legal_dirs(), pop(), push()

### Community 117 - "Session Transcript Docs"
Cohesion: 0.33
Nodes (6): makefile.linux, Player Database, PR3 Server, pr-world/compile, Session Transcript (2026-09-18/19), Zone Definition: Ershteep Road

### Community 118 - "Trap Damage Struct"
Cohesion: 0.33
Nodes (6): trap_type_damage, bonus, dice, msg_to_char, msg_to_room, num

### Community 119 - "Description Rec Struct"
Cohesion: 0.40
Nodes (5): description_rec, adv_forms, irec, of_form, Schema

### Community 120 - "Char/Account Helpers"
Cohesion: 0.40
Nodes (5): char_for_account(), char_holding(), char_holding_with_options(), is_player_corpse(), obj_count_list()

### Community 121 - "PRLib Free Helpers"
Cohesion: 0.50
Nodes (5): ArrayFree(), ArrayFreeSubobjects(), HashFreeSubobjects(), SetFree(), SetFreeSubobjects()

### Community 122 - "genlist Tool"
Cohesion: 0.70
Nodes (4): bad_vnum(), free_char(), main(), should_delete()

### Community 123 - "strip Code Generator"
Cohesion: 0.70
Nodes (4): FILE, main(), parse_and_emit_function(), strip_file()

### Community 124 - "Room Reload"
Cohesion: 0.50
Nodes (4): boot_update(), do_rload(), FILE, read_one_room()

### Community 125 - "Time Formatting"
Cohesion: 0.50
Nodes (4): time_t, pretty_time(), time_t, cftime()

### Community 126 - "Extra Descr Struct"
Cohesion: 0.50
Nodes (4): extra_descr_data, description, keyword, next

### Community 127 - "Ershteep Zone Notes"
Cohesion: 0.67
Nodes (3): Ershteep Road and City, Gargoyle, Sewer Key

### Community 128 - "Class & Spell Docs"
Cohesion: 0.67
Nodes (3): Class Abilities Documentation, Skills, Spells, and Proficiencies Discussion, Spell List

## Knowledge Gaps
- **913 isolated node(s):** `py-json`, `x`, `y`, `z`, `width` (+908 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1072 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `char_data` connect `Character Data Struct` to `Spell Implementations`, `Object Data Struct`, `Player Commands (misc)`, `PRLib Headers & Types`, `Login & Char Creation`, `Reception & Includes`, `Nanny Account Menus`, `Damage & Area Spells`, `Mob Special Procs`, `Protection Spells`, `Account Management`, `Berserk & Affects`, `Offensive Combat Commands`, `Fight Engine`, `Death & Score`, `Object Examine & Identify`, `Object Editor (oedit)`, `Network Comm Layer`, `Boards & Bounty Hunter`, `Player Save Files`, `Clan & Race Boot`, `Room Exits & Movement`, `Auction System`, `Utility & Summon Tables`, `Zone Reset Loader`, `Object DB & Corpses`, `Relocation & Goto`, `Wizard Commands`, `Apex & Arena Commands`, `Affect Handler`, `Connection Data`, `Char Skill/Spell Data`, `Summoning Spells`, `Generic Find & Interpreter`, `Pulse Cooldown Struct`, `Dimension & Regen Struct`, `Equip & Item Set Bonuses`, `Signals & World Save`, `Clan Commands`, `Weapon Spell Skills`, `Class Entry Struct`, `Look & Listings`, `Room Editor (redit)`, `Char Description & Prototype`, `Who & Skill Listings`, `Affected Type Struct`, `Char Stats Struct`, `Damage Calc Commands`, `Event Queue`, `Account Chat Commands`, `At/Form/Weather Commands`, `Mob AI (mobact)`, `Save Utility Tools`, `Cleric & Fort Procs`, `Zone Listing`, `Apex Level Struct`, `Limits & Regen`, `Spell Parser & Followers`, `DB Alloc & Nuke`, `Object DB Mutation`, `Resistances Struct`, `Mob Ranking`, `Skills & Class Boot`, `MXP & Prompt`, `Builder Areas`, `Mob Lookup & Shout`, `Object Get/Carry`, `Int Queue`, `Map Rendering`, `String List`, `Rage & Energy`, `Event Struct`, `Board Files`, `Mob Editor (medit)`, `Hash Table`, `Shop Keeper Logic`, `Time Data Struct`, `Object Apply Editing`, `Char/Account Helpers`, `Room Reload`, `Object Update`?**
  _High betweenness centrality (0.417) - this node is a cross-community bridge._
- **Why does `obj_data` connect `Object Data Struct` to `Character Data Struct`, `Spell Implementations`, `Object Update`, `Player Commands (misc)`, `PRLib Headers & Types`, `Reception & Includes`, `Damage & Area Spells`, `Mob Special Procs`, `Protection Spells`, `Account Management`, `Berserk & Affects`, `Offensive Combat Commands`, `Fight Engine`, `Object Examine & Identify`, `Network Comm Layer`, `Boards & Bounty Hunter`, `Player Save Files`, `Room Exits & Movement`, `Auction System`, `Utility & Summon Tables`, `Zone Reset Loader`, `Object DB & Corpses`, `Relocation & Goto`, `Wizard Commands`, `Apex & Arena Commands`, `Affect Handler`, `Summoning Spells`, `Generic Find & Interpreter`, `Pulse Cooldown Struct`, `Dimension & Regen Struct`, `Equip & Item Set Bonuses`, `Room Data Struct`, `Clan Commands`, `Weapon Spell Skills`, `Look & Listings`, `Char Description & Prototype`, `Char Stats Struct`, `Damage Calc Commands`, `Event Queue`, `At/Form/Weather Commands`, `Mob AI (mobact)`, `Save Utility Tools`, `Cleric & Fort Procs`, `Limits & Regen`, `Spell Parser & Followers`, `DB Alloc & Nuke`, `Object DB Mutation`, `Sale Data Struct`, `Object Get/Carry`, `Apply Stats Struct`, `Event Struct`, `Board Files`, `Shop Keeper Logic`, `Object Apply Editing`, `Socket Apply Struct`, `Object Size Utils`, `Char/Account Helpers`, `Extra Descr Struct`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `connection_data` connect `Connection Data` to `Apex & Arena Commands`, `Character Data Struct`, `Char Skill/Spell Data`, `Class Build Struct`, `PRLib Headers & Types`, `Pulse Cooldown Struct`, `Dimension & Regen Struct`, `Login & Char Creation`, `Nanny Account Menus`, `Reception & Includes`, `Account Management`, `Class Entry Struct`, `Network Comm Layer`, `Affected Type Struct`, `MXP & Prompt`, `Object DB & Corpses`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 533 inferred relationships involving `vlog()` (e.g. with `delete_account()` and `free_acct()`) actually correct?**
  _`vlog()` has 533 INFERRED edges - model-reasoned connections that need verification._
- **Are the 493 inferred relationships involving `act()` (e.g. with `do_potion_make()` and `clean_auc()`) actually correct?**
  _`act()` has 493 INFERRED edges - model-reasoned connections that need verification._
- **Are the 472 inferred relationships involving `sendf()` (e.g. with `do_potion_add()` and `do_potion_make()`) actually correct?**
  _`sendf()` has 472 INFERRED edges - model-reasoned connections that need verification._
- **What connects `py-json`, `x`, `y` to the rest of the system?**
  _913 weakly-connected nodes found - possible documentation gaps or missing edges._