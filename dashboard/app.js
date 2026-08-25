const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);

// ---------------------------------------------------------------- tabs ----
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('page-' + tab.dataset.page).classList.add('active');
  });
});

const fmtMoney = n => '₹' + Number(n).toLocaleString('en-IN', {maximumFractionDigits: 0});
const fmtPct = n => Number(n).toFixed(1) + '%';

// ------------------------------------------------------------- overview ---
function renderOverview() {
  const o = DATA.overview;
  const kpis = [
    {label: 'Total Transactions', value: o.total_transactions.toLocaleString(), sub: 'processed through the pipeline', cls: ''},
    {label: 'Fraud Rate', value: fmtPct(o.fraud_rate_pct), sub: `${o.fraud_transactions.toLocaleString()} flagged HIGH risk`, cls: 'risk-high'},
    {label: 'High-Risk Transactions', value: o.high_risk_transactions.toLocaleString(), sub: `${o.total_risk_alerts} alerts opened`, cls: 'risk-high'},
    {label: 'Avg. Transaction Amount', value: fmtMoney(o.average_transaction_amount), sub: 'across all valid transactions', cls: 'accent'},
  ];
  document.getElementById('kpi-grid').innerHTML = kpis.map(k => `
    <div class="kpi ${k.cls}">
      <div class="label">${k.label}</div>
      <div class="value">${k.value}</div>
      <div class="sub">${k.sub}</div>
    </div>`).join('');

  const total = o.low_risk_transactions + o.medium_risk_transactions + o.high_risk_transactions;
  const lowPct = o.low_risk_transactions / total * 100;
  const medPct = o.medium_risk_transactions / total * 100;
  const highPct = o.high_risk_transactions / total * 100;
  document.getElementById('risk-bar').innerHTML = `
    <div style="width:${lowPct}%; background:var(--low)"></div>
    <div style="width:${medPct}%; background:var(--med)"></div>
    <div style="width:${highPct}%; background:var(--high)"></div>`;
  document.getElementById('risk-legend').innerHTML = `
    <span><span class="dot" style="background:var(--low)"></span>LOW · ${o.low_risk_transactions.toLocaleString()} (${lowPct.toFixed(1)}%)</span>
    <span><span class="dot" style="background:var(--med)"></span>MEDIUM · ${o.medium_risk_transactions.toLocaleString()} (${medPct.toFixed(1)}%)</span>
    <span><span class="dot" style="background:var(--high)"></span>HIGH · ${o.high_risk_transactions.toLocaleString()} (${highPct.toFixed(1)}%)</span>`;

  const mm = DATA.model_metrics;
  const modelMeta = {
    logistic_regression: {name: 'Logistic Regression', desc: 'Linear baseline, class-weighted for imbalance'},
    random_forest: {name: 'Random Forest', desc: '300 trees, balanced-subsample weighting'},
  };
  document.getElementById('model-grid').innerHTML = Object.keys(modelMeta).map(key => {
    const m = mm[key];
    const isBest = mm.best_model === key;
    return `
      <div class="model-card ${isBest ? 'best' : ''}">
        <h4>${modelMeta[key].name} ${isBest ? '<span class="best-badge">SELECTED</span>' : ''}</h4>
        <div class="metric-row"><span class="k">Accuracy</span><span class="v">${(m.accuracy*100).toFixed(2)}%</span></div>
        <div class="metric-row"><span class="k">Precision</span><span class="v">${(m.precision*100).toFixed(2)}%</span></div>
        <div class="metric-row"><span class="k">Recall</span><span class="v">${(m.recall*100).toFixed(2)}%</span></div>
        <div class="metric-row"><span class="k">F1-score</span><span class="v">${(m.f1_score*100).toFixed(2)}%</span></div>
        <div class="metric-row"><span class="k">ROC-AUC</span><span class="v">${m.roc_auc.toFixed(3)}</span></div>
        <div style="font-size:11px; color:var(--muted-2); margin-top:8px;">${modelMeta[key].desc}</div>
      </div>`;
  }).join('') + `
    <div class="note" style="grid-column: 1 / -1;">
      Fraud is a heavily imbalanced problem (~1.5% positive class), so <b>accuracy alone is misleading</b> —
      a model that predicts "not fraud" every time would still score ~98% accuracy. Model selection here is
      driven by <b>ROC-AUC</b>, with precision/recall/F1 reported to make the tradeoff between catching fraud
      and false-alerting analysts explicit.
    </div>`;

  const q = DATA.data_quality;
  const pct = q.quality_score_pct;
  const circumference = 2 * Math.PI * 38;
  const offset = circumference * (1 - pct / 100);
  const arc = document.getElementById('quality-arc');
  arc.setAttribute('stroke-dasharray', circumference);
  arc.setAttribute('stroke-dashoffset', offset);
  document.getElementById('quality-pct').textContent = pct + '%';

  const checks = q.checks;
  document.getElementById('quality-checks').innerHTML = Object.values(checks).map(c => `
    <div class="qcheck ${c.passed ? 'pass' : 'fail'}">
      <div class="ic">${c.passed ? '✓' : '✕'}</div>
      <div class="desc">${c.description} <span style="color:var(--muted-2)">(${c.failures ?? c.rate_pct + '%'} fail${typeof c.failures === 'number' ? '' : ''})</span></div>
    </div>`).join('');
}

// --------------------------------------------------------- transactions ---
function renderTransactionsTable(filter = '') {
  const f = filter.trim().toLowerCase();
  const rows = DATA.top_transactions.filter(t =>
    !f || [t.transaction_id, t.customer_id, t.merchant_id, t.location, t.merchant_category]
      .some(v => String(v).toLowerCase().includes(f))
  );
  document.getElementById('txn-tbody').innerHTML = rows.map(t => `
    <tr>
      <td>${t.transaction_id}</td>
      <td>${t.customer_id}</td>
      <td>${t.merchant_id}</td>
      <td>${t.merchant_category}</td>
      <td>${t.location}</td>
      <td>${fmtMoney(t.transaction_amount)}</td>
      <td>${(parseFloat(t.fraud_probability)*100).toFixed(1)}%</td>
      <td><span class="badge ${t.risk_level}">${t.risk_level}</span></td>
    </tr>`).join('') || `<tr><td colspan="8" style="text-align:center; color:var(--muted); padding:24px;">No matching transactions</td></tr>`;
}
document.getElementById('txn-search').addEventListener('input', e => renderTransactionsTable(e.target.value));

// ------------------------------------------------------------ customers ---
let selectedCustomer = null;
function renderCustList(filter = '') {
  const f = filter.trim().toLowerCase();
  const rows = DATA.top_customers.filter(c => !f || c.customer_id.toLowerCase().includes(f));
  document.getElementById('cust-list').innerHTML = rows.map(c => `
    <div class="cust-row ${selectedCustomer === c.customer_id ? 'selected' : ''}" data-id="${c.customer_id}">
      <div class="id">${c.customer_id}</div>
      <div class="meta">${c.total_transactions} txns · risk score ${c.risk_score}</div>
    </div>`).join('');
  document.querySelectorAll('.cust-row').forEach(el => {
    el.addEventListener('click', () => { selectedCustomer = el.dataset.id; renderCustList(document.getElementById('cust-search').value); renderCustDetail(); });
  });
}
function renderCustDetail() {
  const c = DATA.top_customers.find(x => x.customer_id === selectedCustomer);
  if (!c) { document.getElementById('cust-detail').innerHTML = `<div class="empty-state">Select a customer to open their investigation record.</div>`; return; }
  document.getElementById('cust-detail').innerHTML = `
    <div style="font-family:var(--font-display); font-size:16px; margin-bottom:14px;">Customer ${c.customer_id}</div>
    <div class="detail-grid">
      <div class="detail-stat"><div class="l">Total Transactions</div><div class="v">${c.total_transactions}</div></div>
      <div class="detail-stat"><div class="l">Avg Amount</div><div class="v">${fmtMoney(c.avg_amount)}</div></div>
      <div class="detail-stat"><div class="l">Max Amount</div><div class="v">${fmtMoney(c.max_amount)}</div></div>
      <div class="detail-stat"><div class="l">Risk Score</div><div class="v" style="color:${c.risk_score > 60 ? 'var(--high)' : c.risk_score > 30 ? 'var(--med)' : 'var(--low)'}">${c.risk_score}</div></div>
      <div class="detail-stat"><div class="l">High-Risk Txns</div><div class="v">${c.high_risk_txn_count}</div></div>
      <div class="detail-stat"><div class="l">Avg Fraud Prob.</div><div class="v">${(c.avg_fraud_probability*100).toFixed(1)}%</div></div>
    </div>
    <div class="section-label" style="margin-top:6px;">Devices Used</div>
    <div class="chip-row">${c.devices_used.map(d => `<span class="chip">${d}</span>`).join('')}</div>
    <div class="section-label">Merchants Used</div>
    <div class="chip-row">${c.merchants_used.map(m => `<span class="chip">${m}</span>`).join('')}</div>
    <div class="section-label">Locations Used</div>
    <div class="chip-row">${c.locations_used.map(l => `<span class="chip">${l}</span>`).join('')}</div>`;
}
document.getElementById('cust-search').addEventListener('input', e => renderCustList(e.target.value));

// -------------------------------------------------------- investigation ---
let selectedTxn = null;
function renderInvList(filter = '') {
  const f = filter.trim().toLowerCase();
  const rows = DATA.top_alerts.filter(a => !f || a.transaction_id.toLowerCase().includes(f));
  document.getElementById('inv-list').innerHTML = rows.map(a => `
    <div class="cust-row ${selectedTxn === a.transaction_id ? 'selected' : ''}" data-id="${a.transaction_id}">
      <div class="id">${a.transaction_id}</div>
      <div class="meta">${fmtMoney(a.amount)} · ${(a.fraud_probability*100).toFixed(0)}% probability</div>
    </div>`).join('');
  document.querySelectorAll('#inv-list .cust-row').forEach(el => {
    el.addEventListener('click', () => { selectedTxn = el.dataset.id; renderInvList(document.getElementById('inv-search').value); renderInvDetail(); });
  });
}
function renderInvDetail() {
  const a = DATA.top_alerts.find(x => x.transaction_id === selectedTxn);
  if (!a) { document.getElementById('inv-detail').innerHTML = `<div class="empty-state">Select a transaction to trace Customer → Device → Merchant → Risk Alert.</div>`; return; }

  const nodes = [
    {id: a.customer_id, label: 'Customer', x: 60, y: 40},
    {id: a.transaction_id, label: 'Transaction', x: 260, y: 100},
    {id: a.device_id, label: 'Device', x: 60, y: 160},
    {id: a.merchant_id, label: 'Merchant', x: 460, y: 40},
    {id: a.alert_id, label: 'Risk Alert', x: 460, y: 160},
  ];
  const edges = [
    [nodes[0], nodes[1], 'makes'],
    [nodes[2], nodes[1], 'used for'],
    [nodes[1], nodes[3], 'at'],
    [nodes[1], nodes[4], 'generates'],
  ];
  const edgeLines = edges.map(([from, to, label]) => {
    const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2;
    return `<line x1="${from.x+55}" y1="${from.y+18}" x2="${to.x+55}" y2="${to.y+18}" stroke="var(--border)" stroke-width="1.5" />
            <text x="${mx+55}" y="${my+12}" fill="var(--muted-2)" font-size="9" font-family="IBM Plex Mono" text-anchor="middle">${label}</text>`;
  }).join('');
  const nodeBoxes = nodes.map((n, i) => {
    const isAlert = n.label === 'Risk Alert';
    const isTxn = n.label === 'Transaction';
    const stroke = isAlert ? 'var(--high)' : (isTxn ? 'var(--teal)' : 'var(--border)');
    return `<rect x="${n.x}" y="${n.y}" width="110" height="36" rx="8" fill="var(--panel)" stroke="${stroke}" stroke-width="1.4"/>
            <text x="${n.x+55}" y="${n.y+15}" fill="var(--muted-2)" font-size="8.5" font-family="IBM Plex Mono" text-anchor="middle" text-transform="uppercase">${n.label}</text>
            <text x="${n.x+55}" y="${n.y+27}" fill="var(--text)" font-size="10.5" font-family="IBM Plex Mono" text-anchor="middle">${n.id}</text>`;
  }).join('');

  document.getElementById('inv-detail').innerHTML = `
    <div style="font-family:var(--font-display); font-size:16px; margin-bottom:4px;">Transaction ${a.transaction_id}</div>
    <div style="font-size:12px; color:var(--muted); margin-bottom:14px;">${fmtMoney(a.amount)} · fraud probability ${(a.fraud_probability*100).toFixed(1)}% · <span class="badge ${a.risk_level}">${a.risk_level}</span></div>
    <svg viewBox="0 0 630 220" style="width:100%; height:auto; max-height:260px;">${edgeLines}${nodeBoxes}</svg>
    <div class="section-label">Explainable Risk — Contributing Factors</div>
    <div class="factor-list">${a.contributing_factors.map(f => `<div class="factor">${f}</div>`).join('')}</div>
  `;
}
document.getElementById('inv-search').addEventListener('input', e => renderInvList(e.target.value));

// --------------------------------------------------------------- init -----
renderOverview();
renderTransactionsTable();
renderCustList();
renderInvList();
