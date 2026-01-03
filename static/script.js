const socket = io();

// --- Socket Listeners ---
socket.on('connect', () => {
    console.log("Connected to server");
});

socket.on('game_update', (state) => {
    renderGame(state);
});

socket.on('error', (msg) => {
    alert(msg);
});

// --- Actions ---
function startGame() {
    socket.emit('start_game');
}

function changeName() {
    const nameInput = document.getElementById('name-input');
    const newName = nameInput.value;
    if (newName) {
        socket.emit('change_name', newName);
        nameInput.value = '';
    }
}

function takeChip(value, source) {
    socket.emit('take_chip', { chip_value: value, source: source });
}

function returnChip() {
    socket.emit('return_chip');
}

function toggleSettle() {
    socket.emit('toggle_settle');
}

// --- Rendering ---
function renderGame(state) {
    const phaseEl = document.getElementById('phase-display');
    const vaultEl = document.getElementById('vault-count');
    const alarmEl = document.getElementById('alarm-count');
    const commCardsEl = document.getElementById('community-cards');
    const chipBankEl = document.getElementById('chip-bank');
    const opponentsEl = document.getElementById('opponents-row');
    const myCardsEl = document.getElementById('my-cards');
    const myHistoryEl = document.getElementById('my-history'); // NEW
    const myChipSlot = document.getElementById('my-chip-slot');
    const settleBtn = document.getElementById('settle-btn');
    const returnBtn = document.getElementById('return-btn');
    const myNameEl = document.getElementById('my-name');

    // 1. Status & Score
    const statusText = state.phase === "LOBBY" ? "Waiting for Players..." : `${state.phase} - ${state.chip_color} Chips`;
    phaseEl.innerText = statusText;

    vaultEl.innerText = state.vaults;
    alarmEl.innerText = state.alarms;

    myNameEl.innerText = state.me.name;

    if (state.phase === "RESULT") {
        phaseEl.innerHTML = `
            <div style="color: ${state.result_message.includes('SUCCESS') || state.result_message.includes('WIN') ? '#2ecc71' : '#e74c3c'}">
                ${state.result_message}
            </div>
            <button onclick="startGame()" style="margin-top:10px;">
                ${(state.vaults >= 3 || state.alarms >= 3) ? 'New Game' : 'Next Heist'}
            </button>
        `;
    }

    // 2. Community Cards
    commCardsEl.innerHTML = '';
    state.community_cards.forEach(card => {
        commCardsEl.appendChild(createCardDiv(card));
    });

    // 3. Chip Bank
    chipBankEl.innerHTML = '';
    state.chips_available.forEach(val => {
        const btn = document.createElement('button');
        btn.className = `chip chip-${state.chip_color.toLowerCase()}`;
        btn.innerText = `★ ${val}`;
        btn.onclick = () => takeChip(val, 'center');
        chipBankEl.appendChild(btn);
    });

    // 4. Opponents
    opponentsEl.innerHTML = '';
    state.players.forEach(p => {
        if (p.sid === state.me.sid) return;

        const pDiv = document.createElement('div');
        pDiv.className = `player-card ${p.is_settled ? 'settled' : 'thinking'}`;

        let chipHtml = '<span class="no-chip">No Chip</span>';
        if (p.chip) {
            chipHtml = `<button class="chip chip-${state.chip_color.toLowerCase()}" 
                        onclick="takeChip(${p.chip}, '${p.sid}')">
                        ★ ${p.chip}
                        </button>`;
        }

        let historyHtml = '';
        if (p.chip_history && p.chip_history.length > 0) {
            historyHtml = '<div class="chip-history">';
            p.chip_history.forEach(h => {
                historyHtml += `<span class="mini-chip chip-${h.color.toLowerCase()}">${h.value}</span>`;
            });
            historyHtml += '</div>';
        }

        let handHtml = '<div class="p-hand">🂠 🂠</div>';
        if (p.hand && p.hand.length > 0) {
            handHtml = '<div class="card-container small">';
            p.hand.forEach(c => {
                const cDiv = createCardDiv(c);
                cDiv.classList.add('small-card');
                handHtml += cDiv.outerHTML;
            });
            handHtml += '</div>';
        }

        pDiv.innerHTML = `
            <div class="p-name">${p.name}</div>
            <div class="p-status">${p.is_settled ? '✔ SETTLED' : '...'}</div>
            ${handHtml}
            <div class="p-chip">${chipHtml}</div>
            ${historyHtml}
        `;
        opponentsEl.appendChild(pDiv);
    });

    // 5. My State
    // My Cards
    myCardsEl.innerHTML = '';
    if(state.me.hand.length > 0) {
        state.me.hand.forEach(c => myCardsEl.appendChild(createCardDiv(c)));
    }

    // NEW: My History
    myHistoryEl.innerHTML = '';
    if (state.me.chip_history && state.me.chip_history.length > 0) {
        state.me.chip_history.forEach(h => {
            const span = document.createElement('span');
            span.className = `mini-chip chip-${h.color.toLowerCase()}`;
            span.innerText = h.value;
            myHistoryEl.appendChild(span);
        });
    }

    // My Chip (current)
    if (state.me.chip) {
        myChipSlot.innerHTML = `<div class="chip chip-${state.chip_color.toLowerCase()}">★ ${state.me.chip}</div>`;
        settleBtn.disabled = false;
        returnBtn.disabled = state.me.is_settled;
    } else {
        myChipSlot.innerHTML = '<span class="placeholder">Pick a chip</span>';
        settleBtn.disabled = true;
        returnBtn.disabled = true;
    }

    if (state.me.is_settled) {
        settleBtn.innerText = "Cancel Settle";
        settleBtn.classList.add('active');
        chipBankEl.classList.add('disabled');
    } else {
        settleBtn.innerText = "I'm Settled";
        settleBtn.classList.remove('active');
        chipBankEl.classList.remove('disabled');
    }
}

function createCardDiv(card) {
    const div = document.createElement('div');
    div.className = 'card';
    div.innerText = card.str;
    if (['♥', '♦'].includes(card.suit)) div.classList.add('red-suit');
    return div;
}