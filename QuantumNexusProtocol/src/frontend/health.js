// Dedicated health monitoring view: continuously renders the live health
// of every quantum consensus function, active alerts (block reconciliation
// failures, chain breaks, stasis breaches), the zero-violation enforcement
// gate, legal compliance & rights, and the negotiation/dispute register.
// All external data is rendered via textContent / createElement.
'use strict';

let connected = false;

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function fmtTime(iso) {
    const d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleTimeString();
}

function setStatus(ok) {
    connected = ok;
    const dot = document.getElementById('live-dot');
    const status = document.getElementById('live-status');
    dot.className = 'dot ' + (ok ? 'pulse' : 'down');
    status.textContent = ok ? 'LIVE' : 'RECONNECTING';
}

function statusChip(status) {
    const chip = el('span', 'status-chip ' + (status === 'HEALTHY' || status === 'PASS' ? 'ok'
        : status === 'PENDING' ? 'warn' : 'bad'));
    chip.textContent = status === 'HEALTHY' ? 'HEALTHY' : status;
    return chip;
}

function setStatusValue(id, value, cls) {
    const node = document.getElementById(id);
    node.textContent = value;
    node.className = 'stat-value' + (cls ? ' ' + cls : '');
}

// ---- alerts banner ---------------------------------------------------------
function renderAlerts(alerts) {
    const banner = document.getElementById('alerts-banner');
    const active = alerts.filter((a) => !a.cleared_at);
    banner.textContent = '';
    if (!active.length) {
        banner.hidden = true;
        return;
    }
    banner.hidden = false;
    banner.appendChild(el('h3', 'alerts-title', 'Active alerts'));
    for (const alert of active) {
        const item = el('div', 'alert-item ' + alert.severity);
        item.appendChild(el('span', 'severity-chip ' + alert.severity, alert.severity.toUpperCase()));
        item.appendChild(el('span', 'alert-msg', alert.message));
        item.appendChild(el('span', 'time', fmtTime(alert.raised_at)));
        banner.appendChild(item);
    }
}

// ---- consensus function health ---------------------------------------------
function renderFunctions(checks) {
    const grid = document.getElementById('function-health');
    grid.textContent = '';
    for (const check of checks) {
        const card = el('article', 'check-card ' + (check.status === 'HEALTHY' ? 'ok'
            : check.status === 'PENDING' ? 'warn' : 'bad'));
        const head = el('div', 'check-head');
        head.appendChild(el('span', 'check-name',
            check.name.replace(/_/g, ' ')));
        head.appendChild(statusChip(check.status));
        card.appendChild(head);
        card.appendChild(el('div', 'check-detail', check.detail));
        const meta = el('div', 'card-meta');
        if (check.latency_ms !== null && check.latency_ms !== undefined) {
            meta.appendChild(el('span', 'chip', check.latency_ms + ' ms'));
        }
        if (check.failures > 0) {
            meta.appendChild(el('span', 'chip fail', 'failures: ' + check.failures));
        }
        if (check.last_run) {
            meta.appendChild(el('span', 'time', 'checked ' + fmtTime(check.last_run)));
        }
        card.appendChild(meta);
        grid.appendChild(card);
    }
    const passing = checks.filter((c) => c.status === 'HEALTHY').length;
    setStatusValue('hm-checks', passing + ' / ' + checks.length,
        passing === checks.length ? 'ok' : 'warn');
}

// ---- zero-violation enforcement ---------------------------------------------
function renderEnforcement(enforcement) {
    setStatusValue('ev-mode', enforcement.mode,
        enforcement.mode === 'ACTIVE' ? 'ok' : 'bad');
    setStatusValue('ev-screened', enforcement.screened);
    setStatusValue('ev-stopped', enforcement.blocked, 'ok');
    setStatusValue('ev-accepted', enforcement.accepted_violations,
        enforcement.accepted_violations === 0 ? 'ok' : 'bad');
    setStatusValue('hm-blocked', enforcement.blocked, 'ok');

    const list = document.getElementById('quarantine-list');
    list.textContent = '';
    if (!enforcement.quarantined.length) {
        const empty = el('div', 'q-item none', 'No violations quarantined — the gate is holding clean.');
        list.appendChild(empty);
        return;
    }
    for (const item of enforcement.quarantined.slice(0, 12)) {
        const card = el('article', 'q-item');
        const head = el('div', 'check-head');
        head.appendChild(el('span', 'check-name mono', item.tx_id || 'unknown id'));
        head.appendChild(el('span', 'severity-chip high', 'STOPPED'));
        card.appendChild(head);
        card.appendChild(el('div', 'check-detail',
            (item.sender || '?') + ' → ' + (item.recipient || '?') +
            ' · ' + (item.reasons || []).join(', ')));
        const meta = el('div', 'card-meta');
        meta.appendChild(el('span', 'time', fmtTime(item.stopped_at)));
        const btn = el('button', 'mini-btn');
        btn.type = 'button';
        btn.dataset.action = 'dispute';
        btn.dataset.id = item.tx_id || '';
        btn.dataset.party = item.sender || '';
        btn.dataset.reasons = (item.reasons || []).join(', ');
        btn.textContent = 'Dispute';
        meta.appendChild(btn);
        card.appendChild(meta);
        list.appendChild(card);
    }
}

// ---- health report -----------------------------------------------------------
function renderHealth(data) {
    setStatusValue('hm-overall', data.overall,
        data.overall === 'OPERATIONAL' ? 'ok'
            : data.overall === 'DEGRADED' ? 'warn' : 'bad');
    const active = data.alerts.filter((a) => !a.cleared_at).length;
    setStatusValue('hm-alerts', active, active ? 'bad' : 'ok');
    renderAlerts(data.alerts);
    renderFunctions(data.checks);
    renderEnforcement(data.enforcement);

    const rec = data.last_reconciliation;
    if (rec) {
        const recNode = document.getElementById('hm-reconciliation');
        recNode.textContent = rec.status + ' · ' + rec.blocks_verified + '/' +
            rec.blocks_total + ' blocks · ' + fmtTime(rec.generated_at);
        recNode.className = 'stat-value ' + (rec.block_state === 'RECONCILED' ? 'ok' : 'bad');
    }
}

// ---- compliance, fairness & rights -------------------------------------------
function renderCompliance(data) {
    const verdict = document.getElementById('compliance-verdict');
    verdict.textContent = data.verdict;
    verdict.className = 'report-status ' + (data.verdict === 'COMPLIANT' ? 'ok' : 'bad');

    const fwList = document.getElementById('framework-list');
    fwList.textContent = '';
    for (const fw of data.frameworks) {
        const row = el('article', 'fw-item');
        const head = el('div', 'check-head');
        head.appendChild(el('span', 'check-name', fw.code + ' — ' + fw.name));
        head.appendChild(statusChip(fw.passes ? 'PASS' : 'FAIL'));
        row.appendChild(head);
        row.appendChild(el('div', 'fw-jurisdiction', fw.jurisdiction));
        row.appendChild(el('div', 'check-detail', 'Control: ' + fw.control + ' — ' + fw.detail));
        fwList.appendChild(row);
    }

    const fairnessPanel = document.getElementById('fairness-panel');
    fairnessPanel.textContent = '';
    const fair = data.fairness;
    const head = el('div', 'check-head');
    head.appendChild(el('span', 'check-name', 'Inclusion Monitor — ' + fair.rule));
    head.appendChild(statusChip(fair.verdict === 'FAIR' ? 'PASS' : 'FAIL'));
    fairnessPanel.appendChild(head);
    fairnessPanel.appendChild(el('div', 'check-detail', fair.window +
        ' · typical participant inclusion: ' + fair.benchmark));
    const bars = el('div', 'fairness-bars');
    for (const [participant, count] of Object.entries(fair.counts)) {
        const bar = el('div', 'fairness-bar');
        bar.appendChild(el('span', 'fb-label', participant));
        const track = el('div', 'fb-track');
        const fill = el('div', 'fb-fill');
        fill.style.width = (fair.benchmark
            ? Math.min(100, Math.round(100 * count / fair.benchmark)) : 0) + '%';
        if (fair.benchmark && count < 0.8 * fair.benchmark) {
            fill.className = 'fb-fill low';
        }
        track.appendChild(fill);
        bar.appendChild(track);
        bar.appendChild(el('span', 'fb-count', String(count)));
        bars.appendChild(bar);
    }
    fairnessPanel.appendChild(bars);
    for (const finding of fair.findings) {
        fairnessPanel.appendChild(el('div', 'finding', finding));
    }

    const rightsPanel = document.getElementById('rights-panel');
    rightsPanel.textContent = '';
    const columns = [
        ['As a business', data.rights.business],
        ['As a person', data.rights.person],
        ['Ethical standards', data.rights.ethical_standards],
    ];
    for (const [title, items] of columns) {
        const col = el('div', 'rights-col');
        col.appendChild(el('h4', 'rights-title', title));
        for (const item of items) {
            col.appendChild(el('div', 'right-item', item));
        }
        rightsPanel.appendChild(col);
    }

    const note = document.getElementById('negotiation-note');
    note.textContent = data.negotiation.standing_offer;
    renderDisputes(data.negotiation.disputes);
}

// ---- negotiation & disputes ---------------------------------------------------
function renderDisputes(disputes) {
    const list = document.getElementById('dispute-list');
    list.textContent = '';
    if (!disputes.length) {
        list.appendChild(el('div', 'q-item none',
            'No disputes open. Quarantined items above can be disputed at any time — disputing never affects your standing.'));
        return;
    }
    for (const dispute of disputes) {
        const card = el('article', 'dispute-card ' + dispute.state.toLowerCase());
        const head = el('div', 'check-head');
        head.appendChild(el('span', 'check-name mono', dispute.id + ' · ' + dispute.party));
        head.appendChild(el('span', 'status-chip ' +
            (dispute.state === 'RESOLVED' ? 'ok' : dispute.state === 'ESCALATED' ? 'bad' : 'warn'),
            dispute.state));
        card.appendChild(head);
        card.appendChild(el('div', 'check-detail',
            dispute.subject_type.replace(/_/g, ' ') + ' ' + (dispute.subject_id || '') +
            ' — claim: ' + dispute.claim));
        card.appendChild(el('div', 'check-detail', 'Network: ' + dispute.network_position));
        if (dispute.resolution) {
            card.appendChild(el('div', 'resolution', dispute.resolution));
        }
        if (dispute.state === 'NEGOTIATING') {
            const actions = el('div', 'dispute-actions');
            for (const [offer, label] of [
                ['release_refund', 'Offer: release & refund'],
                ['resubmit_clean', 'Offer: resubmit corrected'],
                ['escalate', 'Escalate to human review'],
            ]) {
                const btn = el('button', 'mini-btn');
                btn.type = 'button';
                btn.dataset.action = 'offer';
                btn.dataset.dispute = dispute.id;
                btn.dataset.offer = offer;
                btn.textContent = label;
                actions.appendChild(btn);
            }
            card.appendChild(actions);
        }
        const meta = el('div', 'card-meta');
        meta.appendChild(el('span', 'time',
            (dispute.resolved_at ? 'settled ' : 'opened ') +
            fmtTime(dispute.resolved_at || dispute.opened_at)));
        card.appendChild(meta);
        list.appendChild(card);
    }
}

// ---- actions --------------------------------------------------------------------
async function postNegotiation(payload) {
    try {
        const res = await fetch('/api/negotiation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (res.ok) renderDisputes(data.disputes);
    } catch (err) {
        setStatus(false);
    }
}

document.addEventListener('click', (event) => {
    const btn = event.target.closest('button[data-action]');
    if (!btn) return;
    if (btn.dataset.action === 'dispute') {
        postNegotiation({
            action: 'open',
            party: btn.dataset.party,
            subject_id: btn.dataset.id,
            subject_type: 'QUARANTINED_TRANSACTION',
            claim: 'violation reason(s): ' + btn.dataset.reasons +
                ' — party disputes the finding and asserts the right to negotiate',
        });
    } else if (btn.dataset.action === 'offer') {
        postNegotiation({
            action: 'propose',
            dispute_id: btn.dataset.dispute,
            offer: btn.dataset.offer,
        });
    }
});

// ---- polling ---------------------------------------------------------------------
async function pollHealth() {
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        renderHealth(await res.json());
        setStatus(true);
    } catch (err) {
        setStatus(false);
    }
}

async function pollCompliance() {
    try {
        const res = await fetch('/api/compliance');
        if (!res.ok) return;
        renderCompliance(await res.json());
    } catch (err) { /* health poll reports connection status */ }
}

pollHealth();
pollCompliance();
setInterval(pollHealth, 2000);
setInterval(pollCompliance, 6000);
