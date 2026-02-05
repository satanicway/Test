# Spellrift Dungeons Simulator — Implemented Coverage + Remaining Gaps

This file tracks what is now implemented in `spellrift_balance_sim.py` and what still remains to reach strict rulebook fidelity.

## Implemented in current simulator

### Core simulation loop
- 4 fixed heroes and room-by-room mission simulation up to 7 rooms.
- Round-based initiative (heroes + enemies) with shuffled initiative each round.
- End-of-round Taint increase, Despair pressure, Void Surge thresholds (5/10/15), spawn-level scaling, and Collapse behavior.

### Deck and run structure
- Finite shuffled deck behavior for:
  - Standard Gate Deck
  - Nexus Gate Deck
  - Basic Room Deck
  - Temple Room Deck
  - Nexus Room Deck
  - 5 Boon decks
- Gate choice loop using 2 Standard + 1 Nexus options.
- Room card draw from deck matching gate type.

### Combat modeling (movement abstracted)
- Dice system with DMG/SPECIAL/blank probabilities aligned with 2/2/2 faces.
- LP spend/gain and reroll behavior.
- Typed damage by die color and vulnerability application.
- Hero and enemy armor handling.
- Multi-target support for attacks that target >1 enemy.
- Hero turn utility usage (modeled abstractions).

### Conditions
- Two-tier conditions (front/back escalation) via structured condition state.
- Opposing-pair cancellation ladder behavior.
- Duration classes (next_move / heal / surge) with trigger-based cleanup.

### Seals and fragments
- Shared seal bank with cap.
- Banking one special (with Merlin rune-slot override).
- Seal spending for fragment claim or taint increase if unavailable.
- Seal channeling (2 same-color seals -> +1 special).
- Gate unseal with matching seal and taint reduction.

### Hero and villain feature coverage (abstracted)
- Hero attack kits for Hercules, Merlin, Joan, Anansi.
- Hero relic effects (modeled abstractions).
- Unique power abstractions:
  - Titan Grip
  - Rune Writing (rune slots/completed spell/overflow)
  - Oriflamme free reroll influence
  - Golden Webway armor influence
- Villain targeting rules and key effects:
  - Drain LP, web/staggered, armor-up, ignore armor, terror wave, treant splash
- Elite spawn +1 level support for ELITE spawns.

### Room and gate rules (partial but expanded)
- Broad gate start bonuses and several gate rule effects.
- Broad room-rule trigger coverage from basic + temple + nexus rooms (abstracted triggers).
- Temple room exchange behavior represented with policy abstractions.

### Output metrics
- Average HP per hero at end of each room (1..7).
- Average hero damage per room.
- Average Taint per room.
- Average CP contribution per Boon card.
- Supports 20,000-run default Monte Carlo.

---

## Still missing / partial (for strict fidelity)

1. **Exact positional mechanics** (flanking geometry, isolated checks, adjacency/LOS constraints) are probabilistic/abstract, not board-exact.
2. **Exact per-card text fidelity** is still partial for many Boons, Gate rules, Room blessings/omens, and Temple exchanges.
3. **Boss fight system** (boss card + attack deck + summon/defeat flow) is not yet implemented.
4. **Return-to-base campaign loop** and persistent Void Essence across retreat/retry is not fully modeled.
5. **Some advanced keyword rules** (full chain routing, knockback collision geometry, precise multi-target die assignment policies by board state) are approximated.
6. **No full uncertainty report (CI/error bars)** in output yet; only means are printed.

---

## Next implementation priorities

1. Add strict boss system and mission completion logic.
2. Expand all Gate/Room/Temple rule handlers to exact card-text behavior.
3. Expand Boon engine to declarative keyword fidelity for all cards.
4. Add confidence intervals and richer diagnostics to the report.

