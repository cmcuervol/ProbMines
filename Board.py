import numpy as np
from typing import Tuple, Optional, List

class MinesweeperBoard:
    def __init__(self, rows: int, cols: int, num_mines: int):
        if num_mines >= rows * cols:
            raise ValueError("Number of mines must be less than total cells.")
        
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.reset()

    def reset(self) -> None:
        """Starts a completely new game from zero with fresh mine placement."""
        self.mines = np.zeros((self.rows, self.cols), dtype=bool)
        self.adjacent_counts = np.zeros((self.rows, self.cols), dtype=int)
        # 0 = Hidden, 1 = Revealed, 2 = Flagged
        self.state = np.zeros((self.rows, self.cols), dtype=int)
        self.mines_placed = False
        self.history: List[Tuple[np.ndarray, bool]] = []

    def _save_snapshot(self) -> None:
        """Stores current board visibility state before a player action."""
        self.history.append((self.state.copy(), self.mines_placed))

    def undo(self) -> bool:
        """Reverts the board to the state right before the last move."""
        if not self.history:
            return False
        self.state, self.mines_placed = self.history.pop()
        if not self.mines_placed:
            self.mines.fill(False)
            self.adjacent_counts.fill(0)
        return True

    def place_mines(self, safe_coord: Optional[Tuple[int, int]] = None) -> None:
        """Randomly places x mines across the m x n grid, avoiding safe_coord."""
        all_indices = np.arange(self.rows * self.cols)
        
        if safe_coord is not None:
            r, c = safe_coord
            safe_flat_idx = r * self.cols + c
            all_indices = np.delete(all_indices, safe_flat_idx)
            
        chosen_flat = np.random.choice(all_indices, size=self.num_mines, replace=False)
        mine_rows, mine_cols = np.unravel_index(chosen_flat, (self.rows, self.cols))
        
        self.mines[mine_rows, mine_cols] = True
        self._compute_adjacencies()
        self.mines_placed = True

    def _compute_adjacencies(self) -> None:
        """Calculates the 8-neighbor mine count for every cell."""
        padded = np.pad(self.mines, pad_width=1, mode='constant', constant_values=False)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                self.adjacent_counts += padded[1 + dr : 1 + dr + self.rows, 
                                               1 + dc : 1 + dc + self.cols]

    def _flood_reveal(self, r: int, c: int) -> bool:
        """Internal reveal without saving a history snapshot. Returns False if a mine is hit."""
        if self.state[r, c] != 0:
            return True

        if self.mines[r, c]:
            self.state[r, c] = 1
            return False

        stack = [(r, c)]
        while stack:
            curr_r, curr_c = stack.pop()
            if self.state[curr_r, curr_c] != 0:
                continue
            self.state[curr_r, curr_c] = 1
            
            if self.adjacent_counts[curr_r, curr_c] == 0:
                for nr in range(max(0, curr_r - 1), min(self.rows, curr_r + 2)):
                    for nc in range(max(0, curr_c - 1), min(self.cols, curr_c + 2)):
                        if self.state[nr, nc] == 0:
                            stack.append((nr, nc))
        return True

    def reveal(self, r: int, c: int) -> bool:
        """Reveals a hidden cell. Returns False if a mine was hit, True otherwise."""
        if self.state[r, c] != 0:
            return True

        self._save_snapshot()

        if not self.mines_placed:
            self.place_mines(safe_coord=(r, c))
            
        return self._flood_reveal(r, c)

    def chord_reveal(self, r: int, c: int) -> bool:
        """
        If (r, c) is a revealed numbered cell whose adjacent flags match its
        mine count, reveals all remaining hidden neighbors in one move.
        Returns False if a wrong flag caused a mine to trigger.
        """
        if self.state[r, c] != 1 or self.adjacent_counts[r, c] == 0:
            return True

        r_min, r_max = max(0, r - 1), min(self.rows, r + 2)
        c_min, c_max = max(0, c - 1), min(self.cols, c + 2)

        sub_state = self.state[r_min:r_max, c_min:c_max]
        flagged_count = int(np.sum(sub_state == 2))
        hidden_coords = [
            (nr, nc)
            for nr in range(r_min, r_max)
            for nc in range(c_min, c_max)
            if self.state[nr, nc] == 0
        ]

        # Only trigger if flags match the cell's number and there are hidden cells left
        if flagged_count != self.adjacent_counts[r, c] or not hidden_coords:
            return True

        self._save_snapshot()
        alive = True
        for nr, nc in hidden_coords:
            if not self._flood_reveal(nr, nc):
                alive = False
        return alive

    def toggle_flag(self, r: int, c: int) -> None:
        """Toggles a flag on a hidden cell."""
        if self.state[r, c] in (0, 2):
            self._save_snapshot()
            self.state[r, c] = 2 if self.state[r, c] == 0 else 0