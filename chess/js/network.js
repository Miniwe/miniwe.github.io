let peer = null;
let conn = null;
let myColor = null; // null = local 2-player mode, 'W' or 'B' in online mode

function initNetwork(onMoveReceivedCallback, onRestartCallback) {
  peer = new Peer();

  const myIdDisplay = document.getElementById('my-id-display');
  const netStatus = document.getElementById('net-status');
  const connectBtn = document.getElementById('connect-btn');
  const peerIdInput = document.getElementById('peer-id-input');

  peer.on('open', (id) => {
    myIdDisplay.textContent = `ID: ${id}`;
  });

  peer.on('connection', (connection) => {
    conn = connection;
    myColor = 'W'; // Host plays White
    setupConnection(onMoveReceivedCallback, onRestartCallback);
    netStatus.textContent = 'ОНЛАЙН: ИГРОК ПОДКЛЮЧИЛСЯ (ВЫ: БЕЛЫЕ)';
    netStatus.style.color = '#00aa44';
  });

  connectBtn.addEventListener('click', () => {
    const targetId = peerIdInput.value.trim();
    if (!targetId) return;

    conn = peer.connect(targetId);
    myColor = 'B'; // Guest plays Black
    setupConnection(onMoveReceivedCallback, onRestartCallback);
    netStatus.textContent = 'ОНЛАЙН: ПОДКЛЮЧЕНО (ВЫ: ЧЕРНЫЕ)';
    netStatus.style.color = '#00aa44';
  });
}

function setupConnection(onMoveReceivedCallback, onRestartCallback) {
  conn.on('data', (data) => {
    if (data.type === 'MOVE') {
      onMoveReceivedCallback(data.fromR, data.fromC, data.toR, data.toC);
    } else if (data.type === 'RESTART') {
      onRestartCallback();
    }
  });

  conn.on('close', () => {
    const netStatus = document.getElementById('net-status');
    netStatus.textContent = 'СОЕДИНЕНИЕ РАЗОРВАНО';
    netStatus.style.color = '#ff0055';
    myColor = null;
  });
}

function sendMoveToOpponent(fromR, fromC, toR, toC) {
  if (conn && conn.open) {
    conn.send({
      type: 'MOVE',
      fromR, fromC, toR, toC
    });
  }
}

function sendRestartToOpponent() {
  if (conn && conn.open) {
    conn.send({ type: 'RESTART' });
  }
}
