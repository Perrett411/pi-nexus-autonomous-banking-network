// Live dashboard: polls the audit-log API and renders every transaction
// and consensus update in real time. All external data is rendered via
// textContent / createElement — never innerHTML.
'use strict';

let cursor = -1;
let connected = false;

const txFeed = document.getElementById('transactions-feed');
const ccFeed = document.getElementById('consensus-feed');
const MAX_CARDS = 100;

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function formatTime(iso) {
    const d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleTimeString();
}

function shortHash(hash) {
    return hash ? hash.slice(0, 12) + '…' : '';
}

function prependCard(feed, card) {
    feed.prepend(card);
    while (feed.children.length > MAX_CARDS) {
        feed.removeChild(feed.lastChild);
    }
}

function renderTransaction(entry) {
    const tx = (entry.payload && entry.payload.transaction) || {};
    const card = el('article', 'card tx');
    card.appendChild(el('div', 'card-head',
        `${tx.sender || '?'} → ${tx.recipient || '?'}`));
    card.appendChild(el('div', 'card-amount', `${tx.amount} QNP`));
    const meta = el('div', 'card-meta');
    meta.appendChild(el('span', 'chip', tx.quantum_channel || 'tx'));
    meta.appendChild(el('span', 'chip mono', shortHash(entry.payload_hash)));
    meta.appendChild(el('span', 'time', formatTime(entry.payload.recorded_at)));
    card.appendChild(meta);
    prependCard(txFeed, card);
}

function renderConsensus(entry) {
    const payload = entry.payload || {};
    const card = el('article', 'card cc');
    card.appendChild(el('div', 'card-head',
        (payload.change_type || 'CONSENSUS').replace(/_/g, ' ')));
    const details = payload.details || {};
    const meta = el('div', 'card-meta');
    if (details && Object.keys(details).length) {
        const dl = el('div', 'detail-list');
        for (const [key, value] of Object.entries(details)) {
            dl.appendChild(el('div', 'detail',
                `${key.replace(/_/g, ' ')}: ${String(value)}`));
        }
        card.appendChild(dl);
    }
    meta.appendChild(el('span', 'chip mono', shortHash(entry.payload_hash)));
    meta.appendChild(el('span', 'time', formatTime(payload.recorded_at)));
    card.appendChild(meta);
    prependCard(ccFeed, card);
}

function updateStats(stats) {
    document.getElementById('stat-transactions').textContent = stats.transactions;
    document.getElementById('stat-consensus').textContent = stats.consensus_changes;
    document.getElementById('stat-validators').textContent = stats.validators;
    document.getElementById('stat-blocks').textContent = stats.blocks_finalized;
    const integrity = document.getElementById('stat-integrity');
    integrity.textContent = stats.chain_intact ? 'VERIFIED' : 'TAMPERED';
    integrity.className = 'stat-value ' + (stats.chain_intact ? 'ok' : 'bad');
    document.getElementById('stat-merkle').textContent =
        stats.merkle_root ? shortHash(stats.merkle_root) : '…';
}

function setStatus(ok) {
    if (ok === connected) return;
    connected = ok;
    const dot = document.getElementById('live-dot');
    const status = document.getElementById('live-status');
    dot.className = 'dot ' + (ok ? 'pulse' : 'down');
    status.textContent = ok ? 'LIVE' : 'RECONNECTING';
}

async function poll() {
    try {
        const res = await fetch(`/api/events?after=${cursor}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        updateStats(data.stats);
        for (const entry of data.entries) {
            if (entry.entry_type === 'TRANSACTION') {
                renderTransaction(entry);
            } else {
                renderConsensus(entry);
            }
        }
        cursor = data.total - 1;
        setStatus(true);
    } catch (err) {
        setStatus(false);
    }
}

poll();
setInterval(poll, 1500);
