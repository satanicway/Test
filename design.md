Dark-Souls-style tension on a tabletop demands (1) perfectly telegraphed threats, (2) player-driven risk management, and (3) no swingy dice undermining mastery. Below is a concise game-design document that turns Idea 1 – “Stamina & Timing Card Combat” into a full prototype: a Samurai hero deck plus two deterministic enemy decks (Oni & Samurai), complete dodge/parry logic, and a hand-cycling system that eliminates draw luck while still rewarding tight play.

1 Core Loop (one round)
PhaseWhat happensWhy it’s skill-based
1 Boss TelegraphFlip the next card of the open Enemy Pattern Deck → shows attack type, speed, damage, area.Players always know exactly what’s coming; no random move selection (KDM’s predictable AI inspires this) kingdomdeath.wiki
2 Target RollDraw a target token (A/B/C/D) that corresponds to heroes’ initiative order. Only randomness in the system.Keeps everyone alert; prevents one hero perma-tanking without adding combat luck.
3 Hero ReactionAll heroes simultaneously pick 1 card from hand (Attack, Dodge, Parry, Block or Utility) and pay its Stamina cost.Mirrors Bloodborne BG’s speed-slot duels reddit.com reddit.com
4 ResolutionCompare card speed vs. attack speed → fast card resolves first, then slower. No hit rolls; effects are deterministic.“If you chose the right tool, you succeed 100 % of the time” – a core Souls principle reddit.com wired.com
5 Cooldown & DrawPlayed hero cards go to a personal cooldown row (2 turns). Re-fill hand from top of ordered personal deck until you hold 4 cards.No shuffle → players can track when each card returns, abolishing draw luck and rewarding memory (City of Kings puzzle ethos) thefriendlyboardgamer.wordpress.com

2 Dodge & Parry Mechanics
ActionSpeedCostEffectSkill Gate
Dodge3 (fast)1 StaminaIf speed ≥ attack speed and you move out of the danger arc, you take 0 damage.Requires reading telegraph and occupying a safe adjacent hex (positional skill).
Parry2 (medium)2 StaminaMust match attack’s exact speed (listed on boss card). Success = 0 dmg and your next Heavy gains +2 dmg. Failure (speed mismatch or wrong timing) = full damage taken.Higher reward but stricter window, echoing Souls’ high-risk parry design gamefaqs.gamespot.com game-wisdom.com

Why it works: Dodge is forgiving but burns fewer resources; Parry is potent but punishable, matching discussions on balancing parry vs. dodge in board-game adaptations reddit.com.

3 Hand-Management: Zero Draw Luck
Personal deck = 12 cards in a fixed order you choose during prep.

You always see your top 4; after play, used cards slide to a 2-step cooldown track, then return to the bottom.

Because order never changes, veterans count turns to line up perfect combos, just like planning stamina bursts in Dark Souls reddit.com.

Skill delta: Beginners react with what’s visible; experts preload their deck so key Dodges return on turns 3 & 6 when the Oni’s big swings land, achieving true no-hit runs.

4 Example Samurai Hero Deck (12 cards)
#Card NameTypeSpeedStaminaExtra Rule
1Iaijutsu CutLight Atk31+1 dmg if you were un-targeted this round.
2RiposteParry22Next Heavy +2 dmg.
3Cross-StepDodge31Move 1 before resolving.
4Twin StrikesLight Atk21Chain: you may immediately play card #6 at 0 Stamina.
5Great KesaHeavy Atk135 dmg; unusable if Stamina ≤ 2.
6Draw CutLight Atk31Counts as Parry if resolving before an attack.
7Guarded StanceBlock11Reduce next hit by 2.
8Ki FocusUtility—0Refresh 1 cooldown slot.
9Shadow StepDodge31Teleport to any adjacent back-hex.
10FlourishLight Atk21Pull aggro: you become priority target next round.
11Zen RecoveryUtility—0Gain 1 Stamina; skip attack.
12Crescent MoonHeavy Atk134 dmg in 180° front arc.

Design Note: Total Stamina = 6. Even with a single action each round, enemies like the Oni can drain your meter and certain cards chain into extra plays. Spending both Heavy Attacks back‑to‑back may leave too little Stamina to Parry or Dodge after a drain, capturing the feel of Souls fatigue reddit.com reddit.com.

5 Enemy Pattern Decks (6 cards each, looped; no shuffle mid-fight)
Oni (Oversized Club, Range 2)
OrderAttackSpeedDmgAreaTarget Logic
1Club Sweep2490° front arcRandom hero in arc
2Leap Crush16Impact hex + adj.Farthest hero ≤ 3
3Rage Roar30GlobalAll heroes lose 1 Stamina
4Double Swipe23×2180° front arcTwo random heroes hit once
5Overhead Smash18Single hexRandom hero ≤ 1
6Recuperate———Oni gains +1 dmg next card

Samurai Enemy (Katana Master, Duelist)
OrderAttackSpeedDmgAreaTarget Logic
1Iaido Draw34SingleHero with most HP
2Feint & Thrust23SingleRandom hero ≤ 2
3Whirlwind Slashes22Adjacent hexesAll adjacent heroes
4Parry Counter30SelfGains “next attack +4 dmg”
5Rising Strike16SingleTarget from Parry buff
6Focused Stare———Switch stance → restart at 1

Both decks guarantee learnable loops; mastering when the 8-damage Smash or 6-damage Rising Strike lands lets experts finish fights unscathed, reflecting KDM’s pattern learning but without AI shuffling randomness reddit.com kingdomdeath.wiki.

6 Why Skilled Play Shines
Predictive Deck Cycle – players know exactly when key cards return, rewarding foresight (lesson from controlled modifier decks in Gloomhaven) reddit.com.

Hard Windows – parry demands a perfect speed match; dodge demands correct arc exit. Errors are punished with 6–8 dmg hits; success = 0 dmg.

Stamina Discipline – Stamina fully refreshes each round during cooldown, but reckless heavy‑attack spam can still leave you unable to play key reactions if the meter is drained by enemy effects (e.g., Rage Roar) or by chaining multiple cards in one turn. This mirrors Souls attrition despite the per‑round reset.

Resource Compression Under Pressure – Oni’s Rage Roar drains Stamina globally, emulating Dark Souls’ stamina tax on blocking; only teams that manage resources stay alive.

Optional Grind Path – players may replay easier rooms for Lore to upgrade Stamina or learn weapon techniques, but flawless teams can clear bosses at tier 1.

7 GDD Snapshot (one page)
Overview
Title: Blades of Desolation
Players: 1-4 Samurai, fully cooperative.
Goal: Battle through domains of corrupt spirits, culminating in a climactic boss each session.

Components
Hero Decks (12 cards each, deterministic order)

Enemy Pattern Decks (6 cards per boss, fixed order)

Stamina Dials (0-6)

Cooldown Boards (two-slot track)

Target Tokens (A/B/C/D) for random hero selection.

Turn Structure
1. Reveal enemy card (telegraph).
2. Draw Target token.
3. Heroes simultaneously select & play 1 action.
4. Resolve by speed (fast → slow).
5. Move hero cards to cooldown; refresh Stamina back to its maximum; draw to 4.
6. Advance enemy deck (loop).

Key Systems
Stamina & Cooldown → forces pacing like Souls endurance.

Speed Clash → deterministic resolution; parry/dodge windows.

Pattern Recognition → bosses loop, enabling mastery.

Minimal RNG → only Target token adds uncertainty (per requirement).

Progression
Optional side rooms grant Lore → spend to add Stamina pip or swap cards between sessions. Grinding is helpful but never mandatory.
