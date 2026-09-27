/* Emit sizes and signedness of every struct field the player/account/object
 * save-file readers touch, so the Python reader matches the compiled server.
 * Build from src/:  gcc -fsigned-char -Ih -DNO_RUBY -D_GNU_SOURCE -o /tmp/layout ../py_json/tools/layout.c
 */
#include <stdio.h>
#include <stddef.h>
#include <time.h>
#include "structs.h"

#define KIND(x) _Generic((x), \
  unsigned char: "u8", signed char: "s8", char: "s8", \
  unsigned short: "u16", short: "s16", \
  unsigned int: "u32", int: "s32", \
  unsigned long: "u64", long: "s64", \
  unsigned long long: "u64", long long: "s64", \
  double: "f64", float: "f32", default: "other")

static int first = 1;
static void emit(const char *name, size_t size, const char *kind, size_t count) {
  printf("%s\n  \"%s\": {\"size\": %zu, \"kind\": \"%s\", \"count\": %zu}", first ? "" : ",", name, size, kind, count);
  first = 0;
}
#define F(prefix, var, field) emit(prefix "." #field, sizeof(var.field), KIND(var.field), 1)
#define A(prefix, var, field) emit(prefix "." #field, sizeof(var.field), KIND(var.field[0]), sizeof(var.field)/sizeof(var.field[0]))
#define S(name, type) emit("sizeof." name, sizeof(type), "struct", 1)

int main(void) {
  char_data ch; obj_data o; acct_data a; affected_type af; affected_pulse_type pa;
  affected_pulse_cooldown pc; item_set_ability isa;
  printf("{");
  S("char_data", char_data); S("obj_data", obj_data); S("affected_type", affected_type);
  S("char_skill_data", char_skill_data); S("char_spell_data", char_spell_data);
  S("remort_data", remort_data); S("kill_info", kill_info);
  S("old_obj_affected_type", struct old_obj_affected_type);
  S("time_t", time_t); S("ID_TYPE", u16);

  F("ch", ch, sex); F("ch", ch, job); F("ch", ch, level); F("ch", ch, bindpoint); F("ch", ch, max_level);
  F("ch", ch, base_stats.strength); F("ch", ch, base_stats.intelligence); F("ch", ch, base_stats.wisdom);
  F("ch", ch, base_stats.dexterity); F("ch", ch, base_stats.constitution); F("ch", ch, base_stats.charisma); F("ch", ch, base_stats.luck);
  F("ch", ch, stats.strength); F("ch", ch, stats.intelligence); F("ch", ch, stats.wisdom);
  F("ch", ch, stats.dexterity); F("ch", ch, stats.constitution); F("ch", ch, stats.charisma); F("ch", ch, stats.luck);
  F("ch", ch, mana); F("ch", ch, max_mana); F("ch", ch, hit); F("ch", ch, max_hit); F("ch", ch, move); F("ch", ch, max_move);
  A("ch", ch, armor); F("ch", ch, gold); F("ch", ch, bankgold); F("ch", ch, exp);
  F("ch", ch, M_resist); F("ch", ch, M_immune); F("ch", ch, susc); F("ch", ch, affected_by); F("ch", ch, position); F("ch", ch, act);
  F("ch", ch, spells_to_learn); F("ch", ch, carry_weight); F("ch", ch, carry_items); F("ch", ch, timer); F("ch", ch, was_in_room);
  A("ch", ch, apply_saving_throw); A("ch", ch, conditions); F("ch", ch, invis_level); F("ch", ch, race);
  F("ch", ch, base_alignment); F("ch", ch, whimpy_level); F("ch", ch, alignment); F("ch", ch, build_lo); F("ch", ch, build_hi);
  A("ch", ch, stopping); F("ch", ch, clan); F("ch", ch, hit_bonus); F("ch", ch, dam_bonus); F("ch", ch, offset);
  F("ch", ch, log_bits); F("ch", ch, carry_volume); F("ch", ch, power); F("ch", ch, max_power);
  F("ch", ch, new_notes); F("ch", ch, page_size); F("ch", ch, page_width); F("ch", ch, account); F("ch", ch, page_min_width);
  F("ch", ch, lockout_till); F("ch", ch, fullness); F("ch", ch, rent_disable); F("ch", ch, weight); F("ch", ch, height);
  F("ch", ch, questpoints); F("ch", ch, worldzone); F("ch", ch, config_bits); F("ch", ch, remort_count); F("ch", ch, clan_rank);
  F("ch", ch, test_lo); F("ch", ch, test_hi); A("ch", ch, base_armor); A("ch", ch, base_stopping); F("ch", ch, attacks_per_round);
  F("ch", ch, apex_exp); F("ch", ch, hit_shield); F("ch", ch, assassinate); F("ch", ch, rage); F("ch", ch, energy);
  F("ch", ch, granted.num);

  F("af", af, type); F("af", af, duration); F("af", af, modifier); F("af", af, location); A("af", af, bitvector);
  F("pc", pc, type); F("pc", pc, cooldown_expire); A("pc", pc, bitvector);
  F("isa", isa, item_set); F("isa", isa, ability); F("isa", isa, last_use_time); F("isa", isa, last_ws_time);
  F("isa", isa, modifier); F("isa", isa, cooldown_expire); F("isa", isa, bonus_level); F("isa", isa, use_duration);

  F("pa", pa, type); F("pa", pa, damage_type); F("pa", pa, proc_type); F("pa", pa, initial_type); F("pa", pa, finish_type);
  F("pa", pa, can_stack); F("pa", pa, stack_multiplier); F("pa", pa, stack_counter); F("pa", pa, start_time); F("pa", pa, last_update);
  F("pa", pa, pulse_proc_delay); F("pa", pa, pulse_proc_frequency); F("pa", pa, duration); F("pa", pa, proc_counter); F("pa", pa, total_procs);
  F("pa", pa, location); F("pa", pa, location_initial); F("pa", pa, location_finish); F("pa", pa, modifier); F("pa", pa, modifier_initial);
  F("pa", pa, modifier_finish); F("pa", pa, is_npc); F("pa", pa, total_dam); F("pa", pa, total_heal); F("pa", pa, total_length);
  F("pa", pa, cooldown); F("pa", pa, total_hp_victim); F("pa", pa, finishing_spell); F("pa", pa, finishing_spell_stack_limit);
  F("pa", pa, finishing_proc_stack_limit); F("pa", pa, finish_on_caster); F("pa", pa, reset_timer_on_hit); F("pa", pa, finish_spell_lvl_limit);
  F("pa", pa, finish_spell_remort_limit); F("pa", pa, can_stack_initial); F("pa", pa, stack_counter_initial); F("pa", pa, stack_multiplier_initial);
  F("pa", pa, initial_dam_aoe); F("pa", pa, pulse_dam_aoe); F("pa", pa, finish_dam_aoe); F("pa", pa, total_dam_aoe);
  F("pa", pa, aoe_dam_multiplier); F("pa", pa, aoe_dam_multiplier_initial); F("pa", pa, aoe_dam_multiplier_finish);
  F("pa", pa, is_item_set_ability); F("pa", pa, is_item_ability); F("pa", pa, no_msg); F("pa", pa, proc_modifier_cap); A("pa", pa, bitvector);
  F("pa", pa, finish_aoe_dam_as_target); F("pa", pa, initial_aoe_dam_as_target); F("pa", pa, pulse_aoe_dam_as_target);
  F("pa", pa, immune_dispel_magic); F("pa", pa, initial_modifier_cap);

  A("o", o, value); F("o", o, wear_flags); F("o", o, extra_flags); F("o", o, intrinsic_weight); F("o", o, cost); F("o", o, cost_per_day);
  F("o", o, timer); A("o", o, bitvector); F("o", o, xtra_bits); F("o", o, eq_pos); F("o", o, in_room); F("o", o, type_flag); F("o", o, vnum);
  F("o", o, min_level); F("o", o, time_stamp); F("o", o, intrinsic_volume); F("o", o, material); F("o", o, length); F("o", o, width); F("o", o, height);
  F("o", o, real_cost); F("o", o, timer2); F("o", o, contents_volume); F("o", o, contents_weight); F("o", o, touch_to_room); F("o", o, rarity);
  F("o", o, mutation_count); F("o", o, fixed); F("o", o, use_cooldown); F("o", o, last_use_time); F("o", o, created_date); F("o", o, ws_cooldown);
  F("o", o, item_set); F("o", o, mm_crack_code); F("o", o, mm_crack_attempts); F("o", o, obj_tier); F("o", o, sockets); F("o", o, pulse_duration);
  F("o", o, apply[0].location); F("o", o, apply[0].modifier); F("o", o, apply[0].qualifier);
  F("o", o, pulse_apply[0].location); F("o", o, pulse_apply[0].modifier);
  F("o", o, socket_apply[0].vnum); F("o", o, socket_apply[0].location); F("o", o, socket_apply[0].modifier);
  F("o", o, socket_apply[0].identifier); F("o", o, socket_apply[0].removable); F("o", o, socket_apply[0].unique);

  F("a", a, account); F("a", a, term_type_id); F("a", a, num_chars); F("a", a, flags); F("a", a, num_ignore);
  F("a", a, last_roll_start); F("a", a, num_rolls); F("a", a, last_class_char);
  printf("\n}\n");
  return 0;
}
