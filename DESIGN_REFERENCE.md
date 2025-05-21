# Game Design and Coding Reference

This document consolidates all gameplay data, card lists, enemy stats and outstanding features for the board game simulator. Use it as a comprehensive reference when implementing or expanding the code.

## Gameplay Overview
- Heroes play through a series of **waves** of enemies. Each wave lasts up to four exchanges.
- Cards resolve in the order: **Utility ➜ Ranged ➜ Monster attacks ➜ delayed Ranged ➜ Melee**.
- After an exchange, end-of-exchange effects trigger and the hero draws a card.
- After defeating a wave the hero gains 1 Fate, draws 2 cards and chooses one upgrade from their pool.
- **Fate** is a resource used for rerolls or to pay card costs (max 10).
- **Armor** reduces incoming damage on a one-for-one basis.
- **Hymns** are persistent songs that Brynhild can maintain for an Exchange or entire Combat. Some cards count the number of active Hymns for bonuses.
- Each hero has a starting deck of 10 cards and a pool of 30 upgrades. Upgrade pools contain 3 copies of each Common, 2 of each Uncommon and 1 of each Rare to weight their drop chances.

## Hero Card Lists
Tables below show every card. Comments explain their intent.

### Brynhild
Initial Deck
Rarity | Attr/Elem | Name | Type | Effect & Comment
---|---|---|---|---
Common | Wisdom/Spiritual | Valkyrie's Descent | Melee | 1 S DMG, +2 per active Hymn. End all Hymns. *(Finisher consuming Hymns)*
Common | Wisdom/Spiritual | Valkyrie's Descent | Melee | same as above
Common | Wisdom/Spiritual | Sky-Piercer | Ranged | 1 S DMG. Gain 1 Fate, or 3 if attack misses all dice. *(Fate generation)*
Common | Charisma/Divine | Hymn of Shields | Ranged | [Combat] End of Exchange, all heroes gain 1 Armor per active Hymn (max 3). *(Team defense)*
Common | Charisma/Divine | Hymn of Shields | Ranged | same as above
Common | Charisma/Divine | Hymn of Storms | Ranged | [Combat] -1 Hit. End of exchanges, deal 3 D DMG per active Hymn. *(Damage hymn)*
Common | Agility/Precise | Thrust of Destiny | Melee | 1 P DMG. +1 Armor per 4 Fate. *(Rewards high Fate)*
Common | Agility/Precise | Thrust of Destiny | Melee | same as above
Common | Strength/Brutal | Spear of the Æsir | Melee | 1 B DMG. [Exchange] Misses grant +1 Armor and +1 Fate. *(Resource on miss)*
Common | Strength/Brutal | Spear of the Æsir | Melee | same as above

Upgrade Pool (10 C / 10 U / 10 R)
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Wisdom/Spiritual | Lightning Crash | Melee | 7 S DMG, -2 Hit. *(Heavy but inaccurate)*
Common | Wisdom/Spiritual | Hymn of Blades | Melee | [Combat] Your attacks deal +2 DMG. *(Offensive hymn)*
Common | Charisma/Divine | Favorable Winds | Melee | 1 D DMG. [Exchange] Reroll once each die that misses. *(Reliability)*
Common | Charisma/Divine | Skald’s Favor | Melee | Gain 2 Fate and 2 Armor. *(Resource boost)*
Common | Charisma/Divine | Hymn of Blood | Melee | [Combat] At end of Combat, HEAL 1 per active Hymn. *(Sustain)*
Common | Agility/Precise | Ward of the Fallen | Melee | 3 P DMG. [Combat] +1 Armor for each two dice that miss. *(Defensive synergy)*
Common | Agility/Precise | Spear Dive | Melee | 2 P DMG, +2 per Fate you pay. *(Spend Fate for damage)*
Common | Strength/Brutal | Tempestuous Finale | Melee | 3 B DMG, +2 per active Hymn. End all Hymns. *(Finisher)*
Common | Strength/Brutal | Piercer of Fates | Melee | 4 B DMG. If Fate ≤3 -1 Hit; if ≥8 +1 Hit. *(Fate threshold bonus)*
Uncommon | Wisdom/Spiritual | Hymn of Fate | Melee | [Combat] End of Exchange gain 1 Fate per active Hymn. *(Fate engine)*
Uncommon | Wisdom/Spiritual | Echoes of Gungnir | Melee | [Combat] +1 DMG per die missed in previous attack. *(Momentum)*
Uncommon | Wisdom/Spiritual | Overflowing Grace | Melee | [Combat] Fate beyond 10 converts to healing. *(Overflow heal)*
Uncommon | Charisma/Divine | Misfortune’s Muse | Melee | 4 D DMG. When you fully miss an attack, draw a card. *(Risk reward)*
Uncommon | Charisma/Divine | Tyr's Choice | Melee | 2 D DMG. Gain 2 Fate or 2 Armor. *(Flex)*
Uncommon | Agility/Precise | Chorus Throw | Ranged | 4 P DMG, +1 per active Hymn. *(Scaling ranged)*
Uncommon | Agility/Precise | Norn's Gambit | Melee | 4 P DMG. Take -X Hit (max -4) to gain twice to DMG. *(Trade accuracy)*
Uncommon | Strength/Brutal | Hymn of Thunder | Melee | [Combat] Your attacks gain +1 Hit. *(Accuracy hymn)*
Uncommon | Strength/Brutal | Triumphant Blow | Melee | 4 B DMG. If this defeats enemy, gain 2 Fate. *(Reward kill)*
Rare | Wisdom/Spiritual | Hymn of the All-Father | Melee | [Combat] End of Exchange gain 1 Armor plus 1 per active Hymn (max 4). *(Strong defense)*
Rare | Wisdom/Spiritual | Loki's Trickery | Melee | 3 S DMG. [Exchange] Hits after rerolling a miss deal +1 DMG. *(Reroll synergy)*
Rare | Wisdom/Spiritual | Ragnarok Call | Melee | 4 S DMG. [Exchange] Other attacks gain +2 DMG and -1 Hit. *(Boost next attacks)*
Rare | Charisma/Divine | Storm's Thunderlance | Ranged | 5 D DMG. +1 Hit per active Hymn. *(Finale)*
Rare | Charisma/Divine | Freyja's Command | Melee | 1 D DMG, +1 per Fate you have. *(Uses stored Fate)*
Rare | Agility/Precise | Meteor Skyfall | Melee | 7 P DMG to all enemies, -2 Hit. *(Area burst)*
Rare | Agility/Precise | Blessing of Balder | Melee | Pay X Fate: gain twice that Armor. *(Convert Fate to defense)*
Rare | Strength/Brutal | Storm's Rhyme Crash | Melee | 4 B DMG to all enemies, +2 per active Hymn you end. *(Consume Hymns for AoE)*
Rare | Strength/Brutal | The Fate-Severer | Melee | 3 B DMG, +3 per Fate paid. *(Big single target)*

### Musashi
Initial Deck
Rarity | Attr/Elem | Name | Type | Effect & Comment
---|---|---|---|---
Common | Agi/Precise | Swallow‑Cut | Melee | 1 P DMG, +2 if target is Vulnerable.
Common | Agi/Precise | Swallow‑Cut | Melee | same as above
Common | Agi/Precise | Cross‑River Strike | Melee | 2 P DMG to up to 2 melee enemies.
Common | Agi/Precise | Cross‑River Strike | Melee | same as above
Common | Str/Brutal | Heaven‑and‑Earth Slash | Melee | 2 B or 2 D DMG. *(Flexible element)*
Common | Str/Brutal | Heaven‑and‑Earth Slash | Melee | same as above
Common | Wis/Spiritual | Flowing Water Parry | Melee | 1 S DMG. 1 Armor. Resolve before Ranged attacks. *(Early defense)*
Common | Wis/Spiritual | Flowing Water Parry | Melee | same as above
Common | Cha/Divine | Dual‑Moon Guard | Melee | [Exchange] Gain Armor equal 1 + half total DMG dealt.
Common | Int/Arcane | Wind‑Reading Focus | Melee | 1 A DMG. Next attack may use any element.

Upgrades
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Agi/Precise | Battojutsu Strike | Melee | 2 P DMG, 2 Armor. Resolve before Ranged.
Common | Agi/Precise | Scroll-Cut Slash | Melee | 3 P DMG to up to 2 enemies.
Common | Str/Brutal | Chance-Seizing Blade | Melee | Pay 1 Fate: [Combat] DMG on Vulnerable enemies ×3 instead of ×2.
Common | Str/Brutal | Susanoo-Descent Cut | Melee | 3 B DMG, +1 per 2 Armor.
Common | Wis/Spiritual | Water-Mirror Split | Melee | Next single-target attack may target 2 enemies.
Common | Wis/Spiritual | Spirit-Cleaver | Melee | 2 S DMG. Next attack any Element.
Common | Cha/Divine | Iron-Will Guard | Ranged | 3 Armor or pay 1 Fate for 5.
Common | Cha/Divine | Ghost-Step Slash | Melee | 3 D DMG. If target dies this Exchange, repeat on a second enemy.
Common | Int/Arcane | Heavenly-Dragon Stance | Melee | 2 A DMG. [Exchange] Pick a played attack; all your attacks use its Element.
Uncommon | Agi/Precise | Seizing-Dragon Slice | Melee | 3 P DMG +4 if target Vulnerable.
Uncommon | Agi/Precise | Two-Heaven Blitz | Melee | 4 P DMG to up to 2 enemies.
Uncommon | Str/Brutal | Crescent-Moon Guard | Ranged | Pay 1 Fate: gain 2 Armor per other card played this Exchange.
Uncommon | Str/Brutal | Mountain-Strike Stance | Melee | [Combat] Enemies have -1 DEF if you attack their Vulnerability.
Uncommon | Wis/Spiritual | Mirror-Flow Style | Melee | [Combat] When exactly two enemies are present, your attacks gain +3 DMG.
Uncommon | Wis/Spiritual | Heaven-Defying Blade | Melee | [Combat] Gain 1 Fate when playing a card the enemy is Vulnerable to.
Uncommon | Cha/Divine | Ascending Vengeance | Melee | [Combat] Enemies lose 1 HP per 2 Armor their attack took from you.
Uncommon | Cha/Divine | Menacing Step | Melee | Remove an enemy from combat; move it to an adjacent location.
Uncommon | Int/Arcane | Iron-Shell Posture | Melee | [Combat] If your Armor fully blocks an enemy’s DMG, it loses 2 HP.
Rare | Agi/Precise | Final-Dragon Slash | Melee | 2 P DMG, +7 if target Vulnerable.
Rare | Agi/Precise | Five-Ring Convergence | Melee | 2 P DMG. [Combat] Pick a played attack; all your attacks use its Element.
Rare | Str/Brutal | The Wanderer's Blade | Melee | 2 B DMG. [Combat] Pick a played attack; all your attacks use its Element.
Rare | Str/Brutal | Formless Principle | Melee | [Combat] Your attacks have +1 DMG and +1 Hit.
Rare | Wis/Spiritual | Stone-Lotus Slash | Melee | 4 S DMG, +1 per Armor you have.
Rare | Wis/Spiritual | Twin-Dragon Descent | Melee | Choose 2 enemies. [Exchange] Next attack DMG on them hits both.
Rare | Cha/Divine | Edge of Harmony | Melee | 4 D DMG. Gain 3 Armor.
Rare | Cha/Divine | Two-Strikes as One | Melee | 3 D DMG to up to 2 enemies. If one dies, both die.
Rare | Int/Arcane | Moment of Perfection | Ranged | 4 Armor or pay 2 Fate to double current Armor.

### Merlin
Initial Deck
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Int/Arcane | Arcane Volley | Ranged | 1 A DMG to all enemies.
Common | Int/Arcane | Arcane Volley | Ranged | same as above
Common | Int/Arcane | Lady’s Warden | Melee | 1 A DMG. 2 Armor to you or an ally.
Common | Int/Arcane | Lady’s Warden | Melee | same as above
Common | Charisma/Divine | Weaver of Fate | Ranged | 1 D DMG. Reroll up to two dice this Exchange.
Common | Charisma/Divine | Weaver of Fate | Ranged | same as above
Common | Agility/Precise | Crystal Cave's Staff | Melee | 1 P DMG. [Combat] Gain 1 Armor per 7 or 8 rolled.
Common | Wisdom/Spiritual | Mists of Time | Ranged | 1 S DMG. [Exchange] Your dice numbers count as 1 higher (up to 8).
Common | Wisdom/Spiritual | Mists of Time | Ranged | same as above
Common | Wisdom/Spiritual | Circle of Avalon | Ranged | 1 S DMG. [Combat] You and allies can reroll 1 die from each attack.

Upgrades
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Int/Arcane | Runic Ray | Ranged | 2 A DMG to all enemies, +2 per card discarded.
Common | Int/Arcane | Crystal‑Shot Volley | Ranged | 3 A DMG. Any 8's give an extra die.
Common | Int/Arcane | Glyph-Marking Bolt | Ranged | 1 A DMG. [Combat] All attacks against target gain +1 die.
Common | Charisma/Divine | Voice of Destiny | Ranged | 3 D DMG. Reroll up to any 2 dice this Exchange.
Common | Charisma/Divine | Druidic Ways | Ranged | 2 D DMG. Heal you 1 or an ally 2.
Common | Agility/Precise | Protective Mists | Ranged | 1 Armor plus 1 per enemy.
Common | Agility/Precise | Mark of Fated Fall | Melee | 1 A DMG. [Combat] Target DEF -2.
Common | Wisdom/Spiritual | Veil‑Rain of Chaos | Ranged | X W DMG to all enemies (1 + number of enemies).
Common | Wisdom/Spiritual | Oracle of Avalon | Ranged | Gain 3 Fate.
Uncommon | Int/Arcane | Waves of Destiny | Ranged | 3 A DMG to all enemies. [Exchange] Gain 1 Fate per enemy that dies.
Uncommon | Int/Arcane | Ancestral Echoes | Ranged | 3 A DMG to all enemies. Each reroll can be applied twice.
Uncommon | Int/Arcane | Whispers of the Wyrd | Ranged | [Combat] +2 DMG to all attacks of one ally.
Uncommon | Charisma/Divine | Nature’s Rebuke | Ranged | 2 D DMG to all enemies. [Combat] Enemies dying heal 1 you or an ally.
Uncommon | Charisma/Divine | Guard from Beyond | Ranged | Ally gains 5 Armor. [Exchange] All enemies attack that ally.
Uncommon | Agility/Precise | Sage's Alacrity | Ranged | 2 P DMG. [Combat] Increase by 2 the number of all your rerolled dice.
Uncommon | Wisdom/Spiritual | Charged Spirits | Ranged | 2 S DMG to all enemies; +1 DMG per Fate spent (max +5).
Uncommon | Wisdom/Spiritual | Avalon's Light | Ranged | 3 S DMG. [Combat] Critical hits (8's) deal 4 DMG.
Uncommon | Wisdom/Spiritual | Spiritual Gifts | Ranged | 4 S DMG. You may discard 1 to allow an ally to gain 2 Fate and draw 1.
Rare | Int/Arcane | Rune Shatter | Ranged | 3 A DMG to all enemies. [Exchange] Enemies have -1 DEF.
Rare | Int/Arcane | Sigil of Final Fate | Ranged | [Combat] All dice rolls of 1 count as 8.
Rare | Int/Arcane | Conflux Lance | Ranged | 5 A DMG. Target has −2 DEF against this attack for each other hero in combat.
Rare | Charisma/Divine | Echoes of Guidance | Ranged | Choose one ally card to be executed an extra time this Exchange.
Rare | Agility/Precise | Mercury Guard | Ranged | [Combat] Gain 1 Armor per enemy once each Exchange.
Rare | Agility/Precise | Old-Ways Shillelagh | Melee | 3 P DMG. +1 Armor for each die that hits.
Rare | Wisdom/Spiritual | Favor of the Druids | Ranged | 1 S DMG. You and allies draw 1.
Rare | Wisdom/Spiritual | Chains of Morrígan | Ranged | [Exchange] Add +1 to each die result for every target its attack has.
Rare | Wisdom/Spiritual | Spirits of the Lands | Ranged | 4 S DMG. Gain 1 Fate for each other attack you played this Exchange.

### Hercules
Initial Deck
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Strength/Brutal | Pillar-Breaker Blow | Melee | 2 B DMG.
Common | Strength/Brutal | Pillar-Breaker Blow | Melee | same as above
Common | Strength/Brutal | Lion Strangler | Melee | 1 B DMG. [Combat] Enemy loses 1 HP per attack you resolve.
Common | Charisma/Divine | Demigodly Heroism | Melee | 1 D DMG. 1 Armor.
Common | Charisma/Divine | Demigodly Heroism | Melee | same as above
Common | Charisma/Divine | Sky Javelin | Ranged | 2 D DMG. [Exchange] +1 DMG to all your other attacks.
Common | Agility/Precise | Club Spin | Melee | 1 P DMG to all enemies.
Common | Agility/Precise | Club Spin | Melee | same as above
Common | Wisdom/Spiritual | Atlas Guard | Ranged | 3 Armor.
Common | Wisdom/Spiritual | Atlas Guard | Ranged | same as above

Upgrades
Rarity | Attribute/Element | Name | Type | Effect & Comment
---|---|---|---|---
Common | Strength/Brutal | Bondless Effort | Melee | 3 B DMG, plus 3 per card discarded.
Common | Strength/Brutal | Colossus Smash | Melee | 3 B DMG. 1 Armor.
Common | Charisma/Divine | Olympian Call | Melee | 1 D DMG. [Combat] You can reroll one die on each attack.
Common | Charisma/Divine | Divine Resilience | Melee | 1 D DMG. 1 Armor, plus 1 per enemy.
Common | Charisma/Divine | Horde Breaker | Melee | 2 D DMG. [Combat] Enemies dying makes others lose 2 HP.
Common | Agility/Precise | Disorienting Blow | Melee | 2 P DMG. [Exchange] Target has -3 Defense against your next card.
Common | Agility/Precise | Piercing Spear | Ranged | 2 P DMG. [Combat] Target has -1 DEF.
Common | Wisdom/Spiritual | Fated War | Melee | 2 S DMG to all enemies. Gain 1 Fate per enemy still in combat.
Common | Wisdom/Spiritual | Fortune's Throw | Ranged | 2 S DMG. 2 Armor or 2 Fate.
Uncommon | Strength/Brutal | Pain Strike | Melee | 4 B DMG. Pay X HP, gain +X B DMG (up to 6).
Uncommon | Strength/Brutal | Fortifying Attack | Melee | 1 Armor per 2 DMG done this Exchange to one target.
Uncommon | Strength/Brutal | Bone‑Splinter Whirl | Melee | 3 B DMG to all enemies. [Combat] Enemies have -1 DEF.
Uncommon | Charisma/Divine | Glorious Uproar | Melee | 1 D DMG to all enemies, +1 DMG per enemy.
Uncommon | Charisma/Divine | Guided By The Gods | Melee | 1 D DMG. [Combat] May reroll 1 die per attack.
Uncommon | Agility/Precise | Chiron's Training | Melee | 1 P DMG. [Combat] Gain 1 Armor per attack you play.
Uncommon | Agility/Precise | Once Isn't Enough | Melee | Execute twice the next attack card in this Exchange.
Uncommon | Wisdom/Spiritual | Strength from Anger | Melee | 1 S DMG. [Combat] +1 DMG to all your attacks.
Uncommon | Wisdom/Spiritual | Enduring Wave | Melee | 2 S DMG to all enemies. 2 Armor.
Rare | Strength/Brutal | Zeus' Wrath | Melee | 4 B DMG to all enemies.
Rare | Strength/Brutal | Ares' Will | Melee | 1 B DMG. [Combat] Enemy loses 2 HP per attack you resolve.
Rare | Strength/Brutal | True Might of Hercules | Melee | 8 B DMG if no other dice-rolling card played this Exchange.
Rare | Charisma/Divine | Athena's Guidance | Melee | Discard a card: [Combat] Double all DMG you do.
Rare | Charisma/Divine | Apollo's Sunburst | Ranged | 3 D DMG to all enemies, +3 per card discarded.
Rare | Charisma/Divine | Nike's Desire | Melee | 1 D DMG. Draw 1 or pay 1 Fate to draw 2.
Rare | Agility/Precise | Blessing of Hephaestus | Ranged | 5 Armor.
Rare | Agility/Precise | Hermes’ Delivery | Melee | 3 P DMG. Draw 1 card and play it as an Attack immediately.
Rare | Wisdom/Spiritual | Eris' Pandemonium | Melee | [Exchange] All your attacks deal +1 DMG per enemy in the combat.

## Enemy Lists
Basic Enemies and elite variants follow the design tables. Abilities include Web Slinger turning ranged attacks into melee, Disturbed Flow preventing rerolls, and others as specified earlier.

## Outstanding Features and Tasks
- Implement full hero card effects.
- Hymn bonuses and armor cap from Hymn of Shields.
- Hero-specific Fate thresholds.
- Temporary vulnerability applies to all targets.
- Element switching and early resolution mechanics.
- Limit global reroll to one per attack.
- Clear ephemeral-wings blocks on Gryphon death.
- Reset upgrade pools between runs.

### Development Task Sets
1. Brynhild Cards – Sets 1‑3
2. Musashi Cards – Sets 1‑3
3. Merlin Cards – Sets 1‑3
4. Hercules Cards – Sets 1‑3
5. Mechanics fixes listed above

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

=======
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
