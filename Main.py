import pygame
import sys
from Board import MinesweeperBoard

CELL_SIZE = 40
MARGIN = 2

# Colors
BG_COLOR = (30, 30, 30)
HIDDEN_COLOR = (70, 75, 85)
REVEALED_COLOR = (210, 215, 220)
FLAG_COLOR = (213, 94, 0)
MINE_COLOR = (200, 40, 40)
TEXT_COLOR = (20, 20, 20)

def get_boundary_probabilities(board: MinesweeperBoard) -> dict:
    """
    Placeholder for your probability solver.
    Returns {(row, col): probability_float} for hidden boundary cells.
    """
    return {}

def run_game(rows: int = 12, cols: int = 16, mines: int = 30):
    pygame.init()
    width = cols * (CELL_SIZE + MARGIN) + MARGIN
    height = rows * (CELL_SIZE + MARGIN) + MARGIN
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Probabilistic Minesweeper")
    font = pygame.font.SysFont("monospace", 18, bold=True)
    prob_font = pygame.font.SysFont("monospace", 11)

    board = MinesweeperBoard(rows, cols, mines)
    game_over = False

    while True:
        probs = get_boundary_probabilities(board) if not game_over else {}

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                mx, my = pygame.mouse.get_pos()
                c = mx // (CELL_SIZE + MARGIN)
                r = my // (CELL_SIZE + MARGIN)
                
                if 0 <= r < rows and 0 <= c < cols:
                    if event.button == 1:  # Left click: reveal
                        alive = board.reveal(r, c)
                        if not alive:
                            game_over = True
                            board.state[board.mines] = 1  # Reveal all mines
                    elif event.button == 3:  # Right click: flag
                        board.toggle_flag(r, c)

        screen.fill(BG_COLOR)
        for r in range(rows):
            for c in range(cols):
                x = MARGIN + c * (CELL_SIZE + MARGIN)
                y = MARGIN + r * (CELL_SIZE + MARGIN)
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                
                cell_state = board.state[r, c]
                if cell_state == 0:  # Hidden
                    pygame.draw.rect(screen, HIDDEN_COLOR, rect)
                    if (r, c) in probs:
                        p_text = prob_font.render(f"{int(probs[(r, c)]*100)}%", True, (255, 255, 255))
                        screen.blit(p_text, (x + 4, y + 12))
                elif cell_state == 2:  # Flagged
                    pygame.draw.rect(screen, FLAG_COLOR, rect)
                elif cell_state == 1:  # Revealed
                    if board.mines[r, c]:
                        pygame.draw.rect(screen, MINE_COLOR, rect)
                    else:
                        pygame.draw.rect(screen, REVEALED_COLOR, rect)
                        count = board.adjacent_counts[r, c]
                        if count > 0:
                            txt = font.render(str(count), True, TEXT_COLOR)
                            screen.blit(txt, (x + 13, y + 10))

        pygame.display.flip()

if __name__ == "__main__":
    run_game(rows=12, cols=16, mines=30)