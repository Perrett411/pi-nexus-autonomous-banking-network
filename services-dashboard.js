/* Pi Nexus — Services Dashboard
   Implements the six services from the Services section as live features,
   each action connected to the QCF-DRIVE quantum consensus engine (/api). */
(function () {
  'use strict';

  var panelsHost = document.getElementById('dashboard-panels');
  if (!panelsHost) return;

  /* ---------------- helpers ---------------- */

  function api(path, options) {
    var opts = Object.assign({ headers: { 'Content-Type': 'application/json' } }, options || {});
    if (opts.body) opts.body = JSON.stringify(opts.body);
    return fetch(path, opts).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) throw new Error(data.error || 'Request failed (' + response.status + ')');
        return data;
      });
    });
  }

  function el(html) {
    var wrap = document.createElement('div');
    wrap.innerHTML = html.trim();
    return wrap.firstChild;
  }

  var INPUT_CLASS = 'w-full px-4 py-2 rounded-lg bg-gray-900 text-white border border-gray-700 focus:outline-none focus:border-orange-500';
  var BTN_CLASS = 'px-5 py-2 rounded-lg font-semibold bg-orange-600 hover:bg-orange-500 text-white transition-colors disabled:opacity-50';
  var BTN_DANGER = 'px-3 py-1 rounded-lg text-sm font-semibold bg-red-900 hover:bg-red-800 text-red-200 border border-red-800 transition-colors';

  function consensusBadge(record) {
    if (!record || typeof record.consensusPassed !== 'boolean') return '';
    var passed = record.consensusPassed;
    var ratio = record.quantum ? (record.quantum.agreementRatio * 100).toFixed(1) : '—';
    var votes = record.quantum ? record.quantum.nodeVotes.map(function (v) {
      return '<span class="inline-block w-3 h-3 rounded-full mr-1 ' + (v === record.quantum.baseVote ? 'bg-green-500' : 'bg-red-500') + '" title="node vote: ' + v + '"></span>';
    }).join('') : '';
    return '<div class="mt-3 flex flex-wrap items-center gap-2">' +
      '<span class="px-3 py-1 rounded-full text-xs font-bold ' + (passed ? 'bg-green-900 text-green-300 border border-green-700' : 'bg-red-900 text-red-300 border border-red-700') + '">' +
      'QUANTUM CONSENSUS ' + (passed ? 'PASSED' : 'REJECTED') + '</span>' +
      '<span class="text-xs text-gray-400">' + ratio + '% agreement · ' + record.nodes + ' nodes · ' + (record.quantum ? record.quantum.method : '') + '</span>' +
      votes + '</div>';
  }

  function statCard(label, value) {
    return '<div class="bg-gray-900 rounded-lg p-4 border border-gray-700">' +
      '<div class="text-xs text-gray-400 uppercase tracking-wide">' + label + '</div>' +
      '<div class="text-2xl font-bold mt-1 text-white">' + value + '</div></div>';
  }

  function statusChip(status) {
    var map = {
      confirmed: 'text-green-300 bg-green-900 border-green-700',
      rejected_by_consensus: 'text-red-300 bg-red-900 border-red-700',
      validated: 'text-green-300 bg-green-900 border-green-700',
      quarantined: 'text-yellow-300 bg-yellow-900 border-yellow-700',
      pending_scan: 'text-gray-300 bg-gray-700 border-gray-600',
      settled: 'text-blue-300 bg-blue-900 border-blue-700',
      pending: 'text-gray-300 bg-gray-700 border-gray-600',
      approved: 'text-green-300 bg-green-900 border-green-700',
      pending_manual_review: 'text-yellow-300 bg-yellow-900 border-yellow-700',
      resolved_by_ai: 'text-green-300 bg-green-900 border-green-700',
      escalated_to_human_agent: 'text-yellow-300 bg-yellow-900 border-yellow-700',
      connected: 'text-green-300 bg-green-900 border-green-700'
    };
    return '<span class="px-2 py-0.5 rounded-full text-xs border ' + (map[status] || 'text-gray-300 bg-gray-700 border-gray-600') + '">' + status.replace(/_/g, ' ') + '</span>';
  }

  function messageArea(element, text, kind) {
    element.innerHTML = '<p class="text-sm ' + (kind === 'error' ? 'text-red-400' : 'text-gray-300') + '">' + text + '</p>';
  }

  function panelShell(id, icon, title, description) {
    return '<div id="' + id + '" class="bg-gray-800 rounded-lg p-6 border border-gray-700 scroll-mt-24">' +
      '<div class="flex items-center gap-4">' +
      '<i class="fas ' + icon + ' text-3xl neon-text"></i>' +
      '<div><h3 class="text-2xl font-semibold text-white">' + title + '</h3>' +
      '<p class="text-sm text-gray-400 mt-1">' + description + '</p></div></div>' +
      '<div data-body class="mt-6"></div></div>';
  }

  /* ---------------- consensus engine panel ---------------- */

  function buildConsensusPanel() {
    var body = document.getElementById('panel-consensus').querySelector('[data-body]');

    // Static layout: stats/history refresh in place so the test result persists.
    body.innerHTML =
      '<div data-stats></div>' +
      '<div class="mt-4 flex flex-wrap items-center gap-4"><button id="consensus-test" class="' + BTN_CLASS + '">Run Consensus Test</button>' +
      '<div id="consensus-result" class="flex-1 min-w-0"></div></div>' +
      '<div id="consensus-history" class="mt-4"></div>';

    function refresh() {
      return api('/api/consensus').then(function (data) {
        var s = data.stats;
        body.querySelector('[data-stats]').innerHTML =
          '<div class="grid grid-cols-2 md:grid-cols-4 gap-4">' +
          statCard('Validation Engine', data.qcf.validationEngine) +
          statCard('Consensus Threshold', (data.qcf.consensusThreshold * 100).toFixed(0) + '%') +
          statCard('Active Branch Nodes', s.activeBranches) +
          statCard('Pass Rate', s.passRate === null ? '—' : (s.passRate * 100).toFixed(1) + '% (' + s.passed + '/' + s.totalDecisions + ')') +
          '</div>';

        var history = data.history.filter(function (r) { return r.consensusPassed !== null; }).slice(0, 5);
        body.querySelector('#consensus-history').innerHTML =
          '<h4 class="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-2">Recent consensus decisions</h4>' +
          '<ul class="space-y-1 text-sm text-gray-400">' +
          (history.length ? history.map(function (r) {
            return '<li class="flex justify-between gap-2"><span>' + r.action.replace(/_/g, ' ') + '</span>' +
              '<span class="' + (r.consensusPassed ? 'text-green-400' : 'text-red-400') + '">' + (r.consensusPassed ? 'passed' : 'rejected') + '</span></li>';
          }).join('') : '<li>No decisions yet.</li>') + '</ul>';
      });
    }

    document.getElementById('consensus-test').addEventListener('click', function (event) {
      var button = event.currentTarget;
      button.disabled = true;
      api('/api/consensus', { method: 'POST', body: { decision: { label: 'Dashboard consensus test', source: 'services-dashboard' } } })
        .then(function (record) {
          document.getElementById('consensus-result').innerHTML = consensusBadge(record);
          refresh();
        })
        .catch(function (err) { messageArea(document.getElementById('consensus-result'), err.message, 'error'); })
        .then(function () { button.disabled = false; });
    });

    refresh();
  }

  /* ---------------- real-time analytics panel ---------------- */

  function buildAnalyticsPanel() {
    var body = document.getElementById('panel-analytics').querySelector('[data-body]');
    var metricsBox = el('<div></div>');
    var resultBox = el('<div class="mt-3"></div>');

    var form = el(
      '<form class="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">' +
      '<input name="sender" class="' + INPUT_CLASS + '" placeholder="Sender" required>' +
      '<input name="recipient" class="' + INPUT_CLASS + '" placeholder="Recipient" required>' +
      '<input name="amount" type="number" min="0.01" step="0.01" class="' + INPUT_CLASS + '" placeholder="Amount" required>' +
      '<select name="currency" class="' + INPUT_CLASS + '"><option>PI</option><option>USD</option><option>EUR</option></select>' +
      '<button type="submit" class="' + BTN_CLASS + '">Submit via Consensus</button></form>'
    );

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var f = event.target;
      messageArea(resultBox, 'Validating transaction through quantum consensus…');
      api('/api/analytics/transactions', {
        method: 'POST',
        body: { sender: f.sender.value, recipient: f.recipient.value, amount: f.amount.value, currency: f.currency.value }
      }).then(function (tx) {
        resultBox.innerHTML =
          '<div class="mt-3 p-3 rounded-lg bg-gray-900 border border-gray-700">' +
          '<p class="text-sm text-gray-300">Transaction <span class="font-mono text-orange-400">' + tx.id.slice(0, 8) + '</span> — ' +
          tx.amount + ' ' + tx.currency + ' from ' + tx.sender + ' to ' + tx.recipient +
          ' → <strong>' + tx.status.replace(/_/g, ' ') + '</strong></p>' +
          consensusBadge(tx.consensus) + '</div>';
        refreshMetrics();
      }).catch(function (err) { messageArea(resultBox, err.message, 'error'); });
    });

    function refreshMetrics() {
      api('/api/analytics/metrics').then(function (m) {
        metricsBox.innerHTML =
          '<div class="grid grid-cols-2 md:grid-cols-4 gap-4">' +
          statCard('Total Transactions', m.totalTransactions) +
          statCard('Confirmed', m.confirmed) +
          statCard('Total Volume', m.totalVolume.toLocaleString()) +
          statCard('Consensus Pass Rate', m.consensus.passRate === null ? '—' : (m.consensus.passRate * 100).toFixed(1) + '%') +
          '</div>' +
          '<div class="mt-4 overflow-x-auto"><table class="w-full text-sm text-gray-300">' +
          '<thead><tr class="text-left text-xs uppercase text-gray-400"><th class="py-2">ID</th><th>Sender → Recipient</th><th>Amount</th><th>Status</th><th>Security</th><th>Settlement</th></tr></thead><tbody>' +
          (m.recent.length ? m.recent.map(function (t) {
            return '<tr class="border-t border-gray-700"><td class="py-2 font-mono text-xs">' + t.id.slice(0, 8) + '</td>' +
              '<td>' + t.sender + ' → ' + t.recipient + '</td><td>' + t.amount + ' ' + t.currency + '</td>' +
              '<td>' + statusChip(t.status) + '</td><td>' + statusChip(t.securityStatus) + '</td><td>' + statusChip(t.settlementStatus) + '</td></tr>';
          }).join('') : '<tr><td colspan="6" class="py-3 text-gray-500">No transactions yet — submit one above.</td></tr>') +
          '</tbody></table></div>';
      });
    }

    body.append(form, resultBox, metricsBox);
    refreshMetrics();
  }

  /* ---------------- enhanced security panel ---------------- */

  function buildSecurityPanel() {
    var body = document.getElementById('panel-security').querySelector('[data-body]');
    var resultBox = el('<div class="mt-3"></div>');
    var button = el('<button class="' + BTN_CLASS + '">Run Security Scan</button>');

    button.addEventListener('click', function () {
      button.disabled = true;
      messageArea(resultBox, 'Scanning transactions against AML rules under quantum consensus…');
      api('/api/security/scan', { method: 'POST' }).then(function (report) {
        resultBox.innerHTML =
          '<div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-3">' +
          statCard('Scanned', report.confirmedScanned) +
          statCard('Clean', report.clean) +
          statCard('Flagged', report.flaggedCount) +
          statCard('Validated', report.validated) +
          statCard('Quarantined', report.quarantined) +
          '</div>' +
          '<p class="mt-3 text-sm text-gray-300">Threat level: <strong class="' +
          (report.threatLevel === 'low' ? 'text-green-400' : report.threatLevel === 'elevated' ? 'text-yellow-400' : 'text-red-400') +
          '">' + report.threatLevel.toUpperCase() + '</strong> · AML threshold: ' + report.amlThreshold.toLocaleString() + '</p>' +
          (report.results.length ? '<div class="mt-3 space-y-2">' + report.results.map(function (r) {
            return '<div class="p-3 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-300">' +
              'Transaction <span class="font-mono text-orange-400">' + r.transaction.id.slice(0, 8) + '</span> (' +
              r.transaction.amount + ' ' + r.transaction.currency + ') → ' + statusChip(r.transaction.securityStatus) +
              consensusBadge(r.consensus) + '</div>';
          }).join('') + '</div>' : '<p class="mt-3 text-sm text-gray-500">No flagged transactions.</p>');
      }).catch(function (err) { messageArea(resultBox, err.message, 'error'); })
        .then(function () { button.disabled = false; });
    });

    body.append(button, resultBox);
  }

  /* ---------------- seamless integration panel ---------------- */

  function buildIntegrationsPanel() {
    var body = document.getElementById('panel-integrations').querySelector('[data-body]');
    var branchList = el('<div class="mt-4"></div>');
    var resultBox = el('<div class="mt-3"></div>');

    var form = el(
      '<form class="flex flex-col md:flex-row gap-3">' +
      '<input name="branchId" class="' + INPUT_CLASS + '" placeholder="Branch ID (e.g. Australia_Branch)" required>' +
      '<button type="submit" class="' + BTN_CLASS + '">Connect via Consensus</button></form>'
    );

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      connectAction('/connect', { branchId: form.branchId.value });
      form.branchId.value = '';
    });

    function connectAction(path, payload) {
      messageArea(resultBox, 'Requesting quantum consensus decision…');
      api('/api/integrations' + path, { method: 'POST', body: payload }).then(function (data) {
        renderBranches(data.branches);
        var ok = path === '/connect' ? data.connected : data.disconnected;
        resultBox.innerHTML = (ok
          ? '<p class="text-sm text-green-400">Branch ' + (path === '/connect' ? 'connected to' : 'disconnected from') + ' QCF-DRIVE.</p>'
          : '<p class="text-sm text-yellow-400">Action not executed (' + (data.reason || 'consensus rejected') + ').</p>') +
          consensusBadge(data.record);
      }).catch(function (err) { messageArea(resultBox, err.message, 'error'); });
    }

    function renderBranches(branches) {
      branchList.innerHTML =
        '<h4 class="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-2">Connected branches (consensus nodes)</h4>' +
        '<div class="space-y-2">' + branches.map(function (b) {
          return '<div class="flex items-center justify-between gap-3 p-3 rounded-lg bg-gray-900 border border-gray-700">' +
            '<div><span class="text-white font-semibold">' + b.name + '</span> ' + statusChip(b.status) +
            '<span class="text-xs text-gray-500 block">quantum-secured · connected ' + new Date(b.connectedAt).toLocaleString() + '</span></div>' +
            '<button data-branch="' + b.branchId + '" class="' + BTN_DANGER + '">Disconnect</button></div>';
        }).join('') + '</div>';

      branchList.querySelectorAll('button[data-branch]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          connectAction('/disconnect', { branchId: btn.getAttribute('data-branch') });
        });
      });
    }

    body.append(form, resultBox, branchList);
    api('/api/integrations').then(function (data) { renderBranches(data.branches); });
  }

  /* ---------------- automated processes panel ---------------- */

  function buildAutomationPanel() {
    var body = document.getElementById('panel-automation').querySelector('[data-body]');
    var resultBox = el('<div class="mt-3"></div>');

    var workflows = [
      { id: 'automated_settlement', label: 'Automated Settlement', icon: 'fa-bolt' },
      { id: 'compliance_report', label: 'Compliance Report', icon: 'fa-file-alt' },
      { id: 'fraud_sweep', label: 'Fraud Sweep', icon: 'fa-shield-virus' }
    ];

    var bar = el('<div class="flex flex-wrap gap-3">' + workflows.map(function (w) {
      return '<button data-workflow="' + w.id + '" class="' + BTN_CLASS + '"><i class="fas ' + w.icon + ' mr-2"></i>' + w.label + '</button>';
    }).join('') + '</div>');

    bar.querySelectorAll('button').forEach(function (button) {
      button.addEventListener('click', function () {
        var workflow = button.getAttribute('data-workflow');
        messageArea(resultBox, 'Executing ' + workflow.replace(/_/g, ' ') + ' under quantum consensus…');
        api('/api/automation/run', { method: 'POST', body: { workflow: workflow } }).then(function (data) {
          var detail = '';
          if (workflow === 'automated_settlement') {
            detail = data.executed
              ? '<p class="text-sm text-green-400 mt-2">Settled ' + data.settledCount + ' transaction(s), total volume ' + data.volume.toLocaleString() + '.</p>'
              : '<p class="text-sm text-yellow-400 mt-2">Settlement blocked: consensus rejected the batch.</p>';
          } else if (workflow === 'compliance_report') {
            detail = (data.published
              ? '<p class="text-sm text-green-400 mt-2">Report published to the consensus ledger.</p>'
              : '<p class="text-sm text-yellow-400 mt-2">Publication blocked: consensus rejected the report.</p>') +
              '<pre class="mt-2 p-3 rounded-lg bg-gray-900 border border-gray-700 text-xs text-gray-300 overflow-x-auto">' +
              JSON.stringify(data.report, null, 2) + '</pre>';
          } else {
            detail = '<p class="text-sm text-gray-300 mt-2">Sweep executed: ' + data.scan.flaggedCount + ' flagged, ' +
              data.scan.quarantined + ' quarantined, threat level ' + data.scan.threatLevel + '.</p>';
          }
          resultBox.innerHTML = detail + consensusBadge(data.consensus);
        }).catch(function (err) { messageArea(resultBox, err.message, 'error'); });
      });
    });

    body.append(bar, resultBox);
  }

  /* ---------------- user privacy panel ---------------- */

  function buildPrivacyPanel() {
    var body = document.getElementById('panel-privacy').querySelector('[data-body]');
    var list = el('<div class="mt-4"></div>');
    var resultBox = el('<div class="mt-3"></div>');

    var form = el(
      '<form class="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">' +
      '<select name="type" class="' + INPUT_CLASS + '"><option value="data_export">Data Export</option><option value="right_to_be_forgotten">Right to be Forgotten</option></select>' +
      '<input name="subject" type="email" class="' + INPUT_CLASS + '" placeholder="Subject (e.g. user@bank.com)" required>' +
      '<button type="submit" class="' + BTN_CLASS + '">Submit via Consensus</button></form>'
    );

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      messageArea(resultBox, 'Quantum consensus is deciding on your privacy request…');
      api('/api/privacy/requests', { method: 'POST', body: { type: form.type.value, subject: form.subject.value } })
        .then(function (request) {
          var detail = request.status === 'approved'
            ? (request.type === 'right_to_be_forgotten'
              ? 'Approved — ' + request.affectedRecords + ' record(s) anonymized.'
              : 'Approved — ' + (request.export ? request.export.length : 0) + ' record(s) exported.')
            : 'Consensus could not approve this request automatically; it is pending manual review.';
          resultBox.innerHTML = '<p class="text-sm text-gray-300">' + detail + '</p>' + consensusBadge(request.consensus);
          refreshList();
        }).catch(function (err) { messageArea(resultBox, err.message, 'error'); });
    });

    function refreshList() {
      api('/api/privacy/requests').then(function (data) {
        list.innerHTML = '<h4 class="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-2">Requests</h4>' +
          (data.requests.length ? '<ul class="space-y-2">' + data.requests.map(function (r) {
            return '<li class="p-3 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-300 flex justify-between gap-2">' +
              '<span>' + r.type.replace(/_/g, ' ') + ' — ' + r.subject + '</span>' + statusChip(r.status) + '</li>';
          }).join('') + '</ul>' : '<p class="text-sm text-gray-500">No privacy requests yet.</p>');
      });
    }

    body.append(form, resultBox, list);
    refreshList();
  }

  /* ---------------- 24/7 support panel ---------------- */

  function buildSupportPanel() {
    var body = document.getElementById('panel-support').querySelector('[data-body]');
    var list = el('<div class="mt-4"></div>');
    var resultBox = el('<div class="mt-3"></div>');

    var form = el(
      '<form class="grid grid-cols-1 gap-3">' +
      '<input name="subject" class="' + INPUT_CLASS + '" placeholder="Subject" required>' +
      '<textarea name="message" rows="3" class="' + INPUT_CLASS + '" placeholder="Describe your issue…" required></textarea>' +
      '<button type="submit" class="' + BTN_CLASS + ' w-full md:w-auto">Open Ticket via Consensus</button></form>'
    );

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      messageArea(resultBox, 'Generating AI response and validating through quantum consensus…');
      api('/api/support/tickets', { method: 'POST', body: { subject: form.subject.value, message: form.message.value } })
        .then(function (ticket) {
          resultBox.innerHTML =
            '<div class="p-4 rounded-lg bg-gray-900 border border-gray-700">' +
            '<p class="text-sm text-gray-400">' + ticket.message + '</p>' +
            '<p class="mt-2 text-sm text-orange-300"><strong>AI response:</strong> ' + ticket.response + '</p>' +
            statusChip(ticket.status) + consensusBadge(ticket.consensus) + '</div>';
          refreshList();
        }).catch(function (err) { messageArea(resultBox, err.message, 'error'); });
    });

    function refreshList() {
      api('/api/support/tickets').then(function (data) {
        list.innerHTML = '<h4 class="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-2">Tickets</h4>' +
          (data.tickets.length ? '<ul class="space-y-2">' + data.tickets.slice(0, 5).map(function (t) {
            return '<li class="p-3 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-300 flex justify-between gap-2">' +
              '<span>' + t.subject + '</span>' + statusChip(t.status) + '</li>';
          }).join('') + '</ul>' : '<p class="text-sm text-gray-500">No tickets yet.</p>');
      });
    }

    body.append(form, resultBox, list);
    refreshList();
  }

  /* ---------------- build ---------------- */

  panelsHost.innerHTML =
    panelShell('panel-consensus', 'fa-atom', 'Quantum Consensus Engine',
      'The QCF-DRIVE consensus function every service connects to. Run it directly and inspect the ledger.') +
    panelShell('panel-analytics', 'fa-chart-line', 'Real-Time Analytics',
      'Submit transactions validated by quantum consensus and watch live network metrics.') +
    panelShell('panel-security', 'fa-shield-alt', 'Enhanced Security',
      'AML scans — flagged transactions are validated or quarantined by quantum consensus.') +
    panelShell('panel-integrations', 'fa-network-wired', 'Seamless Integration',
      'Connect banking branches to the QCF-DRIVE consensus network; each becomes a consensus node.') +
    panelShell('panel-automation', 'fa-cogs', 'Automated Processes',
      'Run settlement, compliance reporting and fraud sweeps — each gated by a consensus decision.') +
    panelShell('panel-privacy', 'fa-user-shield', 'User Privacy',
      'GDPR-style data export and right-to-be-forgotten requests, decided by quantum consensus.') +
    panelShell('panel-support', 'fa-headset', '24/7 Customer Support',
      'AI support responses validated by quantum consensus; failed validations escalate to humans.');

  buildConsensusPanel();
  buildAnalyticsPanel();
  buildSecurityPanel();
  buildIntegrationsPanel();
  buildAutomationPanel();
  buildPrivacyPanel();
  buildSupportPanel();

  // Service cards in the Services section scroll to their panel.
  document.querySelectorAll('[data-panel-target]').forEach(function (card) {
    card.classList.add('cursor-pointer', 'hover:border-orange-500', 'transition-colors');
    card.addEventListener('click', function () {
      var target = document.getElementById(card.getAttribute('data-panel-target'));
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
  });
})();
