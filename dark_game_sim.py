import random
import sys
import heapq
from collections import defaultdict, deque, Counter
from itertools import permutations

# ───────────── TUNABLE CONSTANTS ─────────────
HERO_SPEED   = 2
ROUND_SPAWNS = [0,2,2,2,3,3,3,4,4,4]
TOTAL_ROUNDS = 9
RUNS         = 2500
# ──────────────────────────────────────────────

# ---------------- Graph ----------------
G = {
    1:[3],2:[3,6],3:[1,2,4,5,36],4:[3,5,31],5:[3,4],
    6:[2,7,11],7:[6],8:[9],9:[8,10,11,12,14],10:[9],
    11:[6,9,33],12:[9,33],13:[14,18,34],14:[9,13,15],
    15:[14,16],16:[15],17:[18,20],18:[13,17],19:[20,34],
    20:[17,19,21],21:[20,22,35],22:[21,23],23:[22],
    24:[25],25:[24,26],26:[25,27,35],27:[26,28,32],
    28:[27,30],29:[30],30:[28,29,31],31:[4,30,32],
    32:[27,31,36],33:[11,12,36],34:[13,19,36],
    35:[21,26,36],36:[3,32,33,34,35]
}
ALL, CENTRE, H = list(G), 36, 4

# ────────────── Clusters ──────────────
CLUSTERS = {
    'A':[32,33,34,36],'B':[2,7,6,11],'C':[8,9,10,12],
    'D':[13,14,15,16],'E':[17,18,19,20],'F':[21,22,23,35],
    'G':[24,25,26,27],'H':[28,29,30,31],'I':[1,3,4,5]
}
CLUSTER_MAJOR = {
    'B':6,'C':9,'D':13,'E':17,
    'F':22,'G':25,'H':30,'I':1
}
CLUSTER_ADJ = {
    'B':['I','C'],'C':['B','D'],'D':['C','E'],'E':['D','F'],
    'F':['E','G'],'G':['F','H'],'H':['G','I'],'I':['H','B']
}
NODE_TO_CLUSTER = {n:cl for cl,nodes in CLUSTERS.items() for n in nodes}
MAJORS = list(CLUSTER_MAJOR.values())

# ───────── BFS (unweighted) ─────────
def shortest(a, b):
    if a == b:
        return [a]
    dq, par = deque([a]), {a: None}
    while dq:
        u = dq.popleft()
        for v in G[u]:
            if v not in par:
                par[v] = u
                dq.append(v)
                if v == b:
                    path = [v]
                    while par[v] is not None:
                        v = par[v]
                        path.append(v)
                    return path[::-1]


def dist(a, b):
    return len(shortest(a, b)) - 1

# ───────── Dijkstra (darkness-weighted) ─────────
def dijkstra(start):
    dm = {n: float('inf') for n in ALL}
    prev = {}
    dm[start] = 0
    pq = [(0, start)]
    while pq:
        cd, u = heapq.heappop(pq)
        if cd > dm[u]:
            continue
        for v in G[u]:
            cost = 2 if dark_map[NODE_TO_CLUSTER[v]] else 1
            nd = cd + cost
            if nd < dm[v]:
                dm[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dm, prev


def reconstruct_path(prev, goal):
    path = []
    u = goal
    while u in prev:
        path.append(u)
        u = prev[u]
    path.append(u)
    return path[::-1]

# ───────── Spots & spawn ─────────
class Spot:
    __slots__ = ('t', 'hp')

    def __init__(self, t):
        self.t = t
        self.hp = 2 if t == 'Q' else 1

    def __repr__(self):
        return self.t


def initial_spawn(board):
    free = [n for n in ALL if n != CENTRE]
    picks = random.sample(free, 5)
    for loc in picks[:2]:
        board[loc].append(Spot('R'))
    for loc in picks[2:4]:
        board[loc].append(Spot('M'))
    board[picks[4]].append(Spot('Q'))


def spawn_spots(k):
    global board
    free = [n for n in ALL if n != CENTRE and not board.get(n)]
    for loc in random.sample(free, min(k, len(free))):
        r = random.random()
        if r < 0.3:
            t = 'R'
        elif r < 0.8:
            t = 'M'
        else:
            t = 'Q'
        board[loc].append(Spot(t))

# ───────── Darkness helpers ─────────
def place_initial_dark(verbose=False):
    for cl in random.sample(list(CLUSTER_MAJOR.keys()), 2):
        dark_map[cl] = True
        if verbose:
            print(f"    Initial dark at major {CLUSTER_MAJOR[cl]} ({cl})")


def end_of_round_darkness(rnd, verbose=False):
    if rnd <= 3:
        k = 1
    elif rnd <= 6:
        k = 1 + (random.random() < 0.5)
    elif rnd <= 8:
        k = 2
    else:
        k = 0

    placed = 0
    prim = list(CLUSTER_MAJOR.keys())
    random.shuffle(prim)
    for cl in prim:
        if placed >= k:
            break
        if not dark_map[cl]:
            dark_map[cl] = True
            placed += 1
            if verbose:
                print(f"    Placed dark at {CLUSTER_MAJOR[cl]} ({cl})")
        else:
            for nbr in CLUSTER_ADJ[cl]:
                if placed >= k:
                    break
                if not dark_map[nbr]:
                    dark_map[nbr] = True
                    placed += 1
                    if verbose:
                        print(f"    Spread dark to {CLUSTER_MAJOR[nbr]} ({nbr})")
    if placed < k:
        for cl in prim:
            if placed >= k:
                break
            if not dark_map[cl]:
                dark_map[cl] = True
                placed += 1
                if verbose:
                    print(f"    Filled dark at {CLUSTER_MAJOR[cl]} ({cl})")

# ───────── One game ─────────
board = None
dark_map = None

def play_game(verbose=False, return_loss_detail=False):
    global board, dark_map
    heroes = [CENTRE] * H
    board = defaultdict(list)
    dark_map = {c: False for c in CLUSTERS}

    full_loss = False
    doom = 0
    lost_hero = [0] * H
    lost_round = [[0] * H for _ in range(TOTAL_ROUNDS)]
    dark_per_round = [0] * TOTAL_ROUNDS
    rifts_per_round = []
    mons_per_round = []

    if verbose:
        print("==== GAME START ====")
    initial_spawn(board)
    if verbose:
        print(" RMQs:", {loc: [s.t for s in board[loc]] for loc in sorted(board)})
    place_initial_dark(verbose)
    if verbose:
        print(" Dark clusters:", [c for c, v in dark_map.items() if v])

    for rnd in range(1, TOTAL_ROUNDS + 1):
        if verbose:
            print(f"\n-- ROUND {rnd} --")
        cnts = Counter(s.t for p in board.values() for s in p)
        rifts_per_round.append(cnts['R'])
        mons_per_round.append(cnts['M'])
        doom += cnts['M']

        dark_per_round[rnd - 1] = sum(dark_map[c] for c in dark_map if c != 'A')
        if verbose:
            dlist = [c for c in dark_map if dark_map[c]]
            print(
                f" Rifts={cnts['R']} Mons={cnts['M']} Doom={doom} Dark={len(dlist)}/8 {dlist}"
            )
            print(" Heroes:", heroes)

        dist_maps = [dijkstra(h)[0] for h in heroes]

        if sum(dark_map[c] for c in dark_map if c != 'A') >= 5:
            candidates = [CLUSTER_MAJOR[c] for c in dark_map if dark_map[c]]
        else:
            candidates = [
                loc
                for loc in board
                if any(s.t in ('R', 'M', 'Q') for s in board[loc])
            ]
            dark_candidates = [
                CLUSTER_MAJOR[c] for c in dark_map if dark_map[c]
            ]
            candidates = list(dict.fromkeys(candidates + dark_candidates))

        targets = [None] * H
        if candidates:
            if len(candidates) >= H:
                best_score = float('inf')
                best_assign = None
                for perm in permutations(candidates, H):
                    score = sum(
                        dist_maps[i].get(perm[i], float('inf')) for i in range(H)
                    )
                    if score < best_score:
                        best_score, best_assign = score, perm
                targets = list(best_assign)
            else:
                k = len(candidates)
                best_score = float('inf')
                best_assign = None
                for perm in permutations(candidates, k):
                    score = sum(
                        dist_maps[i].get(perm[i], float('inf')) for i in range(k)
                    )
                    if score < best_score:
                        best_score, best_assign = score, perm
                for i in range(k):
                    targets[i] = best_assign[i]

        if verbose:
            for h in range(H):
                print(f"  Hero{h+1} target → {targets[h]}")

        for h in range(H):
            dm, prev = dijkstra(heroes[h])
            tgt = targets[h] or heroes[h]
            path = reconstruct_path(prev, tgt)
            mp = HERO_SPEED
            pos = heroes[h]
            for nxt in path[1:]:
                cost = 2 if dark_map[NODE_TO_CLUSTER[nxt]] else 1
                if cost > mp:
                    break
                mp -= cost
                lost_hero[h] += cost - 1
                lost_round[rnd - 1][h] += cost - 1
                pos = nxt
            heroes[h] = pos
            if verbose:
                print(f"  Hero{h+1} moved → {pos}")

            cl = NODE_TO_CLUSTER[pos]
            if cl != 'A' and dark_map[cl] and pos == CLUSTER_MAJOR[cl]:
                if random.random() < 0.7:
                    dark_map[cl] = False
                    if verbose:
                        print(f"  Hero{h+1} cleaned darkness at {pos}")

            pile = board.get(pos, [])
            types = {s.t for s in pile}
            if 'R' in types and random.random() < min(1, 0.65 + (rnd - 1) * 0.015):
                pile.remove(next(s for s in pile if s.t == 'R'))
                if verbose:
                    print(f"  Hero{h+1} closed Rift")
            elif 'M' in types:
                pile.remove(next(s for s in pile if s.t == 'M'))
                if verbose:
                    print(f"  Hero{h+1} killed Monster")
            elif 'Q' in types:
                pile.remove(next(s for s in pile if s.t == 'Q'))
                if verbose:
                    print(f"  Hero{h+1} took Quest")

        if rnd < TOTAL_ROUNDS:
            if verbose:
                print(" End-of-round Darkness:")
            end_of_round_darkness(rnd, verbose)
            if sum(dark_map[c] for c in dark_map if c != 'A') == 8:
                full_loss = True
                if verbose:
                    print(" ALL 8 majors dark!")

    if return_loss_detail:
        final_cnts = Counter(s.t for p in board.values() for s in p)
        return {
            'full_loss': full_loss,
            'lost_hero': lost_hero,
            'lost_round': lost_round,
            'dark_per_round': dark_per_round,
            'end_rifts': final_cnts['R'],
            'end_mons': final_cnts['M'],
            'end_doom': doom,
            'peak_rifts': max(rifts_per_round),
            'peak_mons': max(mons_per_round),
        }
    return None

# ───────── Monte Carlo driver ─────────
def main():
    print("=== VERBOSE FIRST GAME ===")
    play_game(verbose=True, return_loss_detail=False)

    md_losses = 0
    sum_lost_hero = [0] * H
    sum_lost_round = [[0] * H for _ in range(TOTAL_ROUNDS)]
    sum_dark_round = [0] * TOTAL_ROUNDS
    sum_end_rifts = 0
    sum_end_mons = 0
    sum_end_doom = 0
    sum_peak_rifts = 0
    sum_peak_mons = 0

    for i in range(1, RUNS + 1):
        res = play_game(verbose=False, return_loss_detail=True)
        if res['full_loss']:
            md_losses += 1

        for r in range(TOTAL_ROUNDS):
            sum_dark_round[r] += res['dark_per_round'][r]

        for h in range(H):
            sum_lost_hero[h] += res['lost_hero'][h]
            for r in range(TOTAL_ROUNDS):
                sum_lost_round[r][h] += res['lost_round'][r][h]

        sum_end_rifts += res['end_rifts']
        sum_end_mons += res['end_mons']
        sum_end_doom += res['end_doom']
        sum_peak_rifts += res['peak_rifts']
        sum_peak_mons += res['peak_mons']

        if i <= 10 or i % 100 == 0 or i == RUNS:
            sys.stdout.write(f"\rSim {i}/{RUNS} ({100 * i / RUNS:5.1f}%)")
            sys.stdout.flush()
    print()

    print(f"\nGames with all 8 majors dark: {md_losses}/{RUNS}\n")
    print("Avg MP lost to darkness per hero (total):")
    for h in range(H):
        print(f" Hero{h+1}: {sum_lost_hero[h] / RUNS:.2f}")
    print("\nAvg MP lost per hero per round:")
    for r in range(TOTAL_ROUNDS):
        vals = ", ".join(
            f"H{h+1}:{sum_lost_round[r][h] / RUNS:.2f}" for h in range(H)
        )
        print(f" Round {r + 1}: {vals}")
    print("\nAvg dark clusters per round:")
    for r in range(TOTAL_ROUNDS):
        print(f" Round {r + 1}: {sum_dark_round[r] / RUNS:.2f}")

    print(f"\nAvg end-of-game Rifts:    {sum_end_rifts / RUNS:.2f}")
    print(f"Avg end-of-game Monsters: {sum_end_mons / RUNS:.2f}")
    print(f"Avg end-of-game Doom:     {sum_end_doom / RUNS:.2f}\n")
    print(f"Avg peak Rifts:           {sum_peak_rifts / RUNS:.2f}")
    print(f"Avg peak Monsters:        {sum_peak_mons / RUNS:.2f}")


if __name__ == '__main__':
    main()
