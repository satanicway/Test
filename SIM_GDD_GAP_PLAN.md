# Spellrift Simulator — Remaining Fidelity Gaps (Post-Implementation)

This repository now includes a substantially upgraded simulation model in `spellrift_balance_sim.py`:
- finite shuffled gate/room decks per run,
- initiative + round flow,
- seals (banking/channeling) and fragment claim costs,
- hero LP/special/dice resolution,
- condition escalation/opposition + surge cleanups,
- villain level scaling and core villain effects,
- room-wise outputs (HP, hero damage, taint) and boon CP contributions.

## Still needed for a fully faithful v0.4.2 simulator

1. **Full Boon card fidelity**
   - Only a representative subset of each color deck is modeled.
   - Many conditional effects (Ruin/Chain/Assassinate edge cases) are still abstracted.

2. **Full room card fidelity**
   - Room roster coverage is partial (representative entries for Basic/Temple/Nexus).
   - Several room rules and Eye Omens are approximated as probabilistic pressure effects.

3. **Hero utility + unique powers, full detail**
   - Modeled partially/abstractly (especially Merlin runes); still missing complete behavior for Titan Grip, Oriflamme zone logic, and Golden Webway interactions.

4. **Boss phase and Void Essence flow**
   - Current simulation targets the requested 7-room room-by-room analysis and does not execute boss encounter logic.

5. **Exact task-based fragment claims**
   - Task triggers are probabilistic, not event-proofed against full positional predicates.

6. **Range/adjacency predicates under movement simplification**
   - Effects that depend on strict geometry are translated to average-case probabilities.

7. **Temple exchange policy AI**
   - Temple exchanges are represented as heuristics, not explicit option optimization per state.

## Why this is still useful now

The current simulator already produces the requested Monte Carlo outputs at 20,000 runs:
- average HP per hero at end of each room (1..7),
- average damage dealt by each hero per room,
- average CP contribution per boon card,
- average taint per room.

This gives balance-directional data while preserving runtime practicality and avoiding a full grid/physics simulation.
