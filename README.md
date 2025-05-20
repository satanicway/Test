# Board Game Simulator

This repository contains a small Python script `sim.py` that performs a very
lightweight simulation of a card‑driven board game. The current implementation
only models a handful of cards and monsters, but demonstrates key mechanics
such as armor, Fate points, and elemental vulnerabilities.

Run a quick simulation by executing:
 main

```bash
python3 sim.py
```
The script randomly selects one of the heroes and attempts a short series of
battles against simplified enemies. The output prints the overall win rate for
100 trials.

This code is intentionally compact and omits most card effects from the full
game description. It should be treated as an illustrative starting point rather
than a final rules implementation.
 main
