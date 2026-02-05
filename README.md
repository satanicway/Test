# Spellrift Dungeons — Balance Simulation Workspace

This repository now contains only artifacts related to **Spellrift Dungeons**.

## Contents

- `spellrift_balance_sim.py` — Monte Carlo simulator for Spellrift Dungeons alpha balance testing.
- `SIM_GDD_GAP_PLAN.md` — Gap analysis and implementation roadmap versus GDD v0.4.2.

## Quick start

```bash
python3 spellrift_balance_sim.py --sims 20000 --seed 42
```

Use `--sims` to configure the number of simulation runs.
Use `--max-rounds-safety` to cap pathological long combats in the abstract model.
