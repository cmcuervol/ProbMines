import numpy as np
from typing import Tuple, Optional

class MinesweeperBoard:
    def __init__(self, rows: int, cols: int, num_mines: int):
        if num_mines >= rows * cols:
            raise ValueError("Number of mines must be less than total cells.")
        
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        
        # Core grids
        self.mines = np.zeros((rows, cols), dtype=bool)
        self.adjacent_counts = np.zeros((rows, cols), dtype=int)
        
        # Visibility states: 0 = Hidden, 1 = Revealed, 2 = Flagged
        self.state = np.zeros((rows, cols), dtype=int)
        self.mines_placed = False

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

    def reveal(self, r: int, c: int) -> bool:
        """Reveals a cell. Returns False if a mine was hit, True otherwise."""
        if not self.mines_placed:
            self.place_mines(safe_coord=(r, c))
            
        if self.state[r, c] != 0:
            return True
            
        if self.mines[r, c]:
            self.state[r, c] = 1
            return False  # Game Over
            
        # Flood-fill reveal for zero-adjacent cells
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

    def toggle_flag(self, r: int, c: int) -> None:
        """Toggles a flag on a hidden cell."""
        if self.state[r, c] == 0:
            self.state[r, c] = 2
        elif self.state[r, c] == 2:
            self.state[r, c] = 0