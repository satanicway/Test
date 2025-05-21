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
Enemies appear in waves with specific HP, defense, vulnerabilities and abilities (e.g. Web Slinger converting ranged to melee, Disturbed Flow preventing rerolls). Elite versions add stronger effects like Sticky Web or Spiked Armor.

### Enemy Cards
The table below lists every enemy defined in the design. "Damage" gives the
four-number damage band used when rolling their attacks.

```text
NameXPSpawnVulnerabilityHPDefenseTypeDamageAbility
Shadow Spinner43 (A)Spiritual <S>14Melee0/0/1/3Web Slinger: Ranged attacks are considered Melee.
Shadow Spinner43 (B)Spiritual <S>14Melee0/0/1/3Web Slinger: Ranged attacks are considered Melee.
Void Soldier43 (C)Precise <P>25Melee0/0/0/2Dark Phalanx: Soldiers take -1 <DMG> (min. 1) from multi target attacks, if at least 2 Soldiers are alive.
Void Soldier43 (D)Precise <P>25Melee0/0/0/2Dark Phalanx: Soldiers take -1 <DMG> (min. 1) from multi target attacks, if at least 2 Soldiers are alive.
Priest of Oblivion33 (A)Arcane <A>23Ranged0/0/1/1Power of Death: Priests deal +1 <DMG> for each dead Priest in this combat.
Priest of Oblivion33 (B)Arcane <A>23Ranged0/0/1/1Power of Death: Priests deal +1 <DMG> for each dead Priest in this combat.
Corrupted Dryad53 (C)Brutal <B>24Melee0/0/1/1Cursed Thorns: Unused <ARMOR> at end of Exchange cause hero to lose that amount of <HP>.
Corrupted Dryad53 (D)Brutal <B>24Melee0/0/1/1Cursed Thorns: Unused <ARMOR> at end of Exchange cause hero to lose that amount of <HP>.

Dark Minotaur52 (A)Precise <P>43Melee0/0/1/3Cleaving and Stomping: Minotaurs deals <DMG> to each hero in battle.
Dark Minotaur52 (B)Precise <P>43Melee0/0/1/3Cleaving and Stomping: Minotaurs deals <DMG> to each hero in battle.
Dark Wizard42 (C)Brutal <B>23Ranged0/1/1/3Curse of Torment: Hero takes 1 <DMG> whenever it rolls a 1 or 2 (after rerolls).
Dark Wizard42 (D)Brutal <B>23Ranged0/1/1/3Curse of Torment: Hero takes 1 <DMG> whenever it rolls a 1 or 2 (after rerolls).
Shadow Banshee42 (A)Divine <D>35Melee0/0/1/2Ghostly: Start of 4th Exchange, end combat without resolution. MOVE Banshees to the next letter Location in this tile.
Shadow Banshee42 (B)Divine <D>35Melee0/0/1/2Ghostly: Start of 4th Exchange, end combat without resolution. MOVE Banshees to the next letter Location in this tile.

Void Gryphon51 (C)Spiritual <S>45Melee0/1/3/4Aerial Combat: Melee Attacks have -1 to <Hit> the Gryphon.
Void Gryphon51 (D)Spiritual <S>45Melee0/1/3/4Aerial Combat: Melee Attacks have -1 to <Hit> the Gryphon.
Void Treant61 (A)Divine <D>76Melee0/1/1/4Power Sap: End of each Exchange, end 1 Combat effect. If it does, HEAL 1 the Treant.
Void Treant61 (B)Divine <D>76Melee0/1/1/4Power Sap: End of each Exchange, end 1 Combat effect. If it does, HEAL 1 the Treant.
Corrupted Angel51 (C)Arcane <A>55Melee0/1/2/5Corrupted Destiny: Start of each Exchange, the hero loses 2 <Fate>.
Corrupted Angel51 (D)Arcane <A>55Melee0/1/2/5Corrupted Destiny: Start of each Exchange, the hero loses 2 <Fate>.

ELITE ENEMIESSpawnVulnerabilityHPDefenseDamageAbility
Shadow Spinner63 (A)Spiritual <S>25Melee0/0/1/4Sticky Web: Heroes DRAW -1 card on each Exchange draws.
Shadow Spinner63 (B)Spiritual <S>25Melee0/0/1/4Sticky Web: Heroes DRAW -1 card on each Exchange draws.
Void Soldier63 (C)Precise <P>36Melee0/0/1/3Spiked Armor: Whenever a single attack deals 3+ <DMG> against a Soldier, the hero loses 1 <HP>.
Void Soldier63 (D)Precise <P>36Melee0/0/1/3Spiked Armor: Whenever a single attack deals 3+ <DMG> against a Soldier, the hero loses 1 <HP>.
Priest of Oblivion53 (A)Arcane <A>34Ranged0/0/1/2Silence: No Combat or Exchange cards apply their effects.
Priest of Oblivion53 (B)Arcane <A>34Ranged0/0/1/2Silence: No Combat or Exchange cards apply their effects.
Corrupted Dryad73 (C)Brutal <B>25Melee0/1/1/2Disturbed Flow: Dice can't be rerolled in this combat.
Corrupted Dryad73 (D)Brutal <B>25Melee0/1/1/2Disturbed Flow: Dice can't be rerolled in this combat.

Dark Minotaur72 (A)Precise <P>53Melee0/0/2/4Enrage: When at 3 <HP> or less, the Minotaur attacks twice.
Dark Minotaur72 (B)Precise <P>53Melee0/0/2/4Enrage: When at 3 <HP> or less, the Minotaur attacks twice.
Dark Wizard62 (C)Brutal <B>24Ranged0/2/2/3Void Barrier: Gain 1 <Armor> for each different type of Element <DMG> applied against it. (<B>, <P>, etc...)
Dark Wizard62 (D)Brutal <B>24Ranged0/2/2/3Void Barrier: Gain 1 <Armor> for each different type of Element <DMG> applied against it. (<B>, <P>, etc...)
Shadow Banshee62 (A)Divine <D>45Melee0/0/1/3Banshee Wail: Deal 1 <DMG> to all heroes in this Combat for each 3 dice rolled against this Banshee in the Exchange (rounded down).
Shadow Banshee62 (B)Divine <D>45Melee0/0/1/3Banshee Wail: Deal 1 <DMG> to all heroes in this Combat for each 3 dice rolled against this Banshee in the Exchange (rounded down).

Void Gryphon71 (C)Spiritual <S>55Melee0/2/4/6Ephemeral Wings: After you deal <DMG> to the Gryphon, your next card in the Exchange deals no <DMG> to it.
Void Gryphon71 (D)Spiritual <S>55Melee0/2/4/6Ephemeral Wings: After you deal <DMG> to the Gryphon, your next card in the Exchange deals no <DMG> to it.
Void Treant81 (A)Divine <D>87Melee0/1/3/5Roots of Despair: Whenever a hero miss all dice on an attack card, it loses 1 <HP>.
Void Treant81 (B)Divine <D>87Melee0/1/3/5Roots of Despair: Whenever a hero miss all dice on an attack card, it loses 1 <HP>.
Corrupted Angel71 (C)Arcane <A>76Melee0/3/3/6Denied Heaven: Reroll all dice whose face is 8 (as many times as necessary).
Corrupted Angel71 (D)Arcane <A>76Melee0/3/3/6Denied Heaven: Reroll all dice whose face is 8 (as many times as necessary).
```

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
