# Spellrift Simulator vs GDD v0.4.2 — Gap Analysis and Implementation Plan

This document audits `spellrift_balance_sim.py` against the provided GDD and lists what is **not implemented** or only **partially implemented**, plus a concrete plan to implement each gap.

## Legend
- **Implemented**: present and materially aligned.
- **Partial**: present but simplified/approximate.
- **Missing**: absent.

---

## 1) Global Architecture and Run Structure

### Gaps
1. **Deck-state continuity not modeled exactly** (Gate/Room/Boon decks are sampled each time, not finite shuffled decks per run).  
   Status: **Partial**.
2. **Room card identity and Room rule text not explicitly represented**.  
   Status: **Missing**.
3. **No mission-level boss flow (Void Essence >=3, summon boss, boss deck)**.  
   Status: **Missing**.
4. **No Return to Base / retreat loop and multi-run progression behavior**.  
   Status: **Missing**.

### Plan
- Build a `RunState` with explicit shuffled deck objects: `standard_gate_deck`, `nexus_gate_deck`, `basic_room_deck`, `temple_room_deck`, `altar_room_deck`, and 5 boon decks.
- On each room, perform exact card draws/discards and exhaustion behavior.
- Add room-card data model with:
  - tile id (for future geometry if needed)
  - spawn lists by threat
  - room rule callback.
- Add mission-phase state machine:
  - pre-boss rooms → Nexus clears grant essence → optional boss summon.
- Add retreat policy abstraction (AI policy) and post-retreat effects.

---

## 2) Initiative, Rounds, and Turn Timing

### Gaps
1. **Single initiative line exists, but many start/end timing hooks omitted** (start-of-round room effects, first-time-per-round triggers, etc.).  
   Status: **Partial**.
2. **Round cap (currently hard cap at 8) is simulator-imposed, not in GDD**.  
   Status: **Partial**.

### Plan
- Add event bus hooks for timings:
  - `on_room_start`, `on_round_start`, `on_turn_start`, `on_pre_attack`, `on_post_attack`, `on_turn_end`, `on_round_end`, `on_room_end`.
- Replace hard round cap with configurable fail-safe (`--max-rounds-safety`) and report when safety triggers.

---

## 3) Movement, Position, Terrain, LOS

> The user asked to simplify movement/grid and assume average engagement. This is intentionally omitted.  
> However, several mechanics still depend on adjacency/range/flank/isolated.

### Gaps
1. **No explicit abstract distance model for adjacency/range dependent mechanics**.  
   Status: **Missing**.
2. **Flanking, Isolated, threatened movement events are not represented in an abstract probabilistic way**.  
   Status: **Partial/Missing**.
3. **No LOS abstraction for ranged constraints**.  
   Status: **Missing**.

### Plan
- Add an **abstract engagement state** per combatant pair with probabilities:
  - adjacent probability
  - isolated probability
  - flank probability
  - ranged-LOS probability.
- Parameterize by room archetype/threat and allow calibration from playtest logs.
- Use these probabilities to gate effects (flank bonus, isolated bonuses, chain range validity, etc.) without full grid simulation.

---

## 4) Hero Kits (Attacks, Utility, Unique Powers)

### Gaps
1. **Utilities mostly not modeled** (Heroic Leap, Wyrd Weaver multi-use, Lay on Hands, Nudge the Story).  
   Status: **Missing**.
2. **Unique powers mostly not modeled**:
   - Hercules Titan Grip.  
   - Merlin Rune Writing and rune-slot flow/overflow.  
   - Joan Oriflamme free-reroll aura.  
   - Anansi Golden Webway armor/teleport behavior.  
   Status: **Missing**.
3. **Many attack-specific effects omitted or simplified** (multi-target assignment, pull/push prerequisites, chain lightning details, etc.).  
   Status: **Partial**.

### Plan
- Implement per-hero strategy modules with action priority including utility usage.
- Add support for non-damage effect primitives: `push`, `pull`, `knockback`, `chain`, `heal`, `grant_condition`, `grant_armor`, `reroll_grant`.
- Add state containers:
  - Hercules held-target slot
  - Merlin rune slots + completed spell resolver
  - Joan oriflamme zone state (abstractly represented)
  - Anansi two web markers (abstract usage chances + armor effects).

---

## 5) Villain AI and Villain Effects

### Gaps
1. **Targeting rules partially implemented** (closest approximated via low HP fallback).  
   Status: **Partial**.
2. **Movement/path preference logic omitted** (threatened movement, dangerous terrain avoidance)—acceptable under movement simplification, but needs abstract substitute.  
   Status: **Missing (abstract)**.
3. **Some villain effects simplified or missing** (Banshee terror push all combatants, Dark Wizard push, Treant exact splash radius behavior).  
   Status: **Partial**.
4. **Elite +1 level behavior for elite-tagged spawns not modeled at spawn-card level**.  
   Status: **Missing**.

### Plan
- Build effect functions per villain with explicit trigger timing.
- Add abstract “secondary target exposure probability” for AoE effects.
- Introduce room spawn metadata with elite flags and level override at spawn time.

---

## 6) Conditions System

### Gaps
1. **Two-sided condition escalation (front/back) and anti-stacking logic not fully implemented**.  
   Status: **Missing**.
2. **Opposing pair cancellation ladder not implemented**.  
   Status: **Missing**.
3. **Duration rules incomplete** (until healed, until next move, next surge, etc.).  
   Status: **Partial/Missing**.
4. **Positive/Negative classification and surge cleanup only partly used**.  
   Status: **Partial**.

### Plan
- Replace raw `Counter` with structured `ConditionState`:
  - tier (none/front/back)
  - expiry mode (`surge`, `on_heal`, `next_move`, `next_turn_end`, persistent).
- Implement opposing-pair resolver function and condition transition table.

---

## 7) Seals and Unseal Economy

### Gaps
1. **Seal banking and claim-cost flow are partial** (channeling 2 same-color seals for +1 special absent).  
   Status: **Partial**.
2. **Merlin rune-slot interaction with banking absent**.  
   Status: **Missing**.
3. **Seal cap overflow handling (Merlin overflow) absent**.  
   Status: **Missing**.

### Plan
- Add Seal subsystem with three APIs:
  - `bank_special(hero, color)`
  - `spend_for_fragment(color)`
  - `channel_into_roll(color)`.
- Integrate hero-specific override for Merlin banking destination.

---

## 8) Fragments, Tasks, and Boon Drafting

### Gaps
1. **Fragment task triggers by color are not modeled (red/blue/green/grey/yellow tasks).**  
   Status: **Missing**.
2. **Claim by action vs by task distinction not modeled.**  
   Status: **Missing**.
3. **LP-paid extra draft cards (+1 up to +3) not modeled.**  
   Status: **Missing**.
4. **Exact boon deck draw/discard order and depletion behavior not modeled.**  
   Status: **Partial**.

### Plan
- Add task event detectors and allow out-of-turn fragment claims.
- Implement draft flow exactly:
  - draw 3
  - optional LP spend for extra cards
  - keep 1, bottom rest in chosen order (policy heuristic).
- Maintain finite boon decks and reshuffle rules if desired.

---

## 9) Gate and Room Rules Coverage

### Gaps
1. **Most gate rule text effects are not implemented** (reroll bans, first-round armor ignore, dampening field, bloody fate, etc.).  
   Status: **Mostly Missing**.
2. **Temple exchange options not modeled.**  
   Status: **Missing**.
3. **Basic room blessings and altar eye omens mostly not modeled.**  
   Status: **Missing**.

### Plan
- Convert gate/room effects into data-driven modifiers:
  - passive constraints
  - one-time triggers
  - per-round triggers.
- Implement each gate rule as a tested effect function.
- Add temple decision policy engine for exchange options.

---

## 10) Boon Card Fidelity

### Gaps
1. **Boon set includes simplified projections, not full exact text behavior**.  
   Status: **Partial**.
2. **Many keyword mechanics absent/incomplete in boon resolution**:
   - Chain Lightning, Life Wave, Ruin chaining, Inspire, Bulwark, Assassinate logic.
   Status: **Partial/Missing**.
3. **Cards with placeholder/no effect are included but not distinguished for analytics quality.**  
   Status: **Partial**.

### Plan
- Encode boon cards as declarative effect specs with reusable keyword resolvers.
- Add coverage tests per keyword to ensure deterministic trigger accounting.
- Report confidence labels per boon contribution:
  - exact, approximated, placeholder.

---

## 11) Damage Math and Type Handling

### Gaps
1. **Mixed-type damage separation for vulnerability/resistance is simplified** (single dominant type heuristic).  
   Status: **Partial**.
2. **Multi-target attacks with per-die assignment not implemented.**  
   Status: **Missing**.

### Plan
- Keep per-die color outcomes in a typed damage bucket map.
- Apply vulnerability/resistance per type, then armor, then sum.
- For multi-target attacks, add assignment policy solver (greedy by kill-probability).

---

## 12) Taint, Despair, Surge, Collapse

### Gaps
1. **Core taint/despair/surge modeled, but not all taint modifiers from gate/room/temple effects.**  
   Status: **Partial**.
2. **Collapse handling approximated; needs strict end-of-next-round loss semantics tied to boss/escape conditions.**  
   Status: **Partial**.

### Plan
- Centralize taint changes via `apply_taint(delta, reason)` to ensure all effects route through one system.
- Implement strict collapse timeline with explicit countdown state.

---

## 13) Output and Analysis Quality

### Gaps
1. **Required outputs are present, but confidence/variance intervals missing.**  
   Status: **Partial**.
2. **No per-room win rate / room clear probability / death counts by hero diagnostics.**  
   Status: **Missing**.
3. **No calibration tooling against real playtest logs.**  
   Status: **Missing**.

### Plan
- Add 95% confidence intervals for all reported averages.
- Add diagnostics table:
  - room clear rate
  - hero death incidence
  - average rounds per room
  - seal usage and taint-source breakdown.
- Add optional CSV/JSON export for plotting.

---

## 14) Recommended Implementation Sequence

### Phase 1 — Rules-Core Accuracy (highest impact)
1. Structured condition engine.
2. Typed damage buckets + vulnerability/resistance correctness.
3. Exact seal subsystem (including channeling).
4. Task-based fragment claims + exact draft flow.

### Phase 2 — Content Coverage
5. Gate rules complete implementation.
6. Basic room blessings and altar omens.
7. Temple exchanges with policy AI.
8. Elite spawn tags and room-card specific spawns.

### Phase 3 — Hero/Villain Fidelity
9. Hero utilities and unique powers.
10. Villain special effects full behavior.
11. Multi-target and keyword effect engine.

### Phase 4 — Mission Loop and Analytics
12. Void Essence + boss flow + retreat loop.
13. Confidence intervals and richer telemetry.
14. Calibration hooks and parameter tuning pipeline.

---

## 15) Definition of Done for “Faithful Simulation”

A simulator version should be considered faithful when:
1. All gate rules, room rules, and villain/hero powers are represented by explicit tested mechanics.
2. Condition transitions and durations match the rulebook tables.
3. Damage typing and special-spend rules match card text semantics.
4. Deck draws are finite and reproducible with deterministic seeds.
5. Report contains required averages plus uncertainty and event-source diagnostics.

