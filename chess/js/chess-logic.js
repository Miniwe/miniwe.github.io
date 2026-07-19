class ChessGame {
  constructor() {
    this.reset();
  }

  reset() {
    this.board = this.createInitialBoard();
    this.turn = 'W'; // 'W' - Белые, 'B' - Черные
    this.history = [];
    this.captured = { W: [], B: [] };
    this.isCheck = false;
    this.isGameOver = false;
  }

  createInitialBoard() {
    return [
      ['r','n','b','q','k','b','n','r'],
      ['p','p','p','p','p','p','p','p'],
      [null,null,null,null,null,null,null,null],
      [null,null,null,null,null,null,null,null],
      [null,null,null,null,null,null,null,null],
      [null,null,null,null,null,null,null,null],
      ['P','P','P','P','P','P','P','P'],
      ['R','N','B','Q','K','B','N','R']
    ];
  }

  getPiece(r, c) {
    if (r < 0 || r > 7 || c < 0 || c > 7) return null;
    return this.board[r][c];
  }

  isWhite(piece) {
    return piece && piece === piece.toUpperCase();
  }

  getPieceColor(piece) {
    if (!piece) return null;
    return this.isWhite(piece) ? 'W' : 'B';
  }

  getValidMoves(r, c) {
    const piece = this.board[r][c];
    if (!piece || this.getPieceColor(piece) !== this.turn || this.isGameOver) {
      return [];
    }

    const pseudoMoves = this.getPseudoLegalMoves(r, c);
    return pseudoMoves.filter(m => !this.moveLeavesKingInCheck(r, c, m.r, m.c));
  }

  getPseudoLegalMoves(r, c) {
    const piece = this.board[r][c];
    if (!piece) return [];

    const type = piece.toLowerCase();
    const color = this.getPieceColor(piece);
    const moves = [];

    const addMove = (tr, tc) => {
      if (tr < 0 || tr > 7 || tc < 0 || tc > 7) return false;
      const target = this.board[tr][tc];
      if (!target) {
        moves.push({ r: tr, c: tc });
        return true;
      }
      if (this.getPieceColor(target) !== color) {
        moves.push({ r: tr, c: tc });
      }
      return false;
    };

    if (type === 'p') {
      const dir = color === 'W' ? -1 : 1;
      const startRow = color === 'W' ? 6 : 1;

      if (r + dir >= 0 && r + dir <= 7 && !this.board[r + dir][c]) {
        moves.push({ r: r + dir, c });
        if (r === startRow && !this.board[r + 2 * dir][c]) {
          moves.push({ r: r + 2 * dir, c });
        }
      }
      [-1, 1].forEach(dc => {
        const tr = r + dir, tc = c + dc;
        if (tr >= 0 && tr <= 7 && tc >= 0 && tc <= 7) {
          const target = this.board[tr][tc];
          if (target && this.getPieceColor(target) !== color) {
            moves.push({ r: tr, c: tc });
          }
        }
      });
    }

    if (type === 'n') {
      const offsets = [
        [-2,-1],[-2,1],[-1,-2],[-1,2],
        [1,-2],[1,2],[2,-1],[2,1]
      ];
      offsets.forEach(([dr, dc]) => addMove(r + dr, c + dc));
    }

    if (type === 'k') {
      const offsets = [
        [-1,-1],[-1,0],[-1,1],
        [0,-1],       [0,1],
        [1,-1], [1,0], [1,1]
      ];
      offsets.forEach(([dr, dc]) => addMove(r + dr, c + dc));
    }

    if (type === 'r' || type === 'q') {
      const dirs = [[-1,0],[1,0],[0,-1],[0,1]];
      dirs.forEach(([dr, dc]) => {
        let tr = r + dr, tc = c + dc;
        while (tr >= 0 && tr <= 7 && tc >= 0 && tc <= 7) {
          if (!addMove(tr, tc)) break;
          tr += dr; tc += dc;
        }
      });
    }

    if (type === 'b' || type === 'q') {
      const dirs = [[-1,-1],[-1,1],[1,-1],[1,1]];
      dirs.forEach(([dr, dc]) => {
        let tr = r + dr, tc = c + dc;
        while (tr >= 0 && tr <= 7 && tc >= 0 && tc <= 7) {
          if (!addMove(tr, tc)) break;
          tr += dr; tc += dc;
        }
      });
    }

    return moves;
  }

  makeMove(fromR, fromC, toR, toC) {
    const piece = this.board[fromR][fromC];
    const target = this.board[toR][toC];

    if (target) {
      const targetColor = this.getPieceColor(target);
      this.captured[targetColor].push(target);
    }

    this.board[toR][toC] = piece;
    this.board[fromR][fromC] = null;

    if (piece.toLowerCase() === 'p') {
      if ((this.turn === 'W' && toR === 0) || (this.turn === 'B' && toR === 7)) {
        this.board[toR][toC] = this.turn === 'W' ? 'Q' : 'q';
      }
    }

    const cols = ['a','b','c','d','e','f','g','h'];
    const moveStr = `${piece.toUpperCase()}: ${cols[fromC]}${8-fromR} ➔ ${cols[toC]}${8-toR}${target ? ' ✕' : ''}`;
    this.history.push(moveStr);

    this.turn = this.turn === 'W' ? 'B' : 'W';
    this.isCheck = this.isInCheck(this.turn);

    if (!this.hasAnyLegalMoves(this.turn)) {
      this.isGameOver = true;
    }

    return { captured: target, moveStr };
  }

  findKing(color) {
    const kingChar = color === 'W' ? 'K' : 'k';
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        if (this.board[r][c] === kingChar) return { r, c };
      }
    }
    return null;
  }

  isInCheck(color) {
    const kingPos = this.findKing(color);
    if (!kingPos) return false;

    const opponentColor = color === 'W' ? 'B' : 'W';
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        if (this.getPieceColor(this.board[r][c]) === opponentColor) {
          const moves = this.getPseudoLegalMoves(r, c);
          if (moves.some(m => m.r === kingPos.r && m.c === kingPos.c)) {
            return true;
          }
        }
      }
    }
    return false;
  }

  moveLeavesKingInCheck(fromR, fromC, toR, toC) {
    const origFrom = this.board[fromR][fromC];
    const origTo = this.board[toR][toC];

    this.board[toR][toC] = origFrom;
    this.board[fromR][fromC] = null;

    const inCheck = this.isInCheck(this.turn);

    this.board[fromR][fromC] = origFrom;
    this.board[toR][toC] = origTo;

    return inCheck;
  }

  hasAnyLegalMoves(color) {
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        if (this.getPieceColor(this.board[r][c]) === color) {
          if (this.getValidMoves(r, c).length > 0) return true;
        }
      }
    }
    return false;
  }
}
