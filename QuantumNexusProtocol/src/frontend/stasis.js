// Quantum Stasis Field panel: seal status, Merkle integrity, privacy
// coverage and the pre-threat (predictive QKD) register. DOM built via
// createElement/textContent — never innerHTML.
'use strict';

const stasisThreatList = document.getElementById('stasis-threats');

function stasisEl(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function setStasisValue(id, value, cls) {
    const node = document.getElementById(id);
    node.textContent = value;
    if (cls !== undefined) node.className = 'stat-value ' + cls;
}

function renderStasis(data) {
    setStasisValue('stasis-field',
        data.field_active ? 'SEALED' : 'INACTIVE',
        data.field_active ? 'ok' : 'bad');
    setStasisValue('stasis-integrity',
        data.merkle_match ? 'VERIFIED' : 'BREACH',
        data.merkle_match ? 'ok' : 'bad');
    setStasisValue('stasis-identities', data.identities_protected);
    setStasisValue('stasis-identity-root',
        data.identity_merkle_root ? data.identity_merkle_root.slice(0, 12) + '…' : '…');
    setStasisValue('stasis-threats', data.threats_neutralized);
    const levelClass = { NOMINAL: 'ok', ELEVATED: 'warn', CRITICAL: 'bad' };
    setStasisValue('stasis-level', data.threat_level,
        levelClass[data.threat_level] || '');

    stasisThreatList.replaceChildren();
    const threats = data.recent_threats || [];
    if (!threats.length) {
        stasisThreatList.appendChild(stasisEl('div', 'anomaly-item none',
            'No threats detected — stasis field nominal.'));
        return;
    }
    for (const t of threats) {
        const item = stasisEl('div', 'anomaly-item ' + t.severity);
        item.appendChild(stasisEl('span', 'severity-chip ' + t.severity,
            t.severity.toUpperCase()));
        item.appendChild(stasisEl('span', 'anomaly-msg',
            `${t.description} (tx ${String(t.tx_id).slice(0, 11)}…) — ${t.action}`));
        item.appendChild(stasisEl('span', 'time',
            new Date(t.detected_at).toLocaleTimeString()));
        stasisThreatList.appendChild(item);
    }
}

async function fetchStasis() {
    try {
        const res = await fetch('/api/stasis');
        if (res.ok) renderStasis(await res.json());
    } catch (err) { /* next poll retries */ }
}

fetchStasis();
setInterval(fetchStasis, 6000);
