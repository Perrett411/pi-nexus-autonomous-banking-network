// Network analytics & reconciliation panel: charts the audit log and
// flags anomalies at a glance. DOM built via createElement/textContent.
'use strict';

const chartEl = document.getElementById('tx-chart');
const anomalyList = document.getElementById('anomaly-list');
const anomalyCount = document.getElementById('anomaly-count');
const reportEl = document.getElementById('reconcile-report');
const runBtn = document.getElementById('run-reconcile');

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function fmtTime(epochSeconds) {
    return new Date(epochSeconds * 1000).toLocaleTimeString();
}

function renderAnalytics(data) {
    // bar chart — one bar per minute bucket, spikes highlighted
    const max = Math.max(1, ...data.series.map(b => b.transactions));
    const spikeTs = new Set(
        data.anomalies.filter(a => a.type === 'TRANSACTION_SPIKE').map(a => a.t));
    chartEl.replaceChildren();
    for (const bucket of data.series) {
        const bar = el('div', 'bar' + (spikeTs.has(bucket.t) ? ' spike' : ''));
        const pct = bucket.transactions ? Math.max(8, (bucket.transactions / max) * 100) : 2;
        bar.style.height = pct + '%';
        bar.title = `${fmtTime(bucket.t)} — ${bucket.transactions} tx`;
        chartEl.appendChild(bar);
    }

    // anomaly list
    anomalyList.replaceChildren();
    for (const a of data.anomalies) {
        const item = el('div', 'anomaly-item ' + a.severity);
        item.appendChild(el('span', 'severity-chip ' + a.severity, a.severity.toUpperCase()));
        item.appendChild(el('span', 'anomaly-msg', a.message));
        item.appendChild(el('span', 'time', fmtTime(a.t)));
        anomalyList.appendChild(item);
    }
    anomalyCount.textContent = data.anomalies.length + ' detected';
    if (!data.anomalies.length) {
        anomalyList.appendChild(el('div', 'anomaly-item none',
            'No anomalies detected — network nominal.'));
    }
}

function renderReport(report) {
    reportEl.replaceChildren();
    const head = el('div', 'report-head');
    head.appendChild(el('span', 'report-status ' + (report.compliant ? 'ok' : 'bad'),
        report.status));
    head.appendChild(el('span', 'time',
        'Generated ' + new Date(report.generated_at).toLocaleString()));
    reportEl.appendChild(head);

    const grid = el('div', 'report-grid');
    const rows = [
        ['Transactions scanned', report.transactions_scanned],
        ['Violations corrected', report.violations_corrected],
        ['Violations flagged', report.violations_flagged],
        ['Block state', `${report.blocks_verified} / ${report.blocks_total} (${report.block_state})`],
        ['Audit chain', report.audit_chain_intact ? 'INTACT' : 'BROKEN'],
        ['Merkle root', (report.merkle_root || '').slice(0, 16) + '…'],
    ];
    for (const [label, value] of rows) {
        const cell = el('div', 'report-cell');
        cell.appendChild(el('span', 'stat-label', label));
        cell.appendChild(el('span', 'stat-value', String(value)));
        grid.appendChild(cell);
    }
    reportEl.appendChild(grid);

    const checks = el('ul', 'check-list');
    for (const c of report.checks) checks.appendChild(el('li', null, c));
    reportEl.appendChild(checks);
}

async function fetchAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        if (res.ok) renderAnalytics(await res.json());
    } catch (err) { /* next poll retries */ }
}

async function fetchReport(method) {
    try {
        const res = await fetch('/api/reconciliation', { method: method || 'GET' });
        if (res.ok) renderReport(await res.json());
    } catch (err) { /* next poll retries */ }
}

runBtn.addEventListener('click', () => {
    runBtn.disabled = true;
    fetchReport('POST').finally(() => { runBtn.disabled = false; });
});

fetchAnalytics();
fetchReport('GET');
setInterval(fetchAnalytics, 6000);
setInterval(() => fetchReport('GET'), 60000);
