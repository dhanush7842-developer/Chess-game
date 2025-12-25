import pygame
import sys

pygame.init()

# ---------------- WINDOW ----------------
WIDTH, HEIGHT = 720, 720
SQ = WIDTH // 8
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Game")

# ---------------- COLORS (IMPROVED WOODEN STYLE) ----------------
LIGHT = (240, 217, 181)
DARK  = (181, 136, 99)
SELECT = (255, 255, 150)  # Bright yellow for selected piece
MOVE = (173, 216, 230)  # Light blue for valid moves (like in image)
MOVE_OVERLAY = (173, 216, 230, 180)  # Semi-transparent overlay
CHECK = (255, 0, 0)  # Red for check indication

# ---------------- LOAD PIECES ----------------
pieces = {}
names = ["wp","wr","wn","wb","wq","wk","bp","br","bn","bb","bq","bk"]
for n in names:
    pieces[n] = pygame.transform.scale(
        pygame.image.load(f"pieces/{n}.png").convert_alpha(),
        (SQ - 8, SQ - 8)
    )

# ---------------- BOARD (Starting position) ----------------
# Rank 8 (index 0) to Rank 1 (index 7)
# Files: a(0), b(1), c(2), d(3), e(4), f(5), g(6), h(7)
board = [
    ["br","bn","bb","bq","bk","bb","bn","br"],  # Rank 8
    ["bp","bp","bp","bp","bp","bp","bp","bp"],  # Rank 7
    ["","","","","","","",""],                   # Rank 6
    ["","","","","","","",""],                   # Rank 5
    ["","","","","","","",""],                   # Rank 4
    ["","","","","","","",""],                   # Rank 3
    ["wp","wp","wp","wp","wp","wp","wp","wp"],  # Rank 2
    ["wr","wn","wb","wq","wk","wb","wn","wr"]   # Rank 1
]

turn = "white"
selected = None
last_move = None  # Track last move for highlighting
game_state = "playing"  # "playing", "check", "checkmate", "stalemate"
en_passant_target = None  # (row, col) of pawn that can be captured en passant
castling_rights = {"w": {"kingside": True, "queenside": True}, 
                   "b": {"kingside": True, "queenside": True}}

# ---------------- DRAW ----------------
def draw_board():
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r + c) % 2 == 0 else DARK
            pygame.draw.rect(WIN, color, (c*SQ, r*SQ, SQ, SQ))
    
    # Draw file labels (a-h)
    font = pygame.font.Font(None, 24)
    for c in range(8):
        label = chr(ord('a') + c)
        text = font.render(label, True, (0, 0, 0) if c % 2 == 0 else (255, 255, 255))
        WIN.blit(text, (c*SQ + SQ - 20, HEIGHT - 25))
    
    # Draw rank labels (1-8)
    for r in range(8):
        label = str(8 - r)
        color = (0, 0, 0) if (r + 0) % 2 == 0 else (255, 255, 255)
        text = font.render(label, True, color)
        WIN.blit(text, (5, r*SQ + 5))

def draw_pieces():
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece:
                WIN.blit(pieces[piece], (c*SQ + 4, r*SQ + 4))

def draw_check_indicator():
    """Draw red highlight on king in check"""
    if game_state == "check" or game_state == "checkmate":
        current_color = "w" if turn == "white" else "b"
        king_pos = find_king(current_color)
        if king_pos:
            kr, kc = king_pos
            overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            overlay.fill((*CHECK[:3], 150))  # Semi-transparent red
            WIN.blit(overlay, (kc*SQ, kr*SQ))

def draw_game_status():
    """Display game status text"""
    font = pygame.font.Font(None, 36)
    status_text = ""
    color = (255, 255, 255)
    
    if game_state == "check":
        status_text = "CHECK!"
        color = (255, 200, 0)
    elif game_state == "checkmate":
        winner = "Black" if turn == "white" else "White"
        status_text = f"CHECKMATE! {winner} Wins!"
        color = (255, 0, 0)
    elif game_state == "stalemate":
        status_text = "STALEMATE - Draw!"
        color = (200, 200, 200)
    
    if status_text:
        text_surface = font.render(status_text, True, color)
        text_rect = text_surface.get_rect(center=(WIDTH // 2, 30))
        # Draw background for text
        bg_rect = pygame.Rect(text_rect.x - 10, text_rect.y - 5, 
                              text_rect.width + 20, text_rect.height + 10)
        pygame.draw.rect(WIN, (0, 0, 0), bg_rect)
        pygame.draw.rect(WIN, (50, 50, 50), bg_rect, 2)
        WIN.blit(text_surface, text_rect)

# ---------------- MOVE LOGIC ----------------
def path_clear(sr, sc, er, ec):
    dr = er - sr
    dc = ec - sc
    if dr == 0 and dc == 0:
        return False
    step_r = (dr > 0) - (dr < 0) if dr != 0 else 0
    step_c = (dc > 0) - (dc < 0) if dc != 0 else 0
    r, c = sr + step_r, sc + step_c
    while (r, c) != (er, ec):
        if board[r][c] != "":
            return False
        r += step_r
        c += step_c
    return True

def find_king(color):
    """Find the position of the king for the given color"""
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece[0] == color and piece[1] == "k":
                return (r, c)
    return None

def is_in_check(color):
    """Check if the king of the given color is in check"""
    king_pos = find_king(color)
    if not king_pos:
        return False
    kr, kc = king_pos
    opponent = "b" if color == "w" else "w"
    
    # Check if any opponent piece can attack the king
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece[0] == opponent:
                if valid_move_without_check(r, c, kr, kc):
                    return True
    return False

def valid_move_without_check(sr, sc, er, ec):
    """Check if move is valid without considering check (used internally)"""
    piece = board[sr][sc]
    if not piece:
        return False

    target = board[er][ec]
    if target and target[0] == piece[0]:
        return False

    dr, dc = er - sr, ec - sc

    # PAWN
    if piece[1] == "p":
        direction = -1 if piece[0] == "w" else 1
        start_row = 6 if piece[0] == "w" else 1

        # one step
        if dc == 0 and dr == direction and target == "":
            return True

        # two steps on first move
        if (sr == start_row and dc == 0 and
            dr == 2 * direction and
            board[sr + direction][sc] == "" and
            target == ""):
            return True

        # capture
        if abs(dc) == 1 and dr == direction and target != "":
            return True
        
        # En passant
        if en_passant_target and (er, ec) == en_passant_target:
            if abs(dc) == 1 and dr == direction:
                return True

    # ROOK
    if piece[1] == "r" and (sr == er or sc == ec):
        return path_clear(sr, sc, er, ec)

    # BISHOP
    if piece[1] == "b" and abs(dr) == abs(dc):
        return path_clear(sr, sc, er, ec)

    # QUEEN
    if piece[1] == "q":
        if sr == er or sc == ec or abs(dr) == abs(dc):
            return path_clear(sr, sc, er, ec)

    # KNIGHT
    if piece[1] == "n":
        return (abs(dr), abs(dc)) in [(1,2),(2,1)]

    # KING
    if piece[1] == "k":
        # Normal king move
        if abs(dr) <= 1 and abs(dc) <= 1:
            return True
        # Castling
        if abs(dc) == 2 and dr == 0 and sr in [0, 7]:
            return can_castle(piece[0], sr, sc, er, ec)

    return False

def can_castle(color, kr, kc, er, ec):
    """Check if castling is legal"""
    # King must not have moved
    if not castling_rights[color]["kingside"] and not castling_rights[color]["queenside"]:
        return False
    
    # King must not be in check
    if is_in_check(color):
        return False
    
    # Determine which side
    if ec > kc:  # Kingside
        if not castling_rights[color]["kingside"]:
            return False
        rook_col = 7
        squares_between = [(kr, 5), (kr, 6)]
    else:  # Queenside
        if not castling_rights[color]["queenside"]:
            return False
        rook_col = 0
        squares_between = [(kr, 1), (kr, 2), (kr, 3)]
    
    # Check if rook exists and hasn't moved
    if board[kr][rook_col] != (color + "r"):
        return False
    
    # Check if squares between are empty
    for r, c in squares_between:
        if board[r][c] != "":
            return False
    
    # Check if king passes through check
    # King moves from kc to ec, so check squares between
    step = 1 if ec > kc else -1
    king_path = []
    for col in range(kc + step, ec + step, step):
        king_path.append((kr, col))
    
    for r, c in king_path:
        # Temporarily move king
        backup = board[r][c]
        board[r][c] = color + "k"
        board[kr][kc] = ""
        in_check = is_in_check(color)
        board[kr][kc] = color + "k"
        board[r][c] = backup
        if in_check:
            return False
    
    return True

def valid_move(sr, sc, er, ec):
    """Check if move is valid, including check prevention"""
    piece = board[sr][sc]
    if not piece:
        return False

    # First check basic move validity
    if not valid_move_without_check(sr, sc, er, ec):
        return False
    
    # Handle special moves
    color = piece[0]
    
    # En passant capture
    en_passant_capture = False
    if piece[1] == "p" and en_passant_target and (er, ec) == en_passant_target:
        en_passant_capture = True
        captured_pawn_row = sr  # Pawn being captured is on same row
        captured_pawn_col = ec
    
    # Castling
    castling_move = False
    if piece[1] == "k" and abs(ec - sc) == 2:
        castling_move = True
        rook_start_col = 7 if ec > sc else 0
        rook_end_col = 5 if ec > sc else 3
    
    # Make the move temporarily to check if it leaves own king in check
    backup_target = board[er][ec]
    backup_en_passant = None
    if en_passant_capture:
        backup_en_passant = board[captured_pawn_row][captured_pawn_col]
        board[captured_pawn_row][captured_pawn_col] = ""
    
    if castling_move:
        # Move rook for castling check
        board[er][rook_end_col] = board[sr][rook_start_col]
        board[sr][rook_start_col] = ""
    
    board[er][ec] = board[sr][sc]
    board[sr][sc] = ""
    
    # Check if this move leaves own king in check
    in_check = is_in_check(color)
    
    # Restore the board
    board[sr][sc] = board[er][ec]
    board[er][ec] = backup_target
    if en_passant_capture:
        board[captured_pawn_row][captured_pawn_col] = backup_en_passant
    if castling_move:
        board[sr][rook_start_col] = board[er][rook_end_col]
        board[er][rook_end_col] = ""
    
    # Move is invalid if it leaves own king in check
    return not in_check

# ---------------- PAWN PROMOTION ----------------
def promote_pawn():
    for c in range(8):
        if board[0][c] == "wp":
            board[0][c] = "wq"
        if board[7][c] == "bp":
            board[7][c] = "bq"

# ---------------- AI (EASY MODE) ----------------
def evaluate():
    values = {"p":1,"n":3,"b":3,"r":5,"q":9,"k":100}
    score = 0
    for r in range(8):
        for c in range(8):
            if board[r][c]:
                v = values[board[r][c][1]]
                score += v if board[r][c][0] == "b" else -v
    return score

def get_moves(color):
    moves = []
    for r in range(8):
        for c in range(8):
            if board[r][c] and board[r][c][0] == color:
                for er in range(8):
                    for ec in range(8):
                        if valid_move(r, c, er, ec):
                            moves.append((r, c, er, ec))
    return moves

def update_game_state():
    """Update game state (check, checkmate, stalemate)"""
    global game_state
    current_color = "w" if turn == "white" else "b"
    opponent_color = "b" if turn == "white" else "w"
    
    # Check if current player is in check
    in_check = is_in_check(current_color)
    
    # Get all legal moves for current player
    legal_moves = get_moves(current_color)
    
    if in_check:
        if len(legal_moves) == 0:
            game_state = "checkmate"
        else:
            game_state = "check"
    else:
        if len(legal_moves) == 0:
            game_state = "stalemate"
        else:
            game_state = "playing"

def ai_move():
    """AI makes a move and returns the move coordinates"""
    global en_passant_target
    best_score = -9999
    best_move = None

    moves = get_moves("b")
    if not moves:
        return None

    for m in moves:
        sr, sc, er, ec = m
        piece = board[sr][sc]
        
        # Handle en passant for evaluation
        en_passant_backup = None
        if piece[1] == "p" and en_passant_target and (er, ec) == en_passant_target:
            captured_row = sr
            captured_col = ec
            en_passant_backup = board[captured_row][captured_col]
            board[captured_row][captured_col] = ""
        
        # Handle castling for evaluation
        castling_rook = None
        if piece[1] == "k" and abs(ec - sc) == 2:
            rook_start_col = 7 if ec > sc else 0
            rook_end_col = 5 if ec > sc else 3
            castling_rook = (sr, rook_start_col, rook_end_col)
            board[er][rook_end_col] = board[sr][rook_start_col]
            board[sr][rook_start_col] = ""
        
        backup = board[er][ec]
        board[er][ec] = board[sr][sc]
        board[sr][sc] = ""
        score = evaluate()   # EASY AI
        board[sr][sc] = board[er][ec]
        board[er][ec] = backup
        
        if castling_rook:
            r, rs, re = castling_rook
            board[r][rs] = board[r][re]
            board[r][re] = ""
        
        if en_passant_backup is not None:
            board[sr][ec] = en_passant_backup

        if score > best_score:
            best_score = score
            best_move = m

    if best_move:
        sr, sc, er, ec = best_move
        piece = board[sr][sc]
        
        # Handle en passant
        if piece[1] == "p" and en_passant_target and (er, ec) == en_passant_target:
            captured_row = sr
            captured_col = ec
            board[captured_row][captured_col] = ""
        
        # Handle castling
        if piece[1] == "k" and abs(ec - sc) == 2:
            rook_start_col = 7 if ec > sc else 0
            rook_end_col = 5 if ec > sc else 3
            board[er][rook_end_col] = board[sr][rook_start_col]
            board[sr][rook_start_col] = ""
            castling_rights["b"]["kingside"] = False
            castling_rights["b"]["queenside"] = False
        
        # Update castling rights
        if piece[1] == "k":
            castling_rights["b"]["kingside"] = False
            castling_rights["b"]["queenside"] = False
        if piece[1] == "r":
            if sc == 0:
                castling_rights["b"]["queenside"] = False
            elif sc == 7:
                castling_rights["b"]["kingside"] = False
        
        board[er][ec] = board[sr][sc]
        board[sr][sc] = ""
        
        # Set en passant target
        en_passant_target = None
        if piece[1] == "p" and abs(er - sr) == 2:
            en_passant_target = (sr + (er - sr) // 2, ec)
        
        return (sr, sc, er, ec)
    return None

# ---------------- MAIN LOOP ----------------
def main():
    global selected, turn, last_move, game_state, en_passant_target, castling_rights
    clock = pygame.time.Clock()

    while True:
        clock.tick(60)
        draw_board()

        # Update game state
        update_game_state()

        # Highlight last move (like in the image - f6 and h8)
        if last_move:
            sr, sc, er, ec = last_move
            # Create a semi-transparent surface for overlay
            overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            overlay.fill((*MOVE[:3], 180))  # Add alpha channel
            WIN.blit(overlay, (sc*SQ, sr*SQ))
            WIN.blit(overlay, (ec*SQ, er*SQ))

        # Highlight selected piece and valid moves (square highlighting like in image)
        if selected and game_state not in ["checkmate", "stalemate"]:
            r, c = selected
            # Highlight selected piece
            overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            overlay.fill((*SELECT[:3], 180))
            WIN.blit(overlay, (c*SQ, r*SQ))
            
            # Highlight valid move squares (like in image)
            for er in range(8):
                for ec in range(8):
                    if valid_move(r, c, er, ec):
                        overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                        overlay.fill((*MOVE[:3], 180))  # Add alpha channel
                        WIN.blit(overlay, (ec*SQ, er*SQ))

        draw_pieces()
        draw_check_indicator()
        draw_game_status()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if e.type == pygame.MOUSEBUTTONDOWN and turn == "white" and game_state not in ["checkmate", "stalemate"]:
                x, y = pygame.mouse.get_pos()
                # Don't process clicks on the label area
                if y < HEIGHT - 30 and x < WIDTH - 30:
                    r, c = y // SQ, x // SQ

                    if selected:
                        sr, sc = selected
                        piece = board[sr][sc]
                        if valid_move(sr, sc, r, c):
                            # Handle en passant
                            en_passant_captured = False
                            if piece[1] == "p" and en_passant_target and (r, c) == en_passant_target:
                                captured_row = sr
                                captured_col = c
                                board[captured_row][captured_col] = ""
                                en_passant_captured = True
                            
                            # Handle castling
                            if piece[1] == "k" and abs(c - sc) == 2:
                                rook_start_col = 7 if c > sc else 0
                                rook_end_col = 5 if c > sc else 3
                                board[r][rook_end_col] = board[r][rook_start_col]
                                board[r][rook_start_col] = ""
                                castling_rights[piece[0]]["kingside"] = False
                                castling_rights[piece[0]]["queenside"] = False
                            
                            # Update castling rights
                            if piece[1] == "k":
                                castling_rights[piece[0]]["kingside"] = False
                                castling_rights[piece[0]]["queenside"] = False
                            if piece[1] == "r":
                                if sc == 0:
                                    castling_rights[piece[0]]["queenside"] = False
                                elif sc == 7:
                                    castling_rights[piece[0]]["kingside"] = False
                            
                            # Make the move
                            board[r][c] = board[sr][sc]
                            board[sr][sc] = ""
                            last_move = (sr, sc, r, c)
                            
                            # Set en passant target if pawn moved two squares
                            en_passant_target = None
                            if piece[1] == "p" and abs(r - sr) == 2:
                                en_passant_target = (sr + (r - sr) // 2, c)
                            
                            promote_pawn()
                            
                            # Update game state before AI move
                            update_game_state()
                            
                            if game_state not in ["checkmate", "stalemate"]:
                                turn = "black"
                                ai_move_result = ai_move()
                                if ai_move_result:
                                    last_move = ai_move_result
                                    # Update AI castling rights
                                    ai_piece = board[ai_move_result[2]][ai_move_result[3]]
                                    if ai_piece[1] == "k":
                                        castling_rights["b"]["kingside"] = False
                                        castling_rights["b"]["queenside"] = False
                                    if ai_piece[1] == "r":
                                        if ai_move_result[1] == 0:
                                            castling_rights["b"]["queenside"] = False
                                        elif ai_move_result[1] == 7:
                                            castling_rights["b"]["kingside"] = False
                                    # Clear en passant after AI move
                                    en_passant_target = None
                                promote_pawn()
                                turn = "white"
                        selected = None
                    else:
                        if board[r][c] and board[r][c][0] == "w":
                            selected = (r, c)

        pygame.display.update()

main()


