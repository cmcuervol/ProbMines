import pygame
import sys
import numpy as np
from Board import MinesweeperBoard
from Probability import get_boundary_probabilities

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

# Reversed Inferno control points (p=0.0 safe -> p=1.0 certain mine)
_INFERNO_R_STOPS = np.array([
    [252, 255, 164],  # 0.00: Pale yellow (safe)
    [248, 205, 55],   # 0.20: Warm gold
    [237, 105, 37],   # 0.40: Bright orange
    [187, 55, 84],    # 0.60: Crimson-magenta
    [120, 28, 109],   # 0.80: Deep plum
    [35, 17, 81],     # 1.00: Dark indigo-violet (mine)
], dtype=float)
_INFERNO_R_POS = np.linspace(0.0, 1.0, len(_INFERNO_R_STOPS))


def prob_to_inferno_r(prob: float, lighten: float = 0.22) -> tuple[int, int, int]:
    """Maps probability in [0, 1] to a lightened reversed Inferno RGB tuple."""
    p = float(np.clip(prob, 0.0, 1.0))
    rgb = np.array([
        np.interp(p, _INFERNO_R_POS, _INFERNO_R_STOPS[:, ch]) for ch in range(3)
    ])
    # Blend toward white so tiles look lighter and more vibrant
    rgb = rgb + (255.0 - rgb) * lighten
    return tuple(int(round(c)) for c in rgb)


def draw_outlined_small_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    center_pos: tuple[int, int],
) -> None:
    """Renders crisp white percentage text with a subtle 1px dark halo for contrast."""
    fg = font.render(text, True, (255, 255, 255))
    bg = font.render(text, True, (25, 25, 30))
    rect = fg.get_rect(center=center_pos)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surface.blit(bg, rect.move(dx, dy))
    surface.blit(fg, rect)


def run_game(rows: int = 12, cols: int = 16, mines: int = 30):
    pygame.init()
    width = cols * (CELL_SIZE + MARGIN) + MARGIN
    height = TOP_BAR_HEIGHT + rows * (CELL_SIZE + MARGIN) + MARGIN
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Probabilistic Minesweeper")

    font = pygame.font.SysFont("monospace", 18, bold=True)
    btn_font = pygame.font.SysFont("monospace", 14, bold=True)
    prob_font = pygame.font.SysFont("monospace", 10, bold=True)

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

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and board.undo():
                    game_over = False
                elif event.key == pygame.K_r:
                    board.reset()
                    game_over = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
                mx, my = pygame.mouse.get_pos()

                # 1. Top Bar Buttons
                if event.button == 1 and my < TOP_BAR_HEIGHT:
                    if undo_btn.collidepoint(mx, my):
                        if board.undo():
                            game_over = False
                    elif new_game_btn.collidepoint(mx, my):
                        board.reset()
                        game_over = False
                    continue

                # 2. Grid Clicks
                if not game_over and my >= TOP_BAR_HEIGHT:
                    c = mx // (CELL_SIZE + MARGIN)
                    r = (my - TOP_BAR_HEIGHT) // (CELL_SIZE + MARGIN)

                    if 0 <= r < rows and 0 <= c < cols:
                        if event.button == 1:
                            if board.state[r, c] == 0:
                                alive = board.reveal(r, c)
                            elif board.state[r, c] == 1:
                                alive = board.chord_reveal(r, c)
                            else:
                                alive = True

                            if not alive:
                                game_over = True
                                board.state[board.mines] = 1
                        elif event.button == 2:
                            if not board.chord_reveal(r, c):
                                game_over = True
                                board.state[board.mines] = 1
                        elif event.button == 3:
                            board.toggle_flag(r, c)

        # Draw background & Top Bar
        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, TOP_BAR_COLOR, (0, 0, width, TOP_BAR_HEIGHT))

        u_color = BTN_COLOR if board.history else BTN_DISABLED_COLOR
        pygame.draw.rect(screen, u_color, undo_btn, border_radius=4)
        u_txt = btn_font.render("Undo (Z)", True, BTN_TEXT_COLOR)
        screen.blit(u_txt, (undo_btn.x + 28, undo_btn.y + 7))

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
                    if (r, c) in probs:
                        p = probs[(r, c)]
                        tile_color = prob_to_inferno_r(p, lighten=0.22)
                        pygame.draw.rect(screen, tile_color, rect)
                        draw_outlined_small_text(
                            screen,
                            prob_font,
                            f"{round(p * 100)}%",
                            rect.center,
                        )
                    else:
                        pygame.draw.rect(screen, HIDDEN_COLOR, rect)
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