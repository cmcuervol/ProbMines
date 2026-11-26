import pygame
import sys
from Board import MinesweeperBoard

CELL_SIZE = 40
MARGIN = 2
TOP_BAR_HEIGHT = 50

# Colors
BG_COLOR = (30, 30, 30)
TOP_BAR_COLOR = (42, 45, 52)
BTN_COLOR = (70, 115, 160)
BTN_DISABLED_COLOR = (60, 63, 70)
BTN_TEXT_COLOR = (245, 245, 245)

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
    height = TOP_BAR_HEIGHT + rows * (CELL_SIZE + MARGIN) + MARGIN
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Probabilistic Minesweeper")
    
    font = pygame.font.SysFont("monospace", 18, bold=True)
    btn_font = pygame.font.SysFont("monospace", 14, bold=True)
    prob_font = pygame.font.SysFont("monospace", 11)

    # Top bar button rectangles
    undo_btn = pygame.Rect(10, 10, 130, 30)
    new_game_btn = pygame.Rect(150, 10, 130, 30)

    board = MinesweeperBoard(rows, cols, mines)
    game_over = False

    while True:
        probs = get_boundary_probabilities(board) if not game_over else {}

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Keyboard shortcuts: Z = Undo, R = New Game
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and board.undo():
                    game_over = False
                elif event.key == pygame.K_r:
                    board.reset()
                    game_over = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                mx, my = pygame.mouse.get_pos()

                # 1. Check Top Bar Buttons (Left Click)
                if event.button == 1 and my < TOP_BAR_HEIGHT:
                    if undo_btn.collidepoint(mx, my):
                        if board.undo():
                            game_over = False
                    elif new_game_btn.collidepoint(mx, my):
                        board.reset()
                        game_over = False
                    continue

                # 2. Check Grid Clicks
                if not game_over and my >= TOP_BAR_HEIGHT:
                    c = mx // (CELL_SIZE + MARGIN)
                    r = (my - TOP_BAR_HEIGHT) // (CELL_SIZE + MARGIN)
                    
                    if 0 <= r < rows and 0 <= c < cols:
                        if event.button == 1:  # Left click: reveal
                            alive = board.reveal(r, c)
                            if not alive:
                                game_over = True
                                board.state[board.mines] = 1  # Show all mines on loss
                        elif event.button == 3:  # Right click: flag
                            board.toggle_flag(r, c)

        # Draw background & Top Bar
        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, TOP_BAR_COLOR, (0, 0, width, TOP_BAR_HEIGHT))

        # Draw Undo Button (dims if history is empty)
        u_color = BTN_COLOR if board.history else BTN_DISABLED_COLOR
        pygame.draw.rect(screen, u_color, undo_btn, border_radius=4)
        u_txt = btn_font.render("Undo (Z)", True, BTN_TEXT_COLOR)
        screen.blit(u_txt, (undo_btn.x + 28, undo_btn.y + 7))

        # Draw New Game Button
        pygame.draw.rect(screen, BTN_COLOR, new_game_btn, border_radius=4)
        n_txt = btn_font.render("New Game (R)", True, BTN_TEXT_COLOR)
        screen.blit(n_txt, (new_game_btn.x + 12, new_game_btn.y + 7))

        # Draw Grid
        for r in range(rows):
            for c in range(cols):
                x = MARGIN + c * (CELL_SIZE + MARGIN)
                y = TOP_BAR_HEIGHT + MARGIN + r * (CELL_SIZE + MARGIN)
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