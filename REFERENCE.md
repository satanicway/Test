Python Simulation Rules for Combat Balance Testing

Combat Setup

Heroes start each sequence of combats with full HP and an initial hand of 4 random basic cards from their base decks.

Monsters are selected based on the encounter sequence below.

Encounter Sequence

Combat against 1st random basic group.

After combat: gain 1 random upgrade card, add it to remaining hand.

Draw 3 cards.

Combat against 2nd random basic group.

After combat: gain 1 random upgrade card, add it to remaining hand.

Draw 3 cards.

Combat against 3rd random basic group.

After combat: gain 1 random upgrade card, add it to remaining hand.

Draw 3 cards.

Combat against 1st random ELITE group.

After combat: gain 1 random upgrade card, add it to remaining hand.

Draw 3 cards.

Combat against 2nd random ELITE group.

After combat: gain 1 random upgrade card, add it to remaining hand.

Draw 3 cards.

Combat against 3rd random ELITE group.

NO healing between combats.

Test ends after the 3rd Elite group.

Combat Exchange Loop

Each combat consists of exchanges until either the hero or all monsters are defeated.

Exchange Steps:

Step 1: Enemy Action Determination

Each enemy rolls a 1d8.

Determine enemy actions (Damage, Armor, special effects) from the roll.

Step 2: Hero Card Commitment

Hero selects cards from hand to commit:

Cards used normally (applying effects).

OR discard basic cards for 1 neutral DAMAGE or 1 ARMOR.

Fully commit each card against one villain unless AoE or multi-target is specified.

Hero focuses damage on the enemy rolling the highest damage first.

Step 3: Hero Attack Resolution

Ranged hero cards resolve first:

Target enemies, roll dice per card effect.

Apply damage immediately, deduct enemy HP.

Rolling an 8 deals 2 damage instead of 1.

Hero damage has a 20% chance to be doubled.

Defeated melee enemies do NOT deal damage.

Ranged enemies still act if defeated by melee attacks.

Melee hero cards resolve second:

Repeat damage resolution steps.

Step 4: Enemy Action Resolution

Ranged enemies (unless defeated by ranged heroes):

Apply previously determined damage/actions.

Melee enemies (if alive):

Apply previously determined damage/actions.

Enemy attacks target the hero, deducting Armor first.

Step 5: Card Draw

Hero draws after exchanges as:

After Exchange 1: 3 cards

After Exchange 2: 2 cards

After Exchange 3: 1 card

After Exchange 4+: 0 cards

Sequence resets each new combat.

Special Conditions

Armor (): Temporary HP, resets after each exchange.

Pierce (): Ignores hero Armor.

Disrupt (): Hero discards 1 card.

Shot (): Enemy attack counts as ranged.

Cancel (): Ends one active hero [Combat] or [Exchange] effect.

Handling Special Abilities

Apply each enemy's special abilities as described in their stat blocks.

End of Combat

Ends when either all enemies are defeated or hero HP ≤ 0.

Calculate XP awarded: (Total Monster XP / 2) + 1, rounded up.

Python Simulation Structure (Code Outline)

class Card:
    # Stores card info and effects

class Hero:
    hp: int
    hand: List[Card]
    armor: int
    deck: List[Card]

    def commit_cards():
        # Commit logic

    def apply_damage(damage):
        # Deduct armor then HP

    def draw_cards(exchange_number):
        # Draw based on exchange sequence

class Monster:
    hp: int
    defense: int
    type: str  # 'Ranged' or 'Melee'
    abilities: List[str]

    def roll_action():
        # Roll and determine damage/effects

class Combat:
    hero: Hero
    monsters: List[Monster]

    def run_combat():
        exchange_number = 1
        while hero.hp > 0 and monsters:
            for monster in monsters:
                monster.roll_action()

            hero.commit_cards()

            resolve_hero_attacks(hero, monsters)

            resolve_monster_attacks(monsters, hero)

            hero.draw_cards(exchange_number)

            exchange_number += 1
            # Remove defeated monsters

        return outcome, remaining_hero_hp, total_exchanges

# Loop through the sequence of combats as defined in Encounter Sequence
for encounter in encounter_sequence:
    combat = Combat(hero, encounter)
    outcome, hero_hp, exchanges = combat.run_combat()
    if hero_hp <= 0:
        break  # Test ends if hero defeated
    hero.hand.append(random_upgrade_card())
    hero.draw_cards(initial_draw=3)

Heroes and Villains

Include detailed implementations for each Hero (Hercules, Merlin) and each listed Monster (Shadow Spinner, Void Soldier, etc.), incorporating their special rules and card effects explicitly described in previous documentation.

MERLIN:

HP 15

INITIAL DECKCombat Side (top half)
RarityAttribute/ElementNameBasic UseTypeEffect
1CommonIntelligence/ArcaneArcane Volley1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged1 <A> <DMG> to all enemies.
2CommonIntelligence/ArcaneArcane Volley1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged1 <A> <DMG> to all enemies.
3CommonIntelligence/ArcaneLady’s Warden1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <A> <DMG>.
2 <ARMOR> to you or an ally."
4CommonIntelligence/ArcaneLady’s Warden1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <A> <DMG>.
2 <ARMOR> to you or an ally."
5CommonCharisma/DivineWeaver of Fate1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <D> <DMG>.
Reroll up to two dice in this Exchange."
6CommonCharisma/DivineWeaver of Fate1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <D> <DMG>.
Reroll up to two dice in this Exchange."
7CommonAgility/PreciseCrystal Cave's Staff1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <P> <DMG>.
[Combat] Gain 1 <ARMOR> per 7 or 8 rolled."
8CommonWisdom/SpiritualMists of Time1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <S> <DMG>.
[Exchange] Your dice numbers count as 1 higher (up to 8)."
9CommonWisdom/SpiritualMists of Time1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <S> <DMG>.
[Exchange] Your dice numbers count as 1 higher (up to 8)."
10CommonWisdom/SpiritualCircle of Avalon1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <S> <DMG>.
[Combat] You and allies can reroll 1 die from each attack."

Numero de cartas de upgrade: 10 rodadas, 20% rodadas extras = 12 rodadas, 1,25 upgrades por rodada (base+quests), 3 cartas por upgrade, 33% extra.
Raridade: Comuns 3 copias, Incomuns 2 copias, Raras 1 copia. 10 comuns, 10 incomuns, 10 raras
RarityAttribute/ElementNameTypeEffect
1CommonIntelligence/ArcaneRunic Ray1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged2 <A> <DMG> to all enemies, plus 2 per card you choose to DISCARD.
2CommonIntelligence/ArcaneCrystal‑Shot Volley1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <A> <DMG>.
Any 8's in this attack gives an extra dice (cumulative)."
3CommonIntelligence/ArcaneGlyph-Marking Bolt1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <A> <DMG>.
[Combat] All attacks against this target gain +1 dice."
4CommonCharisma/DivineVoice of Destiny1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <D> <DMG>.
Reroll up to any 2 dice on this Exchange."
5CommonCharisma/DivineDruidic Ways1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <D> <DMG>.
HEAL you 1, or 2 an ally."
6CommonAgility/PreciseProtective Mists1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged1 <ARMOR>, plus 1 for each enemy.
7CommonAgility/PreciseMark of Fated Fall1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <A> <DMG>.
[Combat] Target <DEF> is reduced by 2."
8CommonWisdom/SpiritualVeil‑Rain of Chaos1 <CARTA>: 1 <DMG> or 1 <ARMOR>RangedX <W> <DMG> to all enemies. X is 1 plus the number of enemies in Combat.
9CommonWisdom/SpiritualOracle of Avalon1 <CARTA>: 1 <DMG> or 1 <ARMOR>RangedGain 3 <FATE>.
10UncommonIntelligence/ArcaneWaves of Destiny1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <A> <DMG> to all enemies.
[Exchange] Gain 1 <FATE> per enemy that dies."
11UncommonIntelligence/ArcaneAncestral Echoes1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <A> <DMG> to all enemies.
Each reroll in this attack can be applied twice.   "
12UncommonIntelligence/ArcaneWhispers of the Wyrd1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged[Combat] +2 <DMG> to all attacks of one ally.
13UncommonCharisma/DivineNature’s Rebuke1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <D> <DMG> to all enemies.
[Combat] Enemies dying HEAL 1 you or ally."
14UncommonCharisma/DivineGuard from Beyond1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"Ally gains 5 <ARMOR>.
[Exchange] All enemies attack that ally."
15UncommonAgility/PreciseSage's Alacrity1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <P> <DMG>.
[Combat] Increase by 2 the number of all your rerolled dice."
16UncommonWisdom/SpiritualCharged Spirits1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged2 <S> <DMG> to all enemies; +1 <DMG> per <FATE> you choose to spent (max +5).
17UncommonWisdom/SpiritualAvalon's Light1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <S> <DMG>.
[Combat] Your critical hits (8's) deal 4 <DMG>."
18UncommonWisdom/SpiritualSpiritual Gifts1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"4 <S> <DMG>.
You may DISCARD 1 to allow an ally to gain 2 <Fate> and DRAW 1."
19RareIntelligence/ArcaneRune Shatter1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"3 <A> <DMG> to all enemies.
[Exchange] Enemies have -1 <DEF>."
20RareIntelligence/ArcaneSigil of Final Fate1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged[Combat] All dice rolls of 1's counts as 8's.
21RareIntelligence/ArcaneConflux Lance1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"5 <A> <DMG>.
Target has −2 <DEF> against this Attack for each other hero in this combat."
22RareCharisma/DivineEchoes of Guidance1 <CARTA>: 1 <DMG> or 1 <ARMOR>RangedChoose one ally card to be executed an extra time this Exchange.
23RareAgility/PreciseMercury Guard1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged[Combat] Gain 1 <ARMOR> per enemy in combat, once on each Exchange.
24RareAgility/PreciseOld-Ways Shillelagh1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"3 <P> <DMG>.
+1 <Armor> for each dice that hits."
25RareWisdom/SpiritualFavor of the Druids1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"1 <S> <DMG>.
You and allies DRAW 1."
26RareWisdom/SpiritualChains of Morrígan1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged[Exchange] Add +1 to each die result for every target its attack has.
27RareWisdom/SpiritualSpirits of the Lands1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"4 <S> <DMG>.
Gain 1 <Fate> for each other attack you played this Exchange."

HERCULES

HP 25

INITIAL DECKCombat Side (top half)
RarityAttribute/ElementNameBasic UseTypeEffect
1CommonStrength/BrutalPillar-Breaker Blow1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee2 <B> <DMG>.
2CommonStrength/BrutalPillar-Breaker Blow1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee2 <B> <DMG>.
3CommonStrength/BrutalLion Strangler1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <B> <DMG>.
[Combat] Enemy loses 1 <HP> per attack you resolve."
4CommonCharisma/DivineDemigodly Heroism1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <D> <DMG>.
1 <ARMOR>."
5CommonCharisma/DivineDemigodly Heroism1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <D> <DMG>.
1 <ARMOR>."
6CommonCharisma/DivineSky Javelin1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <D> <DMG>.
[Exchange] +1 <DMG> to all your other attacks."
7CommonAgility/PreciseClub Spin1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee1 <P> <DMG> to all enemies.
8CommonAgility/PreciseClub Spin1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee1 <P> <DMG> to all enemies.
9CommonWisdom/SpiritualAtlas Guard1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged3 <ARMOR>
10CommonWisdom/SpiritualAtlas Guard1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged3 <ARMOR>

Numero de cartas de upgrade: 10 rodadas, 20% rodadas extras = 12 rodadas, 1,25 upgrades por rodada (base+quests), 3 cartas por upgrade, 33% extra.
Raridade: Comuns 3 copias, Incomuns 2 copias, Raras 1 copia. 10 comuns, 10 incomuns, 10 raras
RarityAttribute/ElementNameTypeEffect
1CommonStrength/BrutalBondless Effort1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee3 <B> <DMG>, plus 3 per card you choose to DISCARD.
2CommonStrength/BrutalColossus Smash1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"3 <B>.
1 <ARMOR>."
3CommonCharisma/DivineOlympian Call1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <D> <DMG>.
[Combat] You can reroll one die on each attack."
4CommonCharisma/DivineDivine Resilience1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <D> <DMG>.
1 <ARMOR>, plus 1 per enemy."
5CommonCharisma/DivineHorde Breaker1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"2 <D> <DMG>.
[Combat] Enemies dying makes others lose 2 <HP>."
6CommonAgility/PreciseDisorienting Blow1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"2 <P> <DMG>.
[Exchange] Target has -3 Defense against your next card."
7CommonAgility/PrecisePiercing Spear1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <P> <DMG>.
[Combat] Target has -1 <DEF>."
8CommonWisdom/SpiritualFated War1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"2 <S> <DMG> to all enemies.
Gain 1 {FATE} per enemy still in combat."
9CommonWisdom/SpiritualFortune's Throw1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged"2 <S> <DMG>.
2 <ARMOR> or 2 <FATE>."
10UncommonStrength/BrutalPain Strike1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"4 <B> <DMG>.
Pay X <HP>, gain +X <B> <DMG> (up to 6)."
11UncommonStrength/BrutalFortifying Attack1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee1 <ARMOR> per 2 <DMG> done this Exchange to one target (total <DMG>.)
12UncommonStrength/BrutalBone‑Splinter Whirl1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"3 <B> <DMG> to all enemies.
[Combat] Enemies have -1 <DEF>."
13UncommonCharisma/DivineGlorious Uproar1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee1 <D> <DMG> to all enemies, +1 <DMG> per enemy in combat
14UncommonCharisma/DivineGuided By The Gods1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"2 <D> <DMG>.
[Combat] May reroll 1 die per attack."
15UncommonAgility/PreciseChiron's Training1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <P> <DMG>.
[Combat] Gain 1 <Armor> per attack you play."
16UncommonAgility/PreciseOnce Isn't Enough1 <CARTA>: 1 <DMG> or 1 <ARMOR>MeleeExecute twice the next attack card in this Exchange.
17UncommonWisdom/SpiritualStrength from Anger1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <S> <DMG>.
[Combat] +1 <DMG> to all your attacks."
18UncommonWisdom/SpiritualEnduring Wave1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"2 <S> <DMG> to all enemies.
2 <Armor>."
19RareStrength/BrutalZeus' Wrath1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee4 <B> <DMG> to all enemies.
20RareStrength/BrutalAres' Will1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <B> <DMG>.
[Combat] Enemy loses 2 <HP> per attack you resolve."
21RareStrength/BrutalTrue Might of Hercules1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"8 <B> <DMG>.
If you played no other card that rolls dice in this Exchange."
22RareCharisma/DivineAthena's Guidance1 <CARTA>: 1 <DMG> or 1 <ARMOR>MeleeDiscard a card to gain: [Combat] Double all <DMG> you do.
23RareCharisma/DivineApollo's Sunburst1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged3 <D> <DMG> to all enemies, plus 3 per card you choose to DISCARD.
24RareCharisma/DivineNike's Desire1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"1 <D> <DMG>.
DRAW 1, or pay 1 <FATE> to DRAW 2."
25RareAgility/PreciseBlessing of Hephaestus1 <CARTA>: 1 <DMG> or 1 <ARMOR>Ranged5 <ARMOR>.
26RareAgility/PreciseHermes’ Delivery1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee"3 <P> <DMG>.
DRAW 1 card and play it as an Attack immediately."
27RareWisdom/SpiritualEris' Pandemonium1 <CARTA>: 1 <DMG> or 1 <ARMOR>Melee[Exchange] All your attacks deal +1 <DMG> per enemy in the combat.

MONSTERS:

BASIC ENEMIESXPSpawn Qnt.VulnerabilityHPDefenseType1-23-45-67-8Ability
Shadow Spinner43 (A)Spiritual <S>14Melee-2 <A>1 <D> 2 <A>2 <D> <P>Web Slinger: Ranged attacks are considered Melee.
Shadow Spinner43 (B)Spiritual <S>14Melee-2 <A>1 <D> 2 <A>2 <D> <P>Web Slinger: Ranged attacks are considered Melee.
Void Soldier43 (C)Precise <P>35Melee-1 <A>1 <D>2 <D> 1 <A>Dark Phalanx: Soldiers take -1 <D> (min. 1) from multi-target attacks, if at least 2 Soldiers are alive.
Void Soldier43 (D)Precise <P>35Melee-1 <A>1 <D>2 <D> 1 <A>Dark Phalanx: Soldiers take -1 <D> (min. 1) from multi target attacks, if at least 2 Soldiers are alive.
Priest of Oblivion33 (A)Arcane <A>23Ranged<DR>0 <D>1 <D>1 <D>Power of Death: Priests (on 3+) deal +1 <D> for each dead Priest in this combat.
Priest of Oblivion33 (B)Arcane <A>23Ranged<DR>0 <D>1 <D>1 <D>Power of Death: Priests (on 3+) deal +1 <D> for each dead Priest in this combat.
Corrupted Dryad53 (C)Brutal <B>34Melee-1 <A>1 <D> <S>2 <D>Cursed Thorns: Unused <ARMOR> at end of Exchange cause hero to lose that amount of <HP>.
Corrupted Dryad53 (D)Brutal <B>34Melee-1 <A>1 <D> <S>2 <D>Cursed Thorns: Unused <ARMOR> at end of Exchange cause hero to lose that amount of <HP>.

Dark Minotaur52 (A)Precise <P>53Melee1 <A>1 <D>1 <D> <P>2 <D>Cleaving and Stomping: Minotaurs deals <D> to each hero in battle.
Dark Minotaur52 (B)Precise <P>53Melee1 <A>1 <D>1 <D> <P>2 <D>Cleaving and Stomping: Minotaurs deals <D> to each hero in battle.
Dark Wizard42 (C)Brutal <B>43Ranged<C>1 <D>1 <D> 1 <A>2 <D>Curse of Torment: Hero takes 1 <DMG> whenever it rolls a 1 or 2 (after rerolls).
Dark Wizard2 (D)Brutal <B>43Ranged<C>1 <D>1 <D> 1 <A>2 <D>Curse of Torment: Hero takes 1 <DMG> whenever it rolls a 1 or 2 (after rerolls).
Shadow Banshee42 (A)Divine <D>45Melee3 <A><DR>1 <D>1 <D>Ghostly: Start of 4th Exchange, end combat without resolution. MOVE Banshees to the next letter Location in this tile.
Shadow Banshee42 (B)Divine <D>45Melee3 <A><DR>1 <D>1 <D>Ghostly: Start of 4th Exchange, end combat without resolution. MOVE Banshees to the next letter Location in this tile.

Void Gryphon51 (C)Spiritual <S>55Melee-1 <D> 1 <A>2 <D> 2 <A>3 <D> <P>Aerial Combat: Melee Attacks have -1 to <Hit> the Gryphon.
Void Gryphon51 (D)Spiritual <S>55Melee-1 <D> 1 <A>2 <D> 2 <A>3 <D> <P>Aerial Combat: Melee Attacks have -1 to <Hit> the Gryphon.
Void Treant61 (A)Divine <D>76Melee3 <A>1 <D> 1 <A>1 <D> 1 <A>4 <D>Power Sap: End of each Exchange, end 1 Combat effect. If it does, HEAL 1 the Treant.
Void Treant61 (B)Divine <D>76Melee3 <A>1 <D> 1 <A>1 <D> 1 <A>4 <D>Power Sap: End of each Exchange, end 1 Combat effect. If it does, HEAL 1 the Treant.
Corrupted Angel51 (C)Arcane <A>65Melee-1 <D> <P>2 <D> <S>3 <D> 2 <A>Corrupted Destiny: Start of each Exchange, the hero loses 2 <Fate>.
Corrupted Angel51 (D)Arcane <A>65Melee-1 <D> <P>2 <D> <S>3 <D> 2 <A>Corrupted Destiny: Start of each Exchange, the hero loses 2 <Fate>.

ELITE ENEMIESSpawn Qnt.VulnerabilityHPDefenseDamage
Shadow Spinner63 (A)Spiritual <S>35-2 <A>2 <D> 2 <A>3 <D> <P>Sticky Web: Heroes DRAW -1 card on each Exchange draws.
Shadow Spinner63 (B)Spiritual <S>35-2 <A>2 <D> 2 <A>3 <D> <P>Sticky Web: Heroes DRAW -1 card on each Exchange draws.
Void Soldier63 (C)Precise <P>461 <D>1 <D> 1 <A>1 <D>3 <D> 1 <A>Spiked Armor: Whenever a single attack deals 3+ <DMG> against a Soldier, the hero loses 1 <HP>.
Void Soldier63 (D)Precise <P>461 <D>1 <D> 1 <A>1 <D>3 <D> 1 <A>Spiked Armor: Whenever a single attack deals 3+ <DMG> against a Soldier, the hero loses 1 <HP>.
Priest of Oblivion53 (A)Arcane <A>44<DR>1 <D>1 <D> 1 <A>2 <D>Silence: No Combat or Exchange cards apply their effects.
Priest of Oblivion53 (B)Arcane <A>44<DR>1 <D>1 <D> 1 <A>2 <D>Silence: No Combat or Exchange cards apply their effects.
Corrupted Dryad73 (C)Brutal <B>45-1 <A>2 <D> <S>3 <D>Disturbed Flow: Dice can't be rerolled in this combat.
Corrupted Dryad73 (D)Brutal <B>45-1 <A>2 <D> <S>3 <D>Disturbed Flow: Dice can't be rerolled in this combat.
Dark Minotaur72 (A)Precise <P>63-2 <A>2 <D> <P>3 <D>Enrage: When at 3 <HP> or less, the Minotaur attacks twice.
Dark Minotaur72 (B)Precise <P>63-2 <A>2 <D> <P>3 <D>Enrage: When at 3 <HP> or less, the Minotaur attacks twice.
Dark Wizard62 (C)Brutal <B>34<C>1 <D>1 <D> 1 <P>3 <D>Void Barrier: A Dark Wizard that takes <D> can only take <D> of that same type on that Exchange (reduce other <D> to 0).
Dark Wizard62 (D)Brutal <B>34<C>1 <D>1 <D> 1 <P>3 <D>Void Barrier: A Dark Wizard that takes <D> can only take <D> of that same type on that Exchange (reduce other <D> to 0).
Shadow Banshee62 (A)Divine <D>55-2 <A> <DR>1 <D>2 <D> <P>Banshee Wail: Deal 1 <DMG> to all heroes in this Combat for each 3 dice rolled against a Banshee in the Exchange (rounded down).
Shadow Banshee62 (B)Divine <D>55-2 <A> <DR>1 <D>2 <D> <P>Banshee Wail: Deal 1 <DMG> to all heroes in this Combat for each 3 dice rolled against a Banshee in the Exchange (rounded down).
Void Gryphon71 (C)Spiritual <S>65-2 <D> 3 <A>3 <D> 1 <A>4 <D> <P>Ephemeral Wings: After you deal <DMG> to the Gryphon, your next card in the Exchange deals no <DMG> to it.
Void Gryphon71 (D)Spiritual <S>65-2 <D> 3 <A>3 <D> 1 <A>4 <D> <P>Ephemeral Wings: After you deal <DMG> to the Gryphon, your next card in the Exchange deals no <DMG> to it.
Void Treant81 (A)Divine <D>874 <A>2 <D> 2 <A>2 <D> 2 <A>5 <D>Roots of Despair: Whenever a hero miss all dice on an attack card, it loses 1 <HP>.
Void Treant81 (B)Divine <D>874 <A>2 <D> 2 <A>2 <D> 2 <A>5 <D>Roots of Despair: Whenever a hero miss all dice on an attack card, it loses 1 <HP>.
Corrupted Angel71 (C)Arcane <A>76<C>2 <D> <P>3 <D> <S>5 <D>Denied Heaven: Reroll all dice whose face is 8 (as many times as necessary).
Corrupted Angel71 (D)Arcane <A>76<C>2 <D> <P>3 <D> <S>5 <D>Denied Heaven: Reroll all dice whose face is 8 (as many times as necessary).

<P>: Pierce - Ignore Armor.
<DR>: Disrupt - Discard 1 Card.
<S>: Shot - Gain Ranged for this attack.
<C>: Cancel - End 1 <Combat> or <Exchange> effect.

Addendum to Python Simulation Rules for Combat Balance Testing:

Deck and Hand Management:

Cards used during combat move to the discard pile. The discard pile reshuffles into the deck only when the hero tries to draw a card but the deck is empty. The hero's hand remains intact during reshuffling.

The initial deck consists of exactly the 10 basic (initial) cards. All other cards with defined rarities (common, uncommon, rare) are considered upgrade cards.

Maximum hand size is 7. If a draw would exceed this, the hero draws and then discards one card, prioritizing discarding basic cards over upgraded ones.

Monster Spawn Mechanics:

Monster groups are selected completely at random from the provided possibilities.

"Spawn Qnt.: 3 (A)" means exactly 3 identical monsters spawn as separate, individually targetable entities. The letter in parentheses is to be ignored.

Each monster individually rolls 1d8 at the start of each exchange to determine its actions.

Monster Armor and Attacks:

Monster damage is directly determined by their rolled band without needing to roll to hit.

Monster armor gained from dice bands is temporary and resets at the end of each exchange.

All monsters always target the single hero present.

Card Effects and Decisions:

[Combat] effects persist until the end of the combat.

[Exchange] effects persist only for the current exchange.

There is no limit to how many effects can stack.

Effects mentioning "ally" are ignored. The simulation assumes solo combat.

When prompted by card effects to discard cards or use Fate:

Always discard the two weakest available cards (prioritize discarding basic cards).

Always attempt to spend up to 2 Fate.

Any other decision the AI must make randomly from valid options.

Armor, Damage, and Dice Mechanics:

Hero armor always resets entirely at the end of each exchange and combat.

Hero damage has a 20% chance of doubling, applied separately per die rolled.

Dice success criteria:

A roll equal to or greater than the enemy's Defense = 1 damage.

An exact roll of 8 = 2 damage instead.

Modifiers do not affect the critical 8 result.

Upgrade Card Selection:

Draw 3 random upgrade cards, considering rarity (common: uncommon: rare = 3:2:1). Keep the card of highest rarity among the three drawn.

Selected upgrade cards permanently enter the hero's deck for the remainder of the simulation.

Fate Mechanics:

Hero gains 1 Fate before each combat.

Fate is spent exclusively to reroll missed dice:

Always spend Fate if rerolling could defeat an enemy with 1 or 2 HP remaining.

Spend up to 2 Fate if multiple dice meet this criterion.

Fate persists between combats.

Special Enemy Abilities:

"Disrupt": Hero discards immediately when the damage is applied.

"Shot": Enemy attacks immediately count as ranged.

"Cancel": Ends hero's active effect immediately upon enemy damage application.

"Pierce": Immediately ignores the hero's Armor upon damage application.

All special monster abilities are passive and trigger automatically when conditions are met.

Combat Transitions:

Between combats:

Fate is retained.

All temporary effects, Armor, and temporary HP reset.

Hero HP does not recover.

XP and Leveling:

XP calculations are ignored for the simulation's purposes.
