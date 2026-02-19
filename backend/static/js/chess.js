/* ══════════════════════════════════════════
   chess.js — Full Chess Game UI
   
   Flow:
   1. Board state arrives from Django as JSON
   2. We draw it on HTML5 Canvas
   3. Player clicks → fetch valid moves from Django
   4. Player clicks destination → send move to Django
   5. Django applies move + AI responds
   6. We redraw with new board state
══════════════════════════════════════════ */

// ── CANVAS SETUP ────────────────────────
const canvas   = document.getElementById('chess-board');
const ctx      = canvas.getContext('2d');
canvas.width   = 560;
canvas.height  = 560;

const SQ       = 70;   // pixels per square

// ── COLORS ──────────────────────────────
const LIGHT_SQ    = '#f0d9b5';
const DARK_SQ     = '#b58863';
const SELECTED_SQ = 'rgba(20, 85, 30, 0.6)';
const MOVE_DOT    = 'rgba(0, 0, 0, 0.25)';
const MOVE_RING   = 'rgba(0, 0, 0, 0.25)';
const CHECK_SQ    = 'rgba(231, 76, 60, 0.55)';
const LAST_MOVE   = 'rgba(255, 255, 100, 0.3)';

// ── PIECE SYMBOLS ────────────────────────
const SYMBOLS = {
    white: {
        king:   '♔', queen:  '♕', rook:   '♖',
        bishop: '♗', knight: '♘', pawn:   '♙'
    },
    black: {
        king:   '♚', queen:  '♛', rook:   '♜',
        bishop: '♝', knight: '♞', pawn:   '♟'
    }
};

// Captured piece display symbols
const CAPTURE_SYMBOLS = {
    white: { king:'♔',queen:'♕',rook:'♖',bishop:'♗',knight:'♘',pawn:'♙' },
    black: { king:'♚',queen:'♛',rook:'♜',bishop:'♝',knight:'♞',pawn:'♟' }
};

// ── GAME STATE ───────────────────────────
let board          = INITIAL_BOARD;
let selectedSquare = null;   // [row, col] of selected piece
let validMoves     = [];     // [[row,col], ...] valid destinations
let lastMove       = null;   // {from:[r,c], to:[r,c]}
let inCheck        = false;  // is white king in check?
let gameOver       = GAME_STATUS !== 'active';
let isThinking     = false;  // waiting for server response
let moveCount      = 0;

// Captured pieces tracking
let capturedByWhite = [];
let capturedByBlack = [];


// ════════════════════════════════════════
// DRAWING FUNCTIONS
// ════════════════════════════════════════

function drawBoard() {
    // Find white king position (for check highlighting)
    let whiteKingPos = null;
    if (inCheck) {
        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const p = board[r][c];
                if (p && p.color === 'white' && p.type === 'king') {
                    whiteKingPos = [r, c];
                }
            }
        }
    }

    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const x = col * SQ;
            const y = row * SQ;

            // ── Base square color ────────
            ctx.fillStyle = (row + col) % 2 === 0 ? LIGHT_SQ : DARK_SQ;
            ctx.fillRect(x, y, SQ, SQ);

            // ── Last move highlight ──────
            if (lastMove) {
                const [fr, fc] = lastMove.from;
                const [tr, tc] = lastMove.to;
                if ((row === fr && col === fc) || (row === tr && col === tc)) {
                    ctx.fillStyle = LAST_MOVE;
                    ctx.fillRect(x, y, SQ, SQ);
                }
            }

            // ── Check highlight ──────────
            if (whiteKingPos &&
                row === whiteKingPos[0] &&
                col === whiteKingPos[1]) {
                ctx.fillStyle = CHECK_SQ;
                ctx.fillRect(x, y, SQ, SQ);
            }

            // ── Selected square ──────────
            if (selectedSquare &&
                selectedSquare[0] === row &&
                selectedSquare[1] === col) {
                ctx.fillStyle = SELECTED_SQ;
                ctx.fillRect(x, y, SQ, SQ);
            }

            // ── Valid move indicators ────
            const isValidDest = validMoves.some(
                m => m[0] === row && m[1] === col
            );
            if (isValidDest) {
                if (board[row][col]) {
                    // Capture move → draw ring around piece
                    ctx.strokeStyle = MOVE_RING;
                    ctx.lineWidth   = 6;
                    ctx.beginPath();
                    ctx.arc(
                        x + SQ/2, y + SQ/2,
                        SQ/2 - 4, 0, Math.PI * 2
                    );
                    ctx.stroke();
                } else {
                    // Empty square → draw dot in center
                    ctx.fillStyle = MOVE_DOT;
                    ctx.beginPath();
                    ctx.arc(
                        x + SQ/2, y + SQ/2,
                        SQ * 0.17, 0, Math.PI * 2
                    );
                    ctx.fill();
                }
            }

            // ── Draw piece ───────────────
            const piece = board[row][col];
            if (piece) {
                drawPiece(piece, x, y);
            }
        }
    }
}


function drawPiece(piece, x, y) {
    const symbol = SYMBOLS[piece.color][piece.type];

    ctx.font         = `${SQ * 0.74}px serif`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';

    const cx = x + SQ / 2;
    const cy = y + SQ / 2 + 2;

    // Shadow for depth
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillText(symbol, cx + 2, cy + 2);

    // Main piece
    ctx.fillStyle = piece.color === 'white' ? '#ffffff' : '#1a1a1a';
    ctx.fillText(symbol, cx, cy);

    // Subtle outline on white pieces for visibility
    if (piece.color === 'white') {
        ctx.strokeStyle = 'rgba(0,0,0,0.4)';
        ctx.lineWidth   = 0.5;
        ctx.strokeText(symbol, cx, cy);
    }
}


// ════════════════════════════════════════
// USER INTERACTION
// ════════════════════════════════════════

canvas.addEventListener('click', async (e) => {
    if (isThinking || gameOver) return;

    const rect  = canvas.getBoundingClientRect();
    const scaleX = canvas.width  / rect.width;
    const scaleY = canvas.height / rect.height;

    const col = Math.floor((e.clientX - rect.left) * scaleX / SQ);
    const row = Math.floor((e.clientY - rect.top)  * scaleY / SQ);

    if (row < 0 || row > 7 || col < 0 || col > 7) return;

    const clickedPiece = board[row][col];

    // ── Case 1: Piece already selected ──
    if (selectedSquare) {
        const [sr, sc] = selectedSquare;

        // Clicked a valid destination → make the move
        if (validMoves.some(m => m[0] === row && m[1] === col)) {
            await playerMove(sr, sc, row, col);
            return;
        }

        // Clicked another own white piece → reselect
        if (clickedPiece && clickedPiece.color === 'white') {
            await selectPiece(row, col);
            return;
        }

        // Clicked elsewhere → deselect
        selectedSquare = null;
        validMoves     = [];
        drawBoard();
        setStatus('♟', 'Your turn — select a piece', '');
        return;
    }

    // ── Case 2: No piece selected ────────
    if (clickedPiece && clickedPiece.color === 'white') {
        await selectPiece(row, col);
    }
});


async function selectPiece(row, col) {
    selectedSquare = [row, col];
    validMoves     = [];
    drawBoard();
    setStatus('⏳', 'Loading moves...', '');

    try {
        const res = await fetch(`/game/${GAME_ID}/moves/`, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  CSRF_TOKEN,
            },
            body: JSON.stringify({ row, col }),
        });

        const data = await res.json();
        validMoves = data.moves || [];
        drawBoard();

        if (validMoves.length === 0) {
            setStatus('⚠️', 'No legal moves for this piece', '');
        } else {
            setStatus('✅', `${validMoves.length} moves available`, '');
        }

    } catch (err) {
        setStatus('❌', 'Connection error', '');
    }
}


async function playerMove(fromRow, fromCol, toRow, toCol) {
    isThinking = true;
    setStatus('🤔', 'AI is thinking...', '');

    // Track captured piece before move
    const target = board[toRow][toCol];
    if (target) capturedByWhite.push(target);

    // Optimistic update — show move immediately
    board[toRow][toCol]     = board[fromRow][fromCol];
    board[fromRow][fromCol] = null;
    lastMove       = { from: [fromRow, fromCol], to: [toRow, toCol] };
    selectedSquare = null;
    validMoves     = [];
    inCheck        = false;
    drawBoard();
    updateCaptured();
    addMoveToHistory(fromRow, fromCol, toRow, toCol, 'white');

    try {
        const res = await fetch(`/game/${GAME_ID}/move/`, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  CSRF_TOKEN,
            },
            body: JSON.stringify({
                from_row: fromRow,
                from_col: fromCol,
                to_row:   toRow,
                to_col:   toCol,
            }),
        });

        const data = await res.json();

        if (data.error) {
            setStatus('❌', data.error, '');
            isThinking = false;
            return;
        }

        // Update board with authoritative server state
        board = data.board;

        // Track AI's captured piece
        if (data.ai_move) {
            const [ar, ac] = data.ai_move.from;
            const [br, bc] = data.ai_move.to;
            lastMove       = { from: [ar, ac], to: [br, bc] };
            addMoveToHistory(ar, ac, br, bc, 'black');
        }

        // Update check state
        inCheck = data.in_check || false;
        drawBoard();
        updateCaptured();

        // ── Handle game over states ──────
        if (data.status === 'white_won') {
            showModal('🏆', 'You Won!', 'Checkmate — the AI has no escape!');
            setStatus('🏆', 'Checkmate! You won!', 'win');
            gameOver = true;
            return;
        }
        if (data.status === 'black_won') {
            showModal('😔', 'You Lost!', 'Checkmate — your king is trapped!');
            setStatus('😔', 'Checkmate! You lost!', 'lose');
            gameOver = true;
            return;
        }
        if (data.status === 'draw') {
            showModal('🤝', 'Draw!', 'Stalemate — no legal moves available!');
            setStatus('🤝', 'Stalemate! Draw!', 'draw');
            gameOver = true;
            return;
        }

        // ── Game continues ───────────────
        if (inCheck) {
            setStatus('⚠️', 'Check! Protect your king!', 'check');
        } else {
            setStatus('♟', 'Your turn — select a piece', '');
        }

        // Highlight AI and player turn cards
        updateTurnIndicator('white');

    } catch (err) {
        setStatus('❌', 'Connection error. Please refresh.', '');
    }

    isThinking = false;
}


// ════════════════════════════════════════
// UI HELPER FUNCTIONS
// ════════════════════════════════════════

function setStatus(icon, text, type) {
    document.getElementById('status-icon').textContent = icon;
    document.getElementById('status-text').textContent = text;

    const box = document.getElementById('status-box');
    box.className = 'status-box ' + type;
}


function showModal(icon, title, message) {
    document.getElementById('modal-icon').textContent    = icon;
    document.getElementById('modal-title').textContent   = title;
    document.getElementById('modal-message').textContent = message;
    document.getElementById('game-over-modal').classList.remove('hidden');
}


function updateTurnIndicator(turn) {
    const youCard = document.querySelector('.you-card');
    const aiCard  = document.querySelector('.ai-card');

    if (turn === 'white') {
        youCard.classList.add('active-turn');
        aiCard.classList.remove('active-turn');
    } else {
        aiCard.classList.add('active-turn');
        youCard.classList.remove('active-turn');
    }
}


function addMoveToHistory(fr, fc, tr, tc, color) {
    moveCount++;
    const cols    = 'abcdefgh';
    const rows    = '87654321';
    const from    = cols[fc] + rows[fr];
    const to      = cols[tc] + rows[tr];
    const history = document.getElementById('move-history');

    // Remove "no moves" placeholder
    const placeholder = history.querySelector('.no-moves');
    if (placeholder) placeholder.remove();

    const entry    = document.createElement('div');
    entry.className = `move-entry ${color}-move`;
    entry.innerHTML = `
        <span class="move-num">${Math.ceil(moveCount/2)}.</span>
        <span>${color === 'white' ? '⬜' : '⬛'} ${from} → ${to}</span>
    `;
    history.appendChild(entry);

    // Auto scroll to bottom
    history.scrollTop = history.scrollHeight;
}


function updateCaptured() {
    const whiteEl = document.getElementById('captured-by-white');
    const blackEl = document.getElementById('captured-by-black');

    whiteEl.textContent = capturedByWhite
        .map(p => CAPTURE_SYMBOLS.black[p.type])
        .join('');

    blackEl.textContent = capturedByBlack
        .map(p => CAPTURE_SYMBOLS.white[p.type])
        .join('');
}


// ════════════════════════════════════════
// INITIALIZATION
// ════════════════════════════════════════

// Draw the board on page load
drawBoard();
updateTurnIndicator('white');

// If game was already over when page loaded
if (gameOver) {
    if (GAME_STATUS === 'white_won') {
        showModal('🏆', 'You Won!', 'Checkmate!');
        setStatus('🏆', 'You won this game!', 'win');
    } else if (GAME_STATUS === 'black_won') {
        showModal('😔', 'You Lost!', 'Checkmate!');
        setStatus('😔', 'You lost this game!', 'lose');
    } else if (GAME_STATUS === 'draw') {
        showModal('🤝', 'Draw!', 'Stalemate!');
        setStatus('🤝', 'This game was a draw!', 'draw');
    }
} else {
    setStatus('♟', 'Your turn — select a white piece', '');
}