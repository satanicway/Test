# Game Design and Coding Reference

This file summarises the intended card sets, enemy stats and gameplay rules for the board game simulator. It serves as a reference for future development.

## Gameplay Overview
- Heroes draw from a deck of cards consisting of attacks and utility abilities.
- **Fate** is used for rerolls and special costs (max 10).
- **Armor** absorbs damage before HP.
- **Hymns** (Brynhild) provide persistent buffs lasting an exchange or combat.
- Attacks can be Brutal (B), Precise (P), Divine (D), Arcane (A) or Spiritual (S). Matching the enemy's vulnerability doubles damage.
- Combat proceeds in waves. Each wave plays up to four exchanges where cards resolve in the order: Utility → Ranged → monster attacks → delayed Ranged → Melee. After each exchange, end‑of‑exchange effects trigger and the hero draws a card.
- After a wave the hero gains 1 Fate, draws 2 cards and chooses an upgrade from a weighted pool: 3 copies of each common, 2 of each uncommon, 1 of each rare.

## Card Catalogues
The game defines four heroes – **Brynhild**, **Musashi**, **Merlin** and **Hercules** – each with a starting deck of ten cards and thirty upgrades. The tables from the design document list every card with its element, type and effect. They are too long to repeat here but can be found in `docs/full_card_lists.txt` (to be added later).

### Example – Brynhild Initial Deck
```
Valkyrie's Descent – Melee – 1 S DMG, +2 per active Hymn. End all Hymns.
Sky-Piercer – Ranged – 1 S DMG. Gain 1 Fate (3 if the attack misses all dice.)
Hymn of Shields – Ranged – [Combat] End of Exchange, all heroes gain 1 Armor per active Hymn (max 3.)
Hymn of Storms – Ranged – [Combat] -1 Hit. End of exchanges, deal 3 D DMG per active Hymn.
Thrust of Destiny – Melee – 1 P DMG, +1 Armor per 4 Fate you have.
Spear of the Æsir – Melee – 1 B DMG. [Exchange] Each miss grants +1 Armor and +1 Fate.
```
Upgrade cards extend these mechanics with stronger attacks, new Hymn types, healing and Fate manipulation.

## Enemy Roster
Enemies appear in waves with specific HP, defense, vulnerabilities and abilities (e.g. Web Slinger converting ranged to melee, Disturbed Flow preventing rerolls). Elite versions add stronger effects like Sticky Web or Spiked Armor. Full enemy tables are part of the design assets.

## Outstanding Features
The current simulator only implements a handful of placeholder cards. Major gaps include:
1. Full hero card lists and their complex effects.
2. Hymn bonuses and armor cap logic.
3. Hero-specific Fate thresholds for rerolls.
4. Proper handling of temporary vulnerability on multi-target attacks.
5. Element switching and early resolution for some Musashi cards.
6. Global reroll should grant only one extra reroll per attack.
7. Gryphon "ephemeral wings" blocks must be cleared on death.
8. Upgrade pools should reset between runs.

## Task Breakdown
Development can be divided into small tasks:
1. **Brynhild Cards – Set 1**: implement base deck mechanics and hymn counting.
2. **Brynhild Cards – Set 2**: implement common upgrades.
3. **Brynhild Cards – Set 3**: implement uncommon and rare upgrades.
4. **Hercules Cards – Set 1**: base deck plus early commons.
5. **Hercules Cards – Set 2**: uncommon cards.
6. **Hercules Cards – Set 3**: rare cards.
7. **Musashi Cards – Set 1**: base deck with vulnerability checks and element choice.
8. **Musashi Cards – Set 2**: common upgrades.
9. **Musashi Cards – Set 3**: uncommon and rare upgrades.
10. **Merlin Cards – Set 1**: base deck support effects.
11. **Merlin Cards – Set 2**: common upgrades.
12. **Merlin Cards – Set 3**: uncommon and rare upgrades.
13. **Mechanics fixes**: hymn armor cap, fate thresholds, global reroll limit, vulnerability on all targets, element switching/priority, gryphon block cleanup, reset upgrade pools.

This document should be updated as new mechanics are implemented.
