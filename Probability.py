import math
import numpy as np
from collections import deque
from typing import Dict, List, Tuple, Set
from Board import MinesweeperBoard

Coord = Tuple[int, int]


def _log_comb(n: int, k: int) -> float:
    """Computes log(n choose k) safely as a float for arbitrarily large n."""
    if k < 0 or k > n:
        return -math.inf
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def get_boundary_probabilities(board: MinesweeperBoard) -> Dict[Coord, float]:
    """
    Computes exact Bayesian mine probabilities for hidden cells on the boundary.
    Returns {} if mines aren't placed yet or if fewer than 2 clues exist
    (insufficient overlapping data to constrain the boundary).
    """
    if not board.mines_placed:
        return {}

    rows, cols = board.rows, board.cols
    hidden_mask = board.state == 0
    flagged_mask = board.state == 2
    revealed_num_mask = (board.state == 1) & (board.adjacent_counts > 0)

    total_flagged = int(np.sum(flagged_mask))
    mines_remaining = max(0, board.num_mines - total_flagged)

    # 1. Extract revealed clues and boundary hidden cells
    clues: List[Tuple[Coord, int, List[Coord]]] = []
    boundary_set: Set[Coord] = set()

    num_coords = np.argwhere(revealed_num_mask)
    for r, c in num_coords:
        r, c = int(r), int(c)
        r_min, r_max = max(0, r - 1), min(rows, r + 2)
        c_min, c_max = max(0, c - 1), min(cols, c + 2)

        adj_flags = 0
        adj_hidden: List[Coord] = []
        for nr in range(r_min, r_max):
            for nc in range(c_min, c_max):
                if nr == r and nc == c:
                    continue
                if flagged_mask[nr, nc]:
                    adj_flags += 1
                elif hidden_mask[nr, nc]:
                    adj_hidden.append((nr, nc))

        if adj_hidden:
            needed = int(board.adjacent_counts[r, c]) - adj_flags
            clues.append(((r, c), needed, adj_hidden))
            boundary_set.update(adj_hidden)

    # Skip calculation when there are fewer than 2 active clues (e.g., single '1' opening)
    if len(clues) < 2 or not boundary_set:
        return {}

    total_hidden = int(np.sum(hidden_mask))
    interior_hidden = total_hidden - len(boundary_set)

    # 2. Split boundary cells into connected components via shared clues
    adj_graph: Dict[Coord, Set[Coord]] = {cell: set() for cell in boundary_set}
    for _, _, h_cells in clues:
        for i in range(len(h_cells)):
            for j in range(i + 1, len(h_cells)):
                u, v = h_cells[i], h_cells[j]
                adj_graph[u].add(v)
                adj_graph[v].add(u)

    components: List[List[Coord]] = []
    visited: Set[Coord] = set()
    for cell in boundary_set:
        if cell not in visited:
            comp: List[Coord] = []
            queue = deque([cell])
            visited.add(cell)
            while queue:
                curr = queue.popleft()
                comp.append(curr)
                for nxt in adj_graph[curr]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            components.append(comp)

    # 3. Solve each connected component via backtracking
    comp_solutions: List[Tuple[List[Coord], Dict[int, np.ndarray]]] = []
    for comp in components:
        comp_set = set(comp)
        comp_clues = [
            (needed, h_cells)
            for _, needed, h_cells in clues
            if h_cells[0] in comp_set
        ]
        sols_by_k = _solve_component(comp, comp_clues)
        if not sols_by_k:
            return _fallback_local_ratios(clues)
        comp_solutions.append((comp, sols_by_k))

    # 4. Combine component mine-count distributions in float64 to avoid int overflow
    dp_ways: Dict[int, float] = {0: 1.0}
    for _, sols_by_k in comp_solutions:
        next_dp: Dict[int, float] = {}
        for prev_m, prev_w in dp_ways.items():
            for k, arr in sols_by_k.items():
                if prev_m + k <= mines_remaining:
                    next_dp[prev_m + k] = next_dp.get(prev_m + k, 0.0) + prev_w * len(arr)
        dp_ways = next_dp

    # Compute normalized log-weights for interior mine combinations (prevents huge int overflow)
    log_weights: Dict[int, float] = {}
    for m_b, ways in dp_ways.items():
        m_int = mines_remaining - m_b
        if 0 <= m_int <= interior_hidden and ways > 0:
            log_weights[m_b] = math.log(ways) + _log_comb(interior_hidden, m_int)

    if not log_weights:
        return _fallback_local_ratios(clues)

    max_log_w = max(log_weights.values())
    norm_interior_weights: Dict[int, float] = {
        m_b: math.exp(_log_comb(interior_hidden, mines_remaining - m_b) - max_log_w)
        for m_b in log_weights
    }
    grand_total = sum(
        dp_ways[m_b] * norm_interior_weights[m_b] for m_b in log_weights
    )

    if grand_total == 0.0:
        return _fallback_local_ratios(clues)

    # 5. Marginalize per cell across all valid global mine counts
    probs: Dict[Coord, float] = {}
    for idx, (comp, sols_by_k) in enumerate(comp_solutions):
        other_dp: Dict[int, float] = {0: 1.0}
        for j, (_, other_sols) in enumerate(comp_solutions):
            if idx == j:
                continue
            next_other: Dict[int, float] = {}
            for prev_m, prev_w in other_dp.items():
                for k, arr in other_sols.items():
                    if prev_m + k <= mines_remaining:
                        next_other[prev_m + k] = next_other.get(prev_m + k, 0.0) + prev_w * len(arr)
            other_dp = next_other

        mine_weighted_counts = np.zeros(len(comp), dtype=np.float64)
        for k, arr in sols_by_k.items():
            # Cast to float64 before multiplying by large weights
            cell_mine_sums = np.sum(arr, axis=0, dtype=np.float64)
            for other_m, other_w in other_dp.items():
                m_b = k + other_m
                if m_b in norm_interior_weights:
                    weight = other_w * norm_interior_weights[m_b]
                    mine_weighted_counts += cell_mine_sums * weight

        for cell_i, coord in enumerate(comp):
            probs[coord] = float(np.clip(mine_weighted_counts[cell_i] / grand_total, 0.0, 1.0))

    return probs


def _solve_component(
    comp: List[Coord], comp_clues: List[Tuple[int, List[Coord]]]
) -> Dict[int, np.ndarray]:
    """Backtracks over binary assignments for a connected boundary component."""
    n = len(comp)
    idx_map = {coord: i for i, coord in enumerate(comp)}

    indexed_clues = [
        (needed, [idx_map[c] for c in h_cells]) for needed, h_cells in comp_clues
    ]

    triggers: List[List[Tuple[int, List[int]]]] = [[] for _ in range(n)]
    partial_triggers: List[List[Tuple[int, List[int]]]] = [[] for _ in range(n)]
    for needed, vars_idx in indexed_clues:
        if needed < 0 or needed > len(vars_idx):
            return {}
        last_var = max(vars_idx)
        triggers[last_var].append((needed, vars_idx))
        for v in vars_idx:
            partial_triggers[v].append((needed, vars_idx))

    assignment = [0] * n
    sols_by_k: Dict[int, List[List[int]]] = {}

    def backtrack(pos: int, current_mines: int) -> None:
        if pos == n:
            sols_by_k.setdefault(current_mines, []).append(assignment.copy())
            return

        for val in (0, 1):
            assignment[pos] = val
            valid = True

            for needed, vars_idx in triggers[pos]:
                if sum(assignment[v] for v in vars_idx) != needed:
                    valid = False
                    break

            if valid:
                for needed, vars_idx in partial_triggers[pos]:
                    assigned_sum = 0
                    unassigned = 0
                    for v in vars_idx:
                        if v <= pos:
                            assigned_sum += assignment[v]
                        else:
                            unassigned += 1
                    if assigned_sum > needed or assigned_sum + unassigned < needed:
                        valid = False
                        break

            if valid:
                backtrack(pos + 1, current_mines + val)

    backtrack(0, 0)
    return {k: np.array(v, dtype=np.int8) for k, v in sols_by_k.items()}


def _fallback_local_ratios(clues: List[Tuple[Coord, int, List[Coord]]]) -> Dict[Coord, float]:
    """Simple fallback ratio if user flags contradict board clues."""
    accum: Dict[Coord, List[float]] = {}
    for _, needed, h_cells in clues:
        p = np.clip(needed / len(h_cells), 0.0, 1.0)
        for cell in h_cells:
            accum.setdefault(cell, []).append(float(p))
    return {cell: float(np.mean(vals)) for cell, vals in accum.items()}