# Board Game Simulator (Simplified)

This repository contains a small Python script ``sim.py`` that models a very
stripped down version of a dice‐driven board game.  Heroes draw cards from a
deck, roll dice to attack enemies, and gain upgrades after each wave.

The current simulation is intentionally lightweight; many rules from the full
game are omitted or only partially represented.  It does, however, include
several core mechanics such as:

* **Fate** points with a simple reroll mechanic
* Basic handling of attack elements and enemy vulnerabilities
* [Combat] and [Exchange] effect placeholders
* A deterministic test suite that can be run with ``python3 sim.py test``

Running ``python3 sim.py`` executes a short sample run with random heroes and
prints their win rate across 100 fights.
