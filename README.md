# Board Game Simulator

This repository contains a small Python script `sim.py` that performs a
lightweight simulation of a card‑driven board game.  The implementation
models a handful of heroes, cards and monsters and demonstrates key mechanics
such as armor, Fate points, persistent effects and elemental vulnerabilities.

## Running a simulation

Execute the script directly to run a short combat simulation:

```bash
python3 sim.py
```

By default the script picks a random hero and resolves a fight against the
predefined monster waves.  The output prints the win rate across a number of
trials (20 by default).  You can adjust the number of trials by editing the
`N` constant at the bottom of `sim.py`.

## Fate and rerolls

Heroes accumulate **Fate** as they progress.  When rolling a die they may
spend Fate to reroll a result that fails to meet the target defense.  Hercules
may reroll while above 3 Fate whereas Brynhild requires more than 5.  Fate is
capped at 10.  ``roll_hits`` also checks if a single reroll could finish off an
enemy and automatically uses Fate when possible.

## Elemental vulnerability

Every enemy has an elemental weakness.  When an attack's element matches the
enemy's vulnerability the damage of each hit is doubled.  This is handled by
`roll_hits` which multiplies the number of hits when a vulnerability is
present.

## Upgrades

After clearing a wave the hero gains one upgrade which is drawn from that
hero's upgrade pool and permanently added to the deck.  Upgrades allow the deck
to grow stronger over the course of a run.
