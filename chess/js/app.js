const game = new ChessGame();

let scene, camera, renderer;
let boardSquares3D = [];
let pieces3D = {};

let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();
let draggedPiece = null;
let dragPlane = new THREE.Plane();
let planeNormal = new THREE.Vector3(0, 1, 0);
let planeIntersection = new THREE.Vector3();
let originalSquare = null;
let possibleMoveLocations = [];

const COLORS = {
  lightSquare: 0xffffff,
  darkSquare: 0x111111,
  outline: 0x000000,
  whitePiece: 0xeeeeee,
  blackPiece: 0x222222,
  neonGreen: 0x00ff66,
  neonPink: 0xff0055,
  bg: 0xe5e5e5
};

function init3D() {
  const container = document.getElementById('canvas-container');

  scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.bg);

  const aspect = window.innerWidth / window.innerHeight;
  camera = new THREE.PerspectiveCamera(40, aspect, 1, 1000);
  camera.position.set(10, 11, 10);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
  dirLight.position.set(12, 18, 8);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.width = 2048;
  dirLight.shadow.mapSize.height = 2048;
  dirLight.shadow.camera.near = 0.5;
  dirLight.shadow.camera.far = 40;
  const d = 10;
  dirLight.shadow.camera.left = -d;
  dirLight.shadow.camera.right = d;
  dirLight.shadow.camera.top = d;
  dirLight.shadow.camera.bottom = -d;
  dirLight.shadow.bias = -0.0005;
  scene.add(dirLight);

  dragPlane.setFromNormalAndCoplanarPoint(planeNormal, new THREE.Vector3(0, 0.45, 0));

  createBoard3D();
  spawnPieces3D();

  window.addEventListener('resize', onWindowResize);
  window.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);

  initNetwork(handleRemoteMove, handleRemoteRestart);

  updateUI();
  animate();
}

function addBrutalEdges(mesh, color = COLORS.outline, thickness = 1) {
  const edges = new THREE.EdgesGeometry(mesh.geometry);
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: color, linewidth: thickness }));
  mesh.add(line);
}

function createBoard3D() {
  const squareGeo = new THREE.BoxGeometry(1, 0.3, 1);

  for (let r = 0; r < 8; r++) {
    boardSquares3D[r] = [];
    for (let c = 0; c < 8; c++) {
      const isLight = (r + c) % 2 === 0;
      const squareMat = new THREE.MeshLambertMaterial({
        color: isLight ? COLORS.lightSquare : COLORS.darkSquare
      });

      const squareMesh = new THREE.Mesh(squareGeo, squareMat);
      squareMesh.position.set(c - 3.5, 0.15, r - 3.5);
      squareMesh.receiveShadow = true;

      addBrutalEdges(squareMesh, COLORS.outline);
      squareMesh.userData = { row: r, col: c, originalColor: squareMesh.material.color.clone() };

      scene.add(squareMesh);
      boardSquares3D[r][c] = squareMesh;
    }
  }
}

function buildPieceGeometry(type) {
  const group = new THREE.Group();
  let mainMesh;
  const matMetal = new THREE.MeshPhongMaterial({ flatShading: true });

  switch (type.toLowerCase()) {
    case 'p':
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.35, 0.5, 5), matMetal);
      base.position.y = 0.25;
      const head = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.3), matMetal);
      head.position.y = 0.6;
      group.add(base);
      group.add(head);
      break;

    case 'r':
      mainMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 0.8, 5), matMetal);
      mainMesh.position.y = 0.4;
      group.add(mainMesh);
      break;

    case 'n':
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.7, 0.3), matMetal);
      body.position.y = 0.35;
      const face = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.5), matMetal);
      face.position.set(0, 0.6, 0.1);
      group.add(body);
      group.add(face);
      break;

    case 'b':
      mainMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.35, 0.9, 3), matMetal);
      mainMesh.position.y = 0.45;
      group.add(mainMesh);
      break;

    case 'q':
      const qBody = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.4, 1.1, 8), matMetal);
      qBody.position.y = 0.55;
      const qCrown = new THREE.Mesh(new THREE.SphereGeometry(0.2, 5, 5), matMetal);
      qCrown.position.y = 1.15;
      group.add(qBody);
      group.add(qCrown);
      break;

    case 'k':
      const kBody = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.1, 0.4), matMetal);
      kBody.position.y = 0.55;
      const crossV = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.4, 0.15), matMetal);
      crossV.position.set(0, 1.2, 0);
      const crossH = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.15, 0.15), matMetal);
      crossH.position.set(0, 1.25, 0);
      group.add(kBody);
      group.add(crossV);
      group.add(crossH);
      break;
  }

  group.traverse(child => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
      addBrutalEdges(child, COLORS.outline, 1.5);
    }
  });

  return group;
}

function spawnPieces3D() {
  for (let key in pieces3D) {
    scene.remove(pieces3D[key]);
  }
  pieces3D = {};

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const piece = game.getPiece(r, c);
      if (piece) {
        createPiece3D(piece, r, c);
      }
    }
  }
}

function createPiece3D(type, r, c) {
  const pieceGroup = buildPieceGeometry(type);
  const isWhite = type === type.toUpperCase();

  const colorHex = isWhite ? COLORS.whitePiece : COLORS.blackPiece;
  pieceGroup.traverse(child => {
    if (child.isMesh) {
      child.material.color.setHex(colorHex);
    }
  });

  pieceGroup.position.set(c - 3.5, 0.3, r - 3.5);
  pieceGroup.userData = { row: r, col: c, type: type, isWhite: isWhite };

  scene.add(pieceGroup);
  pieces3D[`${r}_${c}`] = pieceGroup;
}

function highlightTiles(moves) {
  resetTileHighlights();
  possibleMoveLocations = moves;
  moves.forEach(m => {
    const targetSquare = game.getPiece(m.r, m.c);
    const tile = boardSquares3D[m.r][m.c];
    if (targetSquare) {
      tile.material.color.setHex(COLORS.neonPink);
    } else {
      tile.material.color.setHex(COLORS.neonGreen);
    }
  });
}

function resetTileHighlights() {
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const tile = boardSquares3D[r][c];
      tile.material.color.copy(tile.userData.originalColor);
    }
  }
  possibleMoveLocations = [];
}

function updateMouseCoords(e) {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
}

function onPointerDown(e) {
  if (e.target.tagName === 'BUTTON' || e.target.closest('.interactive')) return;

  // Online turn restriction
  if (myColor !== null && game.turn !== myColor) return;

  updateMouseCoords(e);
  raycaster.setFromCamera(mouse, camera);

  const draggableObjects = [];
  for (let key in pieces3D) {
    draggableObjects.push(pieces3D[key]);
  }

  const intersects = raycaster.intersectObjects(draggableObjects, true);

  if (intersects.length > 0) {
    let obj = intersects[0].object;
    while (obj.parent && obj.parent !== scene) {
      obj = obj.parent;
    }

    const data = obj.userData;
    const color = game.getPieceColor(data.type);

    if (color === game.turn && !game.isGameOver) {
      draggedPiece = obj;
      originalSquare = { r: data.row, c: data.col };
      draggedPiece.position.y = 0.95;

      const moves = game.getValidMoves(originalSquare.r, originalSquare.c);
      highlightTiles(moves);
    }
  }
}

function onPointerMove(e) {
  if (!draggedPiece) return;

  updateMouseCoords(e);
  raycaster.setFromCamera(mouse, camera);

  if (raycaster.ray.intersectPlane(dragPlane, planeIntersection)) {
    draggedPiece.position.x = planeIntersection.x;
    draggedPiece.position.z = planeIntersection.z;
  }
}

function onPointerUp(e) {
  if (!draggedPiece) return;

  const targetCol = Math.round(draggedPiece.position.x + 3.5);
  const targetRow = Math.round(draggedPiece.position.z + 3.5);

  let moved = false;
  const isValid = possibleMoveLocations.some(m => m.r === targetRow && m.c === targetCol);

  if (isValid) {
    const fromR = originalSquare.r;
    const fromC = originalSquare.c;

    executeMove(fromR, fromC, targetRow, targetCol);
    sendMoveToOpponent(fromR, fromC, targetRow, targetCol);
    moved = true;
  }

  if (!moved) {
    draggedPiece.position.set(originalSquare.c - 3.5, 0.3, originalSquare.r - 3.5);
  }

  draggedPiece = null;
  originalSquare = null;
  resetTileHighlights();
  updateUI();
}

function executeMove(fromR, fromC, toR, toC) {
  const result = game.makeMove(fromR, fromC, toR, toC);

  if (result.captured) {
    const enemyKey = `${toR}_${toC}`;
    if (pieces3D[enemyKey]) {
      scene.remove(pieces3D[enemyKey]);
      delete pieces3D[enemyKey];
    }
  }

  const pieceMesh = pieces3D[`${fromR}_${fromC}`];
  if (pieceMesh) {
    delete pieces3D[`${fromR}_${fromC}`];
    pieces3D[`${toR}_${toC}`] = pieceMesh;

    pieceMesh.userData.row = toR;
    pieceMesh.userData.col = toC;

    const currentPiece = game.getPiece(toR, toC);
    if (currentPiece !== pieceMesh.userData.type) {
      scene.remove(pieceMesh);
      createPiece3D(currentPiece, toR, toC);
    } else {
      pieceMesh.position.set(toC - 3.5, 0.3, toR - 3.5);
    }
  }
}

function handleRemoteMove(fromR, fromC, toR, toC) {
  executeMove(fromR, fromC, toR, toC);
  updateUI();
}

function handleRemoteRestart() {
  game.reset();
  resetTileHighlights();
  spawnPieces3D();
  updateUI();
}

function onWindowResize() {
  const aspect = window.innerWidth / window.innerHeight;
  camera.aspect = aspect;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}

const statusBar = document.getElementById('status-bar');
const restartBtn = document.getElementById('restart-btn');
const moveLog = document.getElementById('move-log');

function updateUI() {
  if (game.isGameOver) {
    if (game.isCheck) {
      const winner = game.turn === 'W' ? 'ЧЕРНЫЕ' : 'БЕЛЫЕ';
      statusBar.textContent = `МАТ! ПОБЕДИЛИ ${winner}!`;
    } else {
      statusBar.textContent = 'ПАТ! НИЧЬЯ!';
    }
    statusBar.className = 'status-bar check';
  } else {
    const turnText = game.turn === 'W' ? 'БЕЛЫЕ' : 'ЧЕРНЫЕ';
    statusBar.textContent = game.isCheck 
      ? `ШАХ! ХОД: ${turnText}` 
      : `ХОД: ${turnText}`;
    
    statusBar.className = `status-bar ${game.turn === 'W' ? 'white-turn' : 'black-turn'} ${game.isCheck ? 'check' : ''}`;
  }

  moveLog.innerHTML = game.history
    .map((entry, idx) => `<div class="log-entry">${idx + 1}. ${entry}</div>`)
    .reverse()
    .join('');
}

restartBtn.addEventListener('click', () => {
  game.reset();
  resetTileHighlights();
  spawnPieces3D();
  updateUI();
  sendRestartToOpponent();
});

window.onload = init3D;
