DASHBOARD_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My Trade Notify</title>
  <style>
    body { margin:0; background:#f4f7fb; color:#172033; font-family:Arial,sans-serif; }
    main { max-width:900px; margin:40px auto; padding:20px; }
    h1 { text-align:center; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; }
    .grid.hidden { display:none; }
    .card {
      background:white;
      border-radius:8px;
      padding:10px 12px;
      box-shadow:0 2px 8px rgba(0,0,0,.06);
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:10px;
    }
    .label { color:#60708a; font-size:11px; text-transform:uppercase; white-space:nowrap; }
    .value { font-size:13px; font-weight:bold; margin-top:0; white-space:nowrap; text-align:right; }
    .running { color:#16836b; }
    .actions { display:flex; flex-wrap:wrap; gap:12px; justify-content:flex-start; margin:24px 0; }
    .actions-wrap { margin-bottom:10px; }
    button { border:0; border-radius:8px; padding:12px 18px; font-size:15px; font-weight:bold; cursor:pointer; color:white; }
    .daily { background:#2563eb; } .monthly { background:#7c3aed; }
    .alert { background:#dc2626; } .live { background:#ea580c; }
    button:disabled { opacity:.6; cursor:wait; }
    .actions button { position:relative; }
    .actions button::before,
    .actions button::after {
      opacity:0;
      pointer-events:none;
      transition:opacity .15s ease, transform .15s ease;
      position:absolute;
      left:50%;
      z-index:20;
    }
    .actions button::before {
      content:'';
      bottom:calc(100% + 4px);
      transform:translateX(-50%) translateY(4px);
      border:6px solid transparent;
      border-top-color:#0f172a;
    }
    .actions button::after {
      content:attr(data-help);
      bottom:calc(100% + 14px);
      transform:translateX(-50%) translateY(4px);
      background:#0f172a;
      color:#fff;
      font-size:12px;
      font-weight:600;
      line-height:1.35;
      border-radius:6px;
      padding:8px 10px;
      min-width:180px;
      max-width:260px;
      text-align:left;
      white-space:normal;
      box-shadow:0 6px 16px rgba(0,0,0,.25);
    }
    .actions button:hover::before,
    .actions button:hover::after,
    .actions button:focus-visible::before,
    .actions button:focus-visible::after {
      opacity:1;
      transform:translateX(-50%) translateY(0);
    }
    #actionResult { max-width:700px; margin:10px auto 0; text-align:center; font-weight:bold; }
    .header-bar { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
    .account-name { font-size:18px; font-weight:bold; }
    .header-actions { display:flex; flex-direction:column; align-items:flex-end; gap:8px; }
    .country-row { display:flex; align-items:center; gap:8px; }
    .stock-row { display:flex; align-items:center; justify-content:flex-start; gap:8px; margin:10px 0 8px; flex-wrap:wrap; }
    .stock-row select { padding:8px; border-radius:6px; min-width:220px; }
    .stock-timing { margin-left:8px; grid-template-columns:1fr; }
    .stock-timing .card { min-width:280px; }
    .stock-details {
      background:#ffffff;
      border:1px solid #d8e1ef;
      border-radius:8px;
      padding:10px 12px;
      margin:0 auto 10px;
      max-width:760px;
      font-size:14px;
      color:#172033;
    }
    .stock-details.hidden { display:none; }
    .stock-details .title { font-weight:bold; margin-bottom:8px; }
    .stock-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:6px 12px; }
    .stock-item { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .stock-chart {
      background:#ffffff;
      border:1px solid #d8e1ef;
      border-radius:8px;
      padding:12px;
      margin:0 auto 10px;
      max-width:760px;
      color:#172033;
    }
    .stock-chart.hidden { display:none; }
    .stock-chart-header { display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }
    .stock-chart-controls { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .stock-chart-controls select { padding:6px 8px; border-radius:6px; }
    #stockChartStatus { font-size:13px; color:#60708a; margin:10px 0; }
    .stock-chart-plot { position:relative; }
    #stockChartSvg { width:100%; height:240px; background:#fbfdff; border:1px solid #e2e8f0; border-radius:6px; }
    .chart-hover-tooltip {
      position:absolute;
      z-index:15;
      pointer-events:none;
      background:#0f172a;
      color:#ffffff;
      font-size:12px;
      border-radius:6px;
      padding:6px 8px;
      white-space:nowrap;
      box-shadow:0 4px 12px rgba(0,0,0,.25);
      transform:translate(10px, -10px);
    }
    .chart-hover-tooltip.hidden { display:none; }
    .chart-meta {
      margin-top:8px;
      padding-top:8px;
      border-top:1px dashed #cbd5e1;
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
      gap:6px 10px;
      font-size:12px;
      color:#475569;
    }
    .chart-meta-item { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .company-info {
      background:#ffffff;
      border:1px solid #d8e1ef;
      border-radius:8px;
      padding:12px;
      margin:0 auto 10px;
      max-width:760px;
      color:#172033;
      font-size:14px;
    }
    .company-info.hidden { display:none; }
    .company-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:8px 14px; margin-top:8px; }
    .company-item { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .company-summary { grid-column:1 / -1; line-height:1.45; white-space:normal; }
    .company-section { grid-column:1 / -1; background:#f8fbff; border:1px solid #d8e1ef; border-radius:6px; padding:10px; }
    .company-section-title { font-weight:700; color:#1f3a5f; margin-bottom:6px; }
    .company-list { margin:0; padding-left:18px; line-height:1.45; }
    .company-note { grid-column:1 / -1; font-size:12px; color:#475569; }
    .confidence-badge { margin-left:8px; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; text-transform:uppercase; }
    .confidence-high { background:#dcfce7; color:#166534; border:1px solid #86efac; }
    .confidence-medium { background:#fef9c3; color:#854d0e; border:1px solid #fde68a; }
    .confidence-low { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; }
    .power-button { width:38px; height:38px; padding:0; border-radius:50%; background:#dc2626; color:white; font-size:20px; line-height:38px; text-align:center; }
    .power-button:hover { background:#b91c1c; }
    .power-button { position:relative; }
    .power-button::before,
    .power-button::after {
      opacity:0;
      pointer-events:none;
      transition:opacity .15s ease, transform .15s ease;
      position:absolute;
      left:50%;
      z-index:20;
    }
    .power-button::before {
      content:'';
      bottom:calc(100% + 4px);
      transform:translateX(-50%) translateY(4px);
      border:6px solid transparent;
      border-top-color:#0f172a;
    }
    .power-button::after {
      content:attr(data-help);
      bottom:calc(100% + 14px);
      transform:translateX(-50%) translateY(4px);
      background:#0f172a;
      color:#fff;
      font-size:12px;
      font-weight:600;
      line-height:1.35;
      border-radius:6px;
      padding:8px 10px;
      min-width:70px;
      text-align:center;
      white-space:nowrap;
      box-shadow:0 6px 16px rgba(0,0,0,.25);
    }
    .power-button:hover::before,
    .power-button:hover::after,
    .power-button:focus-visible::before,
    .power-button:focus-visible::after {
      opacity:1;
      transform:translateX(-50%) translateY(0);
    }
  </style>
</head>
<body>
  <main>
    <h1>My Trade Notify Production Dashboard</h1>
    <div class="header-bar">
      <div>
        <div class="account-name">{{ account_name }}</div>
        <div style="margin-top:6px;font-size:14px;color:#334155">
          <div><strong>Service:</strong> <span id="serviceStatus">Loading...</span></div>
          <div><strong>Started At:</strong> <span id="startedAt">Loading...</span></div>
        </div>
      </div>
      <div class="header-actions">
        <div class="country-row">
          <label for="country" style="font-weight:bold">Country:</label>
          <select id="country" onchange="setCountry(this.value)" style="padding:8px;border-radius:6px">
            <option value="US">United States</option>
            <option value="IN">India</option>
          </select>
        </div>
        <button type="button" class="power-button" data-help="Logoff" aria-label="Logoff" onclick="window.location.href='/logout'">⏻</button>
      </div>
    </div>
    <div class="actions-wrap">
      <div class="actions">
        {% if account_role == 'admin' %}
        <button class="daily" data-help="Sends profit/loss report and a 30-day unusual-movement check." onclick="triggerAction('daily', this)">Send Daily Report</button>
        <button class="monthly" data-help="Sends the monthly profit/loss report." onclick="triggerAction('monthly', this)">Send Monthly Report</button>
        <button class="alert" data-help="Sends only the unusual-movement alert." onclick="triggerAction('alert', this)">Check 30-Day Alerts</button>
        <button class="live" data-help="Checks the latest 5-minute movement once." onclick="triggerAction('live-alert', this)">Check Live Alert</button>
        {% endif %}
      </div>
      <div id="actionResult"></div>
    </div>
    <div class="stock-row">
      <label for="stockSymbol" style="font-weight:bold">Stock:</label>
      <select id="stockSymbol" onchange="loadSelectedStock()"></select>
      <div class="grid hidden stock-timing" id="cards"></div>
    </div>
    <div id="stockDetails" class="stock-details hidden"></div>
    <div id="stockChartBox" class="stock-chart hidden">
      <div class="stock-chart-header">
        <div class="title" id="stockChartTitle">Stock Price Chart</div>
        <div class="stock-chart-controls">
          <label for="chartRange"><strong>Range:</strong></label>
          <select id="chartRange" onchange="loadStockHistory()">
            <option value="1d">1 Day</option>
            <option value="5d">5 Days</option>
            <option value="1mo" selected>1 Month</option>
            <option value="3mo">3 Months</option>
            <option value="6mo">6 Months</option>
            <option value="1y">1 Year</option>
            <option value="2y">2 Years</option>
          </select>
          <label for="chartInterval"><strong>Interval:</strong></label>
          <select id="chartInterval" onchange="loadStockHistory()">
            <option value="1m">1 Min</option>
            <option value="5m">5 Min</option>
            <option value="15m">15 Min</option>
            <option value="30m">30 Min</option>
            <option value="1h">1 Hour</option>
            <option value="1d" selected>1 Day</option>
            <option value="1wk">1 Week</option>
          </select>
        </div>
      </div>
      <div id="stockChartStatus">Select a stock to view chart data.</div>
      <div class="stock-chart-plot" id="stockChartPlot">
        <svg id="stockChartSvg" viewBox="0 0 760 240" preserveAspectRatio="none"></svg>
        <div id="chartHoverTooltip" class="chart-hover-tooltip hidden"></div>
      </div>
      <div id="stockChartMeta" class="chart-meta"></div>
    </div>
    <div id="companyInfoBox" class="company-info hidden">
      <div class="title" id="companyInfoTitle">Company Info</div>
      <div class="company-grid" id="companyInfoGrid"></div>
    </div>
  </main>
  <script>
    let resultClearTimer = null;
    let loadedStocksCountry = null;
    let activeTimingLabel = null;
    let chartState = null;

    function scheduleResultClear(delayMs = 5000) {
      const result = document.getElementById('actionResult');
      if (resultClearTimer) {
        clearTimeout(resultClearTimer);
      }
      resultClearTimer = setTimeout(() => {
        if (result && result.dataset.notice !== '1') {
          result.textContent = '';
        }
      }, delayMs);
    }

    function formatTimeOnly(value, fallback='Not yet generated') {
      if (!value) {
        return fallback;
      }

      const text = String(value);
      if (text.toLowerCase().includes('not yet')) {
        return text;
      }

      const timePart = text.includes('T') ? text.split('T')[1] : (text.split(' ')[1] || '');
      const pieces = timePart.split(':');
      if (pieces.length < 2) {
        return text;
      }

      const hour24 = Number(pieces[0]);
      const minute = pieces[1];
      if (Number.isNaN(hour24)) {
        return text;
      }

      const suffix = hour24 >= 12 ? 'PM' : 'AM';
      const hour12 = hour24 % 12 || 12;
      return `${String(hour12).padStart(2, '0')}:${minute} ${suffix}`;
    }

    function formatDateTime12(value, fallback='Not available') {
      if (!value) {
        return fallback;
      }

      const text = String(value);
      const parts = text.includes('T') ? text.split('T') : text.split(' ');
      if (parts.length < 2) {
        return text;
      }

      const datePart = parts[0];
      const timePart = parts[1];
      const pieces = timePart.split(':');
      if (pieces.length < 2) {
        return `${datePart} ${timePart}`;
      }

      const hour24 = Number(pieces[0]);
      const minute = pieces[1];
      const second = pieces[2] || '00';
      if (Number.isNaN(hour24)) {
        return `${datePart} ${timePart}`;
      }

      const suffix = hour24 >= 12 ? 'PM' : 'AM';
      const hour12 = hour24 % 12 || 12;
      return `${datePart} ${String(hour12).padStart(2, '0')}:${minute}:${second} ${suffix}`;
    }

    function formatNumber(value, digits = 2) {
      const num = Number(value);
      if (Number.isNaN(num)) {
        return '-';
      }
      return num.toLocaleString(undefined, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });
    }

    function formatCompactNumber(value) {
      const num = Number(value);
      if (Number.isNaN(num)) {
        return '-';
      }
      return num.toLocaleString(undefined, {
        notation: 'compact',
        maximumFractionDigits: 2,
      });
    }

    function formatPercentFromDecimal(value) {
      const num = Number(value);
      if (Number.isNaN(num)) {
        return '-';
      }
      return `${(num * 100).toFixed(2)}%`;
    }

    function toText(value, fallback = '-') {
      if (value === null || value === undefined) {
        return fallback;
      }
      const text = String(value).trim();
      return text ? text : fallback;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function asList(value) {
      if (Array.isArray(value)) {
        return value.map((item) => String(item || '').trim()).filter(Boolean);
      }
      const text = String(value || '').trim();
      return text ? [text] : [];
    }

    function normalizeConfidence(confidence) {
      const value = String(confidence || '').trim().toLowerCase();
      if (value === 'high' || value === 'medium' || value === 'low') {
        return value;
      }
      return 'low';
    }

    function renderConfidenceBadge(confidence, hint) {
      const level = normalizeConfidence(confidence);
      const title = escapeHtml(toText(hint, `Confidence: ${level}`));
      return `<span class="confidence-badge confidence-${level}" title="${title}">${escapeHtml(level)}</span>`;
    }

    function renderListSection(title, items, emptyText, confidence, confidenceHint) {
      const safeTitle = escapeHtml(title);
      const listItems = asList(items);
      const badge = renderConfidenceBadge(confidence, confidenceHint);
      if (listItems.length === 0) {
        return `<div class="company-section"><div class="company-section-title">${safeTitle}${badge}</div><div>${escapeHtml(emptyText)}</div></div>`;
      }
      const htmlItems = listItems.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
      return `<div class="company-section"><div class="company-section-title">${safeTitle}${badge}</div><ul class="company-list">${htmlItems}</ul></div>`;
    }

    function setStockDetailsMessage(message) {
      const target = document.getElementById('stockDetails');
      target.classList.remove('hidden');
      target.innerHTML = message;
    }

    function hideStockDetails() {
      const target = document.getElementById('stockDetails');
      target.classList.add('hidden');
      target.innerHTML = '';
    }

    function hideStockChart() {
      const chartBox = document.getElementById('stockChartBox');
      const chartStatus = document.getElementById('stockChartStatus');
      const chartSvg = document.getElementById('stockChartSvg');
      const chartTitle = document.getElementById('stockChartTitle');
      const chartMeta = document.getElementById('stockChartMeta');
      const hoverTooltip = document.getElementById('chartHoverTooltip');
      chartBox.classList.add('hidden');
      chartStatus.textContent = 'Select a stock to view chart data.';
      chartTitle.textContent = 'Stock Price Chart';
      chartSvg.innerHTML = '';
      chartMeta.innerHTML = '';
      hoverTooltip.classList.add('hidden');
      hoverTooltip.textContent = '';
      chartState = null;
    }

    function hideCompanyInfo() {
      const box = document.getElementById('companyInfoBox');
      const grid = document.getElementById('companyInfoGrid');
      box.classList.add('hidden');
      grid.innerHTML = '';
    }

    function setCompanyInfo(data) {
      const box = document.getElementById('companyInfoBox');
      const title = document.getElementById('companyInfoTitle');
      const grid = document.getElementById('companyInfoGrid');
      title.textContent = `${data.symbol} Company Info`;

      const locationParts = [toText(data.city, ''), toText(data.state, ''), toText(data.country, '')].filter(Boolean);
      const location = locationParts.length ? locationParts.join(', ') : '-';
      const website = toText(data.website);
      const modelBadge = renderConfidenceBadge(data.business_model_confidence, data.business_model_confidence_reason);

      const fields = [
        ['Stock/Company Name', toText(data.company_name)],
        ['Business Model', `${toText(data.business_model)} ${modelBadge}`],
        ['CEO', toText(data.ceo)],
        ['Sector', toText(data.sector)],
        ['Industry', toText(data.industry)],
        ['Location', location],
        ['Exchange', toText(data.exchange)],
        ['Currency', toText(data.currency)],
        ['Employees', formatCompactNumber(data.employees)],
        ['Market Cap', formatCompactNumber(data.market_cap)],
        ['Enterprise Value', formatCompactNumber(data.enterprise_value)],
        ['Beta', formatNumber(data.beta, 2)],
        ['Trailing P/E', formatNumber(data.trailing_pe, 2)],
        ['Forward P/E', formatNumber(data.forward_pe, 2)],
        ['Dividend Yield', formatPercentFromDecimal(data.dividend_yield)],
        ['52W Low', formatNumber(data.fifty_two_week_low, 2)],
        ['52W High', formatNumber(data.fifty_two_week_high, 2)],
        ['Previous Close', formatNumber(data.previous_close, 2)],
        ['Open', formatNumber(data.open_price, 2)],
        ['Volume', formatCompactNumber(data.volume)],
        ['Avg Volume', formatCompactNumber(data.average_volume)],
        ['Website', website === '-' ? '-' : `<a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer">${escapeHtml(website)}</a>`],
      ];

      const itemsHtml = fields.map(([label, value]) =>
        `<div class="company-item"><strong>${escapeHtml(label)}:</strong> ${value}</div>`
      ).join('');

      const summary = toText(data.business_summary, 'Business summary not available.');
      const summaryHtml = `<div class="company-summary"><strong>Business Summary:</strong> ${escapeHtml(summary)}</div>`;

      const serviceOffersHtml = renderListSection(
        'Service Offerings',
        data.service_offerings,
        'Service offerings are not explicitly listed in the available public summary.',
        data.service_offerings_confidence,
        data.service_offerings_confidence_reason
      );
      const serviceCustomersHtml = renderListSection(
        'Service Customers / Organizations',
        data.service_customer_segments,
        'Specific service customer organizations are not clearly named in the available data.',
        data.service_customer_segments_confidence,
        data.service_customer_segments_confidence_reason
      );
      const productOffersHtml = renderListSection(
        'Products / Solutions',
        data.product_offerings,
        'Products are not explicitly listed in the available public summary.',
        data.product_offerings_confidence,
        data.product_offerings_confidence_reason
      );
      const productCustomersHtml = renderListSection(
        'Product Users / Customer Segments',
        data.product_customer_segments,
        'Specific product user companies are not clearly named in the available data.',
        data.product_customer_segments_confidence,
        data.product_customer_segments_confidence_reason
      );
      const disclosureHtml = `<div class="company-note"><strong>Note:</strong> ${escapeHtml(toText(data.customer_disclosure_note, 'Customer lists depend on what is publicly disclosed by the company.'))}</div>`;

      grid.innerHTML = itemsHtml + summaryHtml + serviceOffersHtml + serviceCustomersHtml + productOffersHtml + productCustomersHtml + disclosureHtml;
      box.classList.remove('hidden');
    }

    async function loadCompanyInfo(symbol) {
      if (!symbol) {
        hideCompanyInfo();
        return;
      }
      try {
        const response = await fetch(`/api/stock-company-info?symbol=${encodeURIComponent(symbol)}`, {
          headers: {'Accept': 'application/json'},
          redirect: 'follow'
        });
        if (response.redirected || response.status === 302) {
          window.location.href = '/login';
          return;
        }
        const data = await response.json();
        if (!response.ok || !data.success) {
          hideCompanyInfo();
          return;
        }
        setCompanyInfo(data);
      } catch (error) {
        hideCompanyInfo();
      }
    }

    function shortTimeLabel(value) {
      if (!value) {
        return '-';
      }
      const text = String(value);
      return text.length > 16 ? text.slice(0, 16) : text;
    }

    function renderStockChart(points) {
      const chartSvg = document.getElementById('stockChartSvg');
      const chartMeta = document.getElementById('stockChartMeta');
      if (!Array.isArray(points) || points.length < 2) {
        chartSvg.innerHTML = '';
        chartMeta.innerHTML = '';
        chartState = null;
        return;
      }

      const values = points.map((p) => Number(p.c)).filter((v) => !Number.isNaN(v));
      if (values.length < 2) {
        chartSvg.innerHTML = '';
        return;
      }

      const width = 760;
      const height = 240;
      const padLeft = 36;
      const padRight = 12;
      const padTop = 14;
      const padBottom = 24;
      const minY = Math.min(...values);
      const maxY = Math.max(...values);
      const spanY = maxY - minY || 1;
      const innerW = width - padLeft - padRight;
      const innerH = height - padTop - padBottom;

      const chartPoints = points.map((p, index) => {
        const x = padLeft + (index / (points.length - 1)) * innerW;
        const yValue = Number(p.c);
        const y = padTop + ((maxY - yValue) / spanY) * innerH;
        return {
          x,
          y,
          t: String(p.t || ''),
          o: Number(p.o),
          h: Number(p.h),
          l: Number(p.l),
          c: yValue,
        };
      });

      const polyPoints = chartPoints.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');

      const lastValue = values[values.length - 1];
      const firstValue = values[0];
      const up = lastValue >= firstValue;
      const lineColor = up ? '#16836b' : '#dc2626';
      const firstTime = shortTimeLabel(chartPoints[0].t);
      const lastTime = shortTimeLabel(chartPoints[chartPoints.length - 1].t);
      const rangeText = document.getElementById('chartRange').value;
      const intervalText = document.getElementById('chartInterval').value;
      const midY = minY + spanY / 2;

      chartSvg.innerHTML =
        `<line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}" stroke="#cbd5e1" />` +
        `<line x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" stroke="#cbd5e1" />` +
        `<polyline fill="none" stroke="${lineColor}" stroke-width="2.2" points="${polyPoints}" />` +
        `<text x="4" y="${padTop + 4}" font-size="11" fill="#475569">${formatNumber(maxY)}</text>` +
        `<text x="4" y="${(padTop + innerH / 2 + 4).toFixed(2)}" font-size="11" fill="#64748b">${formatNumber(midY)}</text>` +
        `<text x="4" y="${height - padBottom}" font-size="11" fill="#475569">${formatNumber(minY)}</text>` +
        `<text x="${padLeft}" y="${height - 6}" font-size="11" fill="#475569">${firstTime}</text>` +
        `<text x="${width - padRight}" y="${height - 6}" text-anchor="end" font-size="11" fill="#475569">${lastTime}</text>` +
        `<text x="${width - 155}" y="12" font-size="11" fill="${lineColor}">Last: ${formatNumber(lastValue)}</text>` +
        `<text x="${width - 250}" y="26" font-size="11" fill="#475569">Range: ${rangeText} | Interval: ${intervalText}</text>` +
        `<line id="chartHoverLine" x1="0" y1="0" x2="0" y2="0" stroke="#334155" stroke-width="1" stroke-dasharray="4 3" style="display:none" />` +
        `<circle id="chartHoverDot" cx="0" cy="0" r="4" fill="${lineColor}" stroke="#ffffff" stroke-width="1.5" style="display:none" />`;

      chartState = {
        width,
        height,
        padTop,
        padBottom,
        points: chartPoints,
      };

      chartMeta.innerHTML =
        `<div class="chart-meta-item"><strong>Range:</strong> ${rangeText}</div>` +
        `<div class="chart-meta-item"><strong>Interval:</strong> ${intervalText}</div>` +
        `<div class="chart-meta-item"><strong>Value Range:</strong> ${formatNumber(minY)} to ${formatNumber(maxY)}</div>` +
        `<div class="chart-meta-item"><strong>Start:</strong> ${firstTime}</div>` +
        `<div class="chart-meta-item"><strong>End:</strong> ${lastTime}</div>` +
        `<div class="chart-meta-item"><strong>Points:</strong> ${chartPoints.length}</div>`;
    }

    function bindChartHover() {
      const plot = document.getElementById('stockChartPlot');
      const svg = document.getElementById('stockChartSvg');
      const tooltip = document.getElementById('chartHoverTooltip');

      const hideHover = () => {
        const hoverLine = document.getElementById('chartHoverLine');
        const hoverDot = document.getElementById('chartHoverDot');
        if (hoverLine) {
          hoverLine.style.display = 'none';
        }
        if (hoverDot) {
          hoverDot.style.display = 'none';
        }
        tooltip.classList.add('hidden');
      };

      const showHover = (clientX) => {
        if (!chartState || !chartState.points || chartState.points.length < 2) {
          hideHover();
          return;
        }

        const rect = svg.getBoundingClientRect();
        if (!rect.width) {
          hideHover();
          return;
        }

        const xPx = Math.max(0, Math.min(rect.width, clientX - rect.left));
        const ratio = xPx / rect.width;
        const maxIndex = chartState.points.length - 1;
        const idx = Math.max(0, Math.min(maxIndex, Math.round(ratio * maxIndex)));
        const point = chartState.points[idx];

        const hoverLine = document.getElementById('chartHoverLine');
        const hoverDot = document.getElementById('chartHoverDot');
        if (hoverLine && hoverDot) {
          hoverLine.style.display = 'block';
          hoverLine.setAttribute('x1', point.x.toFixed(2));
          hoverLine.setAttribute('x2', point.x.toFixed(2));
          hoverLine.setAttribute('y1', String(chartState.padTop));
          hoverLine.setAttribute('y2', String(chartState.height - chartState.padBottom));

          hoverDot.style.display = 'block';
          hoverDot.setAttribute('cx', point.x.toFixed(2));
          hoverDot.setAttribute('cy', point.y.toFixed(2));
        }

        const yPx = (point.y / chartState.height) * rect.height;
        tooltip.textContent = `${shortTimeLabel(point.t)} | O:${formatNumber(point.o)} H:${formatNumber(point.h)} L:${formatNumber(point.l)} C:${formatNumber(point.c)}`;
        tooltip.style.left = `${xPx + 10}px`;
        tooltip.style.top = `${Math.max(8, yPx - 24)}px`;
        tooltip.classList.remove('hidden');
      };

      plot.addEventListener('mousemove', (event) => showHover(event.clientX));
      plot.addEventListener('mouseleave', hideHover);
      plot.addEventListener('touchmove', (event) => {
        if (event.touches && event.touches[0]) {
          showHover(event.touches[0].clientX);
        }
      }, {passive: true});
      plot.addEventListener('touchend', hideHover);
    }

    async function loadStockHistory() {
      const symbol = document.getElementById('stockSymbol').value;
      const period = document.getElementById('chartRange').value;
      const interval = document.getElementById('chartInterval').value;
      const chartBox = document.getElementById('stockChartBox');
      const chartStatus = document.getElementById('stockChartStatus');
      const chartTitle = document.getElementById('stockChartTitle');

      if (!symbol) {
        hideStockChart();
        return;
      }

      chartBox.classList.remove('hidden');
      chartTitle.textContent = `${symbol} Price Chart`;
      chartStatus.textContent = 'Loading chart data...';
      try {
        const response = await fetch(`/api/stock-history?symbol=${encodeURIComponent(symbol)}&period=${encodeURIComponent(period)}&interval=${encodeURIComponent(interval)}`, {
          headers: {'Accept': 'application/json'},
          redirect: 'follow'
        });

        if (response.redirected || response.status === 302) {
          window.location.href = '/login';
          return;
        }

        const raw = await response.text();
        let data = null;
        try {
          data = JSON.parse(raw);
        } catch (parseError) {
          const trimmed = String(raw || '').trim().toLowerCase();
          if (trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html')) {
            chartStatus.textContent = 'Session expired. Please log in again.';
          } else {
            chartStatus.textContent = 'Chart service returned an unexpected response.';
          }
          renderStockChart([]);
          return;
        }

        if (!response.ok || !data.success) {
          chartStatus.textContent = data.message || 'Unable to load chart data.';
          renderStockChart([]);
          return;
        }

        chartStatus.textContent = `Range: ${data.period} | Interval: ${data.interval} | Points: ${data.points.length}`;
        renderStockChart(data.points || []);
      } catch (error) {
        chartStatus.textContent = 'Unable to load chart data right now.';
        renderStockChart([]);
      }
    }

    async function loadStocks(country) {
      const select = document.getElementById('stockSymbol');
      const prevValue = select.value;
      const response = await fetch(`/api/stocks?country=${encodeURIComponent(country)}`);
      const data = await response.json();

      if (!data.success || !Array.isArray(data.symbols) || data.symbols.length === 0) {
        select.innerHTML = '<option value="">No stocks available</option>';
        hideStockDetails();
        hideStockChart();
        hideCompanyInfo();
        loadedStocksCountry = country;
        return;
      }

      select.innerHTML = '<option value="">Select Stock/ETF</option>' + data.symbols
        .map((symbol) => `<option value="${symbol}">${symbol}</option>`)
        .join('');

      if (prevValue && data.symbols.includes(prevValue)) {
        select.value = prevValue;
        await loadSelectedStock();
      } else {
        select.value = '';
        hideStockDetails();
        hideStockChart();
        hideCompanyInfo();
      }

      loadedStocksCountry = country;
    }

    async function loadSelectedStock() {
      const select = document.getElementById('stockSymbol');
      const symbol = select.value;
      const country = document.getElementById('country').value || 'US';

      if (!symbol) {
        hideStockDetails();
        hideStockChart();
        hideCompanyInfo();
        return;
      }

      setStockDetailsMessage('Loading stock details...');
      try {
        const response = await fetch(`/api/stock-details?country=${encodeURIComponent(country)}&symbol=${encodeURIComponent(symbol)}`);
        const data = await response.json();
        if (!data.success) {
          setStockDetailsMessage(data.message || 'Unable to load stock details.');
          return;
        }

        const changeColor = data.change >= 0 ? '#16836b' : '#dc2626';
        const changePrefix = data.change >= 0 ? '+' : '';

        setStockDetailsMessage(
          `<div class="title">${data.name} (${data.symbol})</div>` +
          `<div class="stock-grid">` +
          `<div class="stock-item"><strong>Type:</strong> ${data.instrument_type}</div>` +
          `<div class="stock-item"><strong>Date:</strong> ${data.latest_date}</div>` +
          `<div class="stock-item"><strong>Open:</strong> ${formatNumber(data.open_price)}</div>` +
          `<div class="stock-item"><strong>Close:</strong> ${formatNumber(data.close_price)}</div>` +
          `<div class="stock-item"><strong>High:</strong> ${formatNumber(data.high_price)}</div>` +
          `<div class="stock-item"><strong>Low:</strong> ${formatNumber(data.low_price)}</div>` +
          `<div class="stock-item"><strong>Volume:</strong> ${Number(data.volume || 0).toLocaleString()}</div>` +
          `<div class="stock-item"><strong>Change:</strong> <span style="color:${changeColor}">${changePrefix}${formatNumber(data.change)} (${changePrefix}${formatNumber(data.change_percent)}%)</span></div>` +
          `</div>`
        );
        await loadStockHistory();
        await loadCompanyInfo(symbol);
      } catch (error) {
        setStockDetailsMessage('Unable to load stock details right now.');
        hideStockChart();
        hideCompanyInfo();
      }
    }

    async function refresh() {
      const status = await (await fetch('/api/status')).json();
      const result = document.getElementById('actionResult');
      const cards = document.getElementById('cards');
      document.getElementById('serviceStatus').textContent = status.running ? 'Running' : 'Stopped';
      document.getElementById('startedAt').textContent = formatDateTime12(status.started_at, 'Not available');
      const items = [
        ['Last Daily Report',formatTimeOnly(status.last_daily_report)],
        ['Last Monthly Report',formatTimeOnly(status.last_monthly_report)],
        ['Last Live Alert Check',formatTimeOnly(status.last_live_alert_check)],
        ['Last Unusual Alert',formatTimeOnly(status.last_unusual_alert)]
      ];
      if (!activeTimingLabel) {
        cards.classList.add('hidden');
        cards.innerHTML = '';
      } else {
        const selected = items.find(([label]) => label === activeTimingLabel);
        if (selected) {
          const [label, value] = selected;
          cards.classList.remove('hidden');
          cards.innerHTML = `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`;
        } else {
          cards.classList.add('hidden');
          cards.innerHTML = '';
        }
      }
      document.getElementById('country').value=status.selected_country;
      if (loadedStocksCountry !== status.selected_country) {
        await loadStocks(status.selected_country);
      }
      if (status.dashboard_notice) {
        result.textContent=status.dashboard_notice;
        result.style.color=status.dashboard_notice_level==='error'?'#dc2626':'#2563eb';
        result.dataset.notice='1';
      } else if (result.dataset.notice === '1') {
        result.textContent='';
        result.dataset.notice='0';
      }
    }
    async function triggerAction(action,button){
      const actionToTimingLabel = {
        'daily': 'Last Daily Report',
        'monthly': 'Last Monthly Report',
        'alert': 'Last Unusual Alert',
        'live-alert': 'Last Live Alert Check',
      };
      activeTimingLabel = actionToTimingLabel[action] || null;
      button.disabled=true; const result=document.getElementById('actionResult');
      result.textContent='Processing action...';
      try {
        const response=await fetch(`/api/trigger/${action}`,{method:'POST',headers:{'Accept':'application/json'},redirect:'follow'});
        if (response.redirected || response.status === 302) {
          window.location.href='/login';
          return;
        }
        const data=await response.json();
        result.textContent=data.message || 'Action request completed.';
        result.style.color=data.success?'#16836b':'#dc2626';
        result.dataset.notice='0';
        scheduleResultClear(data.success ? 5000 : 4500);
      } catch(error) {
        result.textContent='Unable to trigger the action. Please refresh and log in again.';
        result.style.color='#dc2626';
        result.dataset.notice='0';
        scheduleResultClear(5000);
      }
      finally { button.disabled=false; refresh(); }
    }
    async function setCountry(country){
      const response=await fetch('/api/country',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({country})});
      const data=await response.json(); const result=document.getElementById('actionResult');
      result.textContent=data.success?`Country changed to ${data.country_name}.`:data.message;
      result.style.color=data.success?'#16836b':'#dc2626';
      result.dataset.notice='0';
      if (data.success) {
        await loadStocks(country);
        scheduleResultClear(5000);
      }
    }
    bindChartHover();
    refresh(); setInterval(refresh,10000);
  </script>
</body>
</html>
'''
