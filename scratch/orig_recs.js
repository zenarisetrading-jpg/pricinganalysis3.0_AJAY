<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SADDL | Price Benchmarking</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090b10;
            --surface: rgba(22, 25, 35, 0.7);
            --surface-solid: #161923;
            --border: rgba(255, 255, 255, 0.08);
            --text: #f0f2f5;
            --text-dim: #949eb5;
            --accent: #5b8af0;
            --accent-glow: rgba(91, 138, 240, 0.3);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --radius: 16px;
            --font-main: 'Inter', sans-serif;
            --font-heading: 'Outfit', sans-serif;
            --glass: blur(12px) saturate(180%);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: var(--bg);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(91, 138, 240, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.03) 0%, transparent 40%);
            color: var(--text);
            font-family: var(--font-main);
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }

        /* Sidebar & Navigation */
        .layout { display: flex; min-height: 100vh; }
        
        .sidebar {
            width: 260px;
            background: var(--surface-solid);
            border-right: 1px solid var(--border);
            padding: 32px 20px;
            display: flex;
            flex-direction: column;
            gap: 40px;
            position: sticky;
            top: 0;
            height: 100vh;
        }

        .logo {
            font-family: var(--font-heading);
            font-weight: 700;
            font-size: 22px;
            letter-spacing: -0.02em;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo span { color: var(--accent); }

        .nav-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
        .nav-item {
            padding: 12px 16px;
            border-radius: 12px;
            color: var(--text-dim);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .nav-item:hover { background: rgba(255, 255, 255, 0.05); color: var(--text); }
        .nav-item.active { background: var(--accent-glow); color: var(--accent); }

        /* Main Content */
        .content { flex: 1; padding: 40px; max-width: 1400px; margin: 0 auto; width: 100%; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 40px;
        }

        .header-title h1 { font-family: var(--font-heading); font-size: 32px; margin-bottom: 8px; }
        .header-title p { color: var(--text-dim); font-size: 15px; }

        .client-selector {
            background: var(--surface-solid);
            border: 1px solid var(--border);
            padding: 10px 16px;
            border-radius: 12px;
            color: var(--text);
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Grid Layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }

        .card {
            background: var(--surface);
            backdrop-filter: var(--glass);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .card-title { font-family: var(--font-heading); font-weight: 600; font-size: 18px; }

        /* KPI Cards */
        .kpi-row {
            grid-column: span 2;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: var(--surface-solid);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
        }

        .kpi-label { font-size: 12px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
        .kpi-value { font-family: var(--font-heading); font-size: 28px; font-weight: 700; }
        .kpi-trend { font-size: 13px; margin-top: 8px; display: flex; align-items: center; gap: 4px; }
        .trend-up { color: var(--success); }
        .trend-down { color: var(--danger); }

        /* Position Map */
        .position-map {
            height: 400px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .zone-bar {
            height: 48px;
            width: 100%;
            background: linear-gradient(to right, 
                #ef4444 0%, #f59e0b 20%, #10b981 40%, #10b981 60%, #3b82f6 80%, #6366f1 100%);
            border-radius: 24px;
            position: relative;
            margin-bottom: 32px;
        }

        .zone-marker {
            position: absolute;
            top: -12px;
            width: 4px;
            height: 72px;
            background: white;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
            border-radius: 2px;
            transition: left 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .zone-labels {
            display: flex;
            justify-content: space-between;
            color: var(--text-dim);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        /* Recommendations Table */
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text-dim); font-size: 12px; font-weight: 600; text-transform: uppercase; }
        td { padding: 16px; border-bottom: 1px solid var(--border); font-size: 14px; }

        .price-badge {
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 10px;
            border-radius: 6px;
            font-family: monospace;
            font-weight: 600;
        }

        .action-chip {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .action-increase { background: rgba(16, 185, 129, 0.15); color: var(--success); }
        .action-decrease { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
        .action-hold { background: rgba(148, 158, 181, 0.15); color: var(--text-dim); }

        /* Alerts Feed */
        .alert-item {
            display: flex;
            gap: 16px;
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }
        .alert-item:last-child { border-bottom: none; }
        
        .alert-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .alert-high { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        .alert-medium { background: rgba(245, 158, 11, 0.1); color: var(--warning); }

        .alert-content h4 { font-size: 14px; margin-bottom: 4px; }
        .alert-content p { font-size: 13px; color: var(--text-dim); line-height: 1.4; }
        .alert-time { font-size: 11px; color: var(--text-dim); margin-top: 4px; }

        /* Responsive */
        @media (max-width: 1100px) {
            .dashboard-grid { grid-template-columns: 1fr; }
            .kpi-row { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="logo">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                SADDL<span>.</span>
            </div>
            
            <nav class="nav-list">
                <a href="#" class="nav-item" data-tab="overview">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
                    Overview
                </a>
                <a href="#" class="nav-item active" data-tab="benchmarking">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    Benchmarking
                </a>
                <a href="#" class="nav-item" data-tab="alerts">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
                    Alerts
                </a>
                <a href="#" class="nav-item" data-tab="audit">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    Audit
                </a>
            </nav>
        </aside>

        <main class="content">
            <header>
                <div class="header-title">
                    <h1>Price Benchmarking</h1>
                    <p id="sub-title">Real-time market positioning & repricing intelligence</p>
                </div>
                <button class="client-selector" id="client-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 7h10"/><path d="M7 12h10"/><path d="M7 17h10"/></svg>
                    <span id="active-client">S2C UAE</span>
                </button>
            </header>

            <!-- View: OVERVIEW -->
            <div id="view-overview" style="display: none;">
                <div class="kpi-row">
                    <div class="kpi-card">
                        <div class="kpi-label">Avg. Market Index</div>
                        <div class="kpi-value" id="ov-kpi-index">--</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Tracked SKUs</div>
                        <div class="kpi-value" id="ov-kpi-skus">--</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Health Score</div>
                        <div class="kpi-value" style="color: var(--success)">92%</div>
                    </div>
                </div>
                <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr;">
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">Recent Activity</h3></div>
                        <div id="ov-alerts-feed"></div>
                    </div>
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">Strategy Mix</h3></div>
                        <div style="height: 200px; display: flex; align-items: center; justify-content: center; color: var(--text-dim);">
                             <!-- Mini Strategy Chart -->
                             <div style="display: flex; gap: 20px; align-items: flex-end; height: 120px;">
                                <div style="height: 70%; width: 40px; background: var(--accent); border-radius: 6px;"></div>
                                <div style="height: 30%; width: 40px; background: var(--text-dim); border-radius: 6px;"></div>
                                <div style="height: 50%; width: 40px; background: var(--accent); border-radius: 6px; opacity: 0.5;"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- View: BENCHMARKING (The Original) -->
            <div id="view-benchmarking">
                <div class="dashboard-grid">
                    <div class="kpi-row">
                        <div class="kpi-card">
                            <div class="kpi-label">Avg. Market Index</div>
                            <div class="kpi-value" id="kpi-index">--</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Tracked SKUs</div>
                            <div class="kpi-value" id="kpi-skus">--</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Pending Recs</div>
                            <div class="kpi-value" id="kpi-recs" style="color: var(--warning)">--</div>
                        </div>
                    </div>
                    <div class="dashboard-left" style="grid-column: span 1; display: flex; flex-direction: column; gap: 24px;">
                        <div class="card">
                            <div class="card-header"><h3 class="card-title">Portfolio Position Map</h3></div>
                            <div class="position-map">
                                <div class="zone-bar"><div class="zone-marker" id="portfolio-marker"></div></div>
                                <div class="zone-labels"><span>Below</span><span>Budget</span><span>Value</span><span>Mid</span><span>Premium</span><span>Above</span></div>
                            </div>
                        </div>
                        <div class="card">
                            <div class="card-header"><h3 class="card-title">Repricing Recommendations</h3></div>
                            <div class="table-container">
                                <table><thead><tr><th>SKU / ASIN</th><th>Current</th><th>Target</th><th>Action</th><th>Reasoning</th></tr></thead>
                                <tbody id="recs-body"></tbody></table>
                            </div>
                        </div>
                    </div>
                    <div class="dashboard-right">
                        <div class="card">
                            <div class="card-header"><h3 class="card-title">Live Alerts</h3></div>
                            <div id="alerts-feed"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- View: ALERTS (Full Page) -->
            <div id="view-alerts" style="display: none;">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">All Price Alerts</h3></div>
                    <div id="full-alerts-feed"></div>
                </div>
            </div>

            <!-- View: AUDIT (Performance) -->
            <div id="view-audit" style="display: none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Performance & Pricing Correlation</h3>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>ASIN / Date</th>
                                    <th>Orders</th>
                                    <th>Sessions</th>
                                    <th>ACoS</th>
                                    <th>CVR</th>
                                    <th>Last Updated</th>
                                </tr>
                            </thead>
                            <tbody id="audit-body"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        const API_BASE = '/api/v1/benchmarking';
        let currentClientId = 's2c-uae';
        let activeTab = 'benchmarking';

        // Tab Switching Logic
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = item.textContent.trim().toLowerCase();
                switchTab(tabName);
            });
        });

        function switchTab(tab) {
            activeTab = tab;
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');
            
            // Hide all sections
            document.getElementById('view-overview').style.display = 'none';
            document.getElementById('view-benchmarking').style.display = 'none';
            document.getElementById('view-alerts').style.display = 'none';
            document.getElementById('view-audit').style.display = 'none';
            
            // Show active section
            document.getElementById(`view-${tab}`).style.display = 'block';
            
            refreshData();
        }

        async function refreshData() {
            try {
                if (activeTab === 'overview' || activeTab === 'benchmarking') {
                    const overviewResp = await fetch(`${API_BASE}/overview?client_id=${currentClientId}`);
                    const overviewData = await overviewResp.json();
                    renderOverview(overviewData.rows);
                }

                if (activeTab === 'benchmarking') {
                    const recsResp = await fetch(`${API_BASE}/recommendations?client_id=${currentClientId}`);
                    const recsData = await recsResp.json();
                    renderRecommendations(recsData.recommendations);
                }

                if (activeTab === 'alerts' || activeTab === 'overview') {
                    const alertsResp = await fetch(`${API_BASE}/alerts?client_id=${currentClientId}`);
                    const alertsData = await alertsResp.json();
                    renderAlerts(alertsData.alerts, activeTab === 'overview' ? 5 : 50);
                }

                if (activeTab === 'audit') {
                    const perfResp = await fetch(`${API_BASE}/performance?client_id=${currentClientId}`);
                    const perfData = await perfResp.json();
                    renderPerformanceAudit(perfData.rows);
                }

            } catch (err) {
                console.error('Data refresh failed:', err);
            }
        }

        function renderOverview(rows) {
            if (!rows || rows.length === 0) return;
            
            const avgIndex = rows.reduce((acc, r) => acc + (r.index_vs_median || 100), 0) / rows.length;
            const indexElem = document.getElementById('kpi-index');
            const ovIndexElem = document.getElementById('ov-kpi-index');
            if(indexElem) indexElem.textContent = avgIndex.toFixed(1);
            if(ovIndexElem) ovIndexElem.textContent = avgIndex.toFixed(1);
            
            const skusElem = document.getElementById('kpi-skus');
            const ovSkusElem = document.getElementById('ov-kpi-skus');
            if(skusElem) skusElem.textContent = rows.length;
            if(ovSkusElem) ovSkusElem.textContent = rows.length;

            const portfolioMarker = document.getElementById('portfolio-marker');
            if(portfolioMarker) {
                const zoneMap = { 'below_market': 5, 'budget': 20, 'value': 40, 'mid_market': 60, 'premium': 80, 'above_market': 95 };
                let avgPos = rows.reduce((acc, r) => acc + (zoneMap[r.zone] || 50), 0) / rows.length;
                portfolioMarker.style.left = `${avgPos}%`;
            }
        }

        function renderRecommendations(recs) {
            const body = document.getElementById('recs-body');
            if (!body) return;
            if (!recs || recs.length === 0) {
                body.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 40px;">No pending recommendations</td></tr>';
                return;
            }

            body.innerHTML = recs.map(r => `
                <tr>
                    <td>
                        <div style="font-weight: 600;">${r.sku_id}</div>
                        <div style="font-size: 12px; color: var(--text-dim);">${r.asin}</div>
                    </td>
                    <td><span class="price-badge">${r.current_price.toFixed(2)}</span></td>
                    <td><span class="price-badge" style="color: var(--accent)">${r.recommended_price.toFixed(2)}</span></td>
                    <td><span class="action-chip action-${r.action}">${r.action}</span></td>
                    <td style="color: var(--text-dim); font-size: 13px; max-width: 300px;">
                        ${r.reasoning}
                    </td>
                </tr>
            `).join('');
            
            const kpiRecs = document.getElementById('kpi-recs');
            if(kpiRecs) kpiRecs.textContent = recs.length;
        }

        function renderAlerts(alerts, limit = 50) {
            const targetId = activeTab === 'overview' ? 'ov-alerts-feed' : (activeTab === 'alerts' ? 'full-alerts-feed' : 'alerts-feed');
            const container = document.getElementById(targetId);
            if (!container) return;
            
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: var(--text-dim); padding: 40px;">No recent alerts</div>';
                return;
            }

            const items = alerts.slice(0, limit);
            container.innerHTML = items.map(a => `
                <div class="alert-item">
                    <div class="alert-icon alert-${a.severity}">
                        ${a.alert_type === 'floor_breach' ? '▼' : '▲'}
                    </div>
                    <div class="alert-content">
                        <h4>${a.title}</h4>
                        <p>${a.message}</p>
                        <div class="alert-time">${new Date(a.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                    </div>
                </div>
            `).join('');
        }

        function renderPerformanceAudit(rows) {
            const body = document.getElementById('audit-body');
            if (!body) return;
            if (!rows || rows.length === 0) {
                body.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 40px;">No performance data found.</td></tr>';
                return;
            }

            body.innerHTML = rows.map(r => `
                <tr>
                    <td>
                        <div style="font-weight: 600;">${r.asin}</div>
                        <div style="font-size: 11px; color: var(--text-dim);">${r.performance_date}</div>
                    </td>
                    <td><span class="price-badge">${r.units_ordered || 0}</span></td>
                    <td><span class="price-badge">${r.sessions || 0}</span></td>
                    <td><span class="price-badge" style="color: ${r.acos > 35 ? 'var(--danger)' : 'var(--success)'}">${(r.acos || 0).toFixed(1)}%</span></td>
                    <td><span class="price-badge">${((r.units_ordered / (r.sessions || 1)) * 100).toFixed(2)}%</span></td>
                    <td style="font-size: 11px; color: var(--text-dim);">${new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
            `).join('');
        }

        // Initial Load
        switchTab('benchmarking');
        // Refresh every 60 seconds
        setInterval(refreshData, 60000);
    </script>
</body>
</html>
