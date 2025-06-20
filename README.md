# Blades of Desolation Prototype

This repository contains a very small prototype for a deterministic card based combat system inspired by Dark Souls. The code in `game.py` implements the round structure described in `design.md`.

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

## Example Round

Below is a brief example showing one round using the default Samurai deck against the Oni.

```
Starting hand: Iaijutsu Cut, Riposte, Cross-Step, Twin Strikes
Stamina: 6

Enemy telegraphs: Club Sweep (speed 2, damage 4)
Target token: A

Hero plays Iaijutsu Cut (speed 3, cost 1)
Hero acts first and deals 2 damage to the Oni.
Oni survives and hits back for 3 damage after armor.

Iaijutsu Cut moves to cooldown slot 1.
Stamina refreshes to 6 and a new card is drawn.
Enemy deck advances to the next card in its pattern.
```

Run `python3 game.py` for a tiny command line demo or `python3 -m unittest` to execute the tests.
