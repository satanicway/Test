# Blades of Desolation Prototype

This repository contains a very small prototype for a deterministic card based combat system inspired by Dark Souls. The code in `game.py` implements the round structure described in `design.md`.

## Project Purpose

The goal of this repository is to provide a lightweight sandbox for
experimenting with a deterministic card‑driven combat loop.  It models a
"Souls‑like" encounter using a fixed‑order hero deck and predictable enemy
patterns.  The code focuses on clarity over presentation and runs entirely in
the terminal.

## Setup

1. Ensure Python 3.11+ is available on your system.
2. Clone the repository.
3. No external packages are required.

Run the minimal demo with:

```bash
python3 game.py
```

Execute the unit tests with:

```bash
python3 -m unittest
```

## Card System

Heroes fight using a fixed order deck of action cards. At the start of play you choose the order of your 12 cards and draw the top four as your hand. Each card has a speed and stamina cost. When you play a card:

1. The stamina cost is paid from your hero's pool (default 6).
2. The card is placed in the first slot of a two step cooldown track.
3. After each round the cooldown slots slide forward. When a card falls off the second slot it is returned to the bottom of the deck and can be drawn again.

This predictable cycle means you always know when a card will return, rewarding careful planning.

## Stamina

Stamina represents your ability to act. Every card has a cost. You regain full stamina each round after cooldown is processed. Running out of stamina limits which cards you can play until it refreshes.

## Enemy Patterns

Enemies use their own small pattern decks. They reveal the next card at the start of each round ("telegraphing" the attack) and step through the deck one card per round, looping back to the beginning when they reach the end. Because the order never changes you can learn and predict enemy behavior.

## Hero Cards and Abilities

Each Samurai deck contains the same twelve cards in a fixed order you choose during setup. Several cards have special rules beyond their type, speed and stamina cost:

| ID | Name           | Extra Rule |
|----|---------------|------------|
| 1  | Iaijutsu Cut  | +1 damage if you were not targeted this round |
| 2  | Riposte       | Next Heavy attack gains +2 damage |
| 3  | Cross-Step    | Move 1 hex left before resolving |
| 4  | Twin Strikes  | Chain: immediately play card #6 for 0 stamina |
| 5  | Great Kesa    | 5 damage; unusable if stamina ≤ 2 |
| 6  | Draw Cut      | Counts as a Parry if it resolves before the attack |
| 7  | Guarded Stance| Reduce the next hit by 2 |
| 8  | Ki Focus      | Refresh one card from cooldown |
| 9  | Shadow Step   | Teleport to any adjacent back hex |
| 10 | Flourish      | Pull aggro; you become the priority target next round |
| 11 | Zen Recovery  | Gain 1 stamina; skip attack |
| 12 | Crescent Moon | Heavy attack hitting a 180° front arc |

## Enemy Effects

Enemy pattern cards can also include special effects:

* **Oni** – *Rage Roar* drains 1 stamina from every hero. *Recuperate* buffs the next attack with +1 damage. *Double Swipe* hits twice.
* **Samurai** – *Parry Counter* grants +4 damage to the next attack. *Focused Stare* resets the deck back to card 1.

## Position and Areas

The prototype tracks hero and enemy locations on a small grid. Enemy cards define arcs such as "90° front" or "180° front" which are converted into coordinate sets. Dodge cards succeed only if you move out of the attack area. Some hero cards modify position:

* **Cross-Step** shifts the hero one hex left before checking the dodge.
* **Shadow Step** teleports to a hex behind the enemy, automatically outside most front arcs.


## Example Round

Below is a short example round showing a special card ability and an enemy special attack.

```
Starting hand: Cross-Step, Iaijutsu Cut, Riposte, Twin Strikes
Stamina: 6

Enemy telegraphs: Double Swipe (speed 2, damage 3) – hits twice
Target token: B

Hero plays Cross-Step (speed 3, cost 1)
Hero moves one hex left before the attack and resolves first.
Leaving the 180° arc causes both swings to miss.

Cross-Step moves to cooldown slot 1.
Stamina refreshes to 6 and a new card is drawn.
Enemy deck advances to the next card.
```

Run `python3 game.py` for a tiny command line demo or `python3 -m unittest` to execute the tests.
