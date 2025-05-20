# Board Game Simulator

This repository contains a small Python script `sim.py` that performs a
lightweight simulation of a card‑driven board game.  The implementation
models a handful of cards and monsters and demonstrates key mechanics such
as armor, Fate points, persistent effects and elemental vulnerabilities.

Run a quick simulation by executing:

```bash
python3 sim.py
```

The script randomly selects one of the heroes and resolves a brief combat
against a basic enemy.  The output prints the win rate for a number of
trials.  This code is intentionally compact and omits most card effects from
the full game description.  It should be treated as an illustrative starting
point rather than a final rules implementation.
