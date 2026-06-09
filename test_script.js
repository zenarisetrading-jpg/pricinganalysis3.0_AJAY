
        const API_BASE = '/api/v1/benchmarking';
        let currentClientId = 's2c-uae';
        let activeTab = 'benchmarking';
        let testCatalog = [];
        let simulationActive = false;
        let simulationResults = null;
        let overviewSnapshots = [];
        let globalRecommendations = [];
        let currentOverviewChartInstance = null;

        // Tab Switching Logic
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = item.getAttribute('data-tab');
                switchTab(tabName);
            });
        });

        function switchTab(tab, shouldRefresh = true) {
            activeTab = tab;
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');

            // Hide all sections
            document.getElementById('view-benchmarking').style.display = 'none';
            document.getElementById('view-categories').style.display = 'none';

            // Show active section
            const targetEl = document.getElementById(`view-${tab}`);
            if (targetEl) targetEl.style.display = 'block';

            if (shouldRefresh) refreshData();
        }

        // Account Selection Logic
        const accountSelector = document.getElementById('account-selector');
        accountSelector.addEventListener('change', (e) => {
            currentClientId = e.target.value;
            simulationActive = false;
            simulationResults = null;
            testCatalog = [];
            

            
            refreshData();
        });

        async function fetchAccounts() {
            try {
                const resp = await fetch(`${API_BASE}/accounts`, {
                    headers: { 'X-Internal-Token': 'saddl_secret_token_123' }
                });
                const data = await resp.json();
                
                if (data.accounts && data.accounts.length > 0) {
                    accountSelector.innerHTML = data.accounts.map(acc => 
                        `<option value="${acc.client_id}" ${acc.client_id === currentClientId ? 'selected' : ''}>
                            ${acc.client_name || acc.client_id} [${acc.client_id}]
                        </option>`
                    ).join('');
                    
                    if (!currentClientId || !data.accounts.find(a => a.client_id === currentClientId)) {
                        currentClientId = data.accounts[0].client_id;
                    }
                    accountSelector.value = currentClientId; 
                    refreshData();
                } else {
                    accountSelector.innerHTML = '<option value="" disabled selected>No accounts found</option>';
                }
            } catch (err) {
                console.error('Failed to fetch accounts:', err);
                accountSelector.innerHTML = '<option value="" disabled selected>Error loading accounts</option>';
            }
        }


        // Common File Processor
        async function processFileContent(file, text) {
            let records = [];
            if (file.name.endsWith('.json')) {
                const raw = JSON.parse(text);
                records = Array.isArray(raw) ? raw : (raw.records || []);
                // Map flexible prices and nested objects
                records.forEach(r => {
                    let rawPrice = r.floor_price || r.price || r.selling_price || r.buy_box_price || r.amount || r.listing_price;
                    if (rawPrice && typeof rawPrice === 'object') {
                        rawPrice = rawPrice.value || rawPrice.amount || rawPrice.price;
                    }
                    r.floor_price = parseFloat(rawPrice);
                    r.price = r.floor_price; // Consistency
                    r.asin = r.asin || r.ASIN;
                    r.sku = r.sku || r.sku_id || r.SKU;
                    r.marketplace = r.marketplace || 'UAE';
                });
            } else if (file.name.endsWith('.csv')) {
                records = parseCSV(text);
            }
            return records;
        }

        function parseCSV(text) {
            const lines = text.split('\n');
            if (lines.length < 2) return [];
            const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
            return lines.slice(1).filter(l => l.trim()).map(line => {
                const values = line.split(',').map(v => v.trim());
                const obj = {};
                headers.forEach((h, i) => {
                    let val = values[i];
                    if (['floor_price', 'buy_box_price', 'shipping_price', 'price', 'selling price', 'selling_price', 'amount'].includes(h)) {
                        val = parseFloat(val);
                    } else if (h === 'is_buy_box_winner') {
                        val = val.toLowerCase() === 'true';
                    }
                    obj[h] = val;
                });
                
                // Map common price columns to floor_price if missing
                if (!obj.floor_price) {
                    obj.floor_price = obj.price || obj['selling price'] || obj.selling_price || obj.amount || obj.buy_box_price;
                }
                obj.marketplace = obj.marketplace || 'UAE';
                return obj;
            });
        }

        function resetKPIs() {
            const kpis = ['kpi-health', 'kpi-index', 'kpi-skus', 'kpi-recs'];
            kpis.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = '--';
            });
            const portfolioMarker = document.getElementById('portfolio-marker');
            if (portfolioMarker) portfolioMarker.style.left = '50%';
            const panel = document.getElementById('product-metrics-panel');
            if (panel) panel.style.display = 'none';
        }

        async function refreshData() {
            try {
                // Always fetch overview and alerts as they are core to the selected account
                const headers = { 
                    'X-Client-Id': currentClientId,
                    'X-Internal-Token': 'saddl_secret_token_123'
                };
                
                // Fetch recommendations first so they are available globally for the overview chart
                try {
                    const recsResp = await fetch(`${API_BASE}/recommendations?client_id=${currentClientId}`, { headers });
                    if (recsResp.ok) {
                        const recsData = await recsResp.json();
                        globalRecommendations = recsData.recommendations || [];
                    }
                } catch (e) {
                    console.error('Failed to fetch recommendations:', e);
                }

                const overviewResp = await fetch(`${API_BASE}/overview?client_id=${currentClientId}`, { headers });
                if (!overviewResp.ok) throw new Error(`HTTP ${overviewResp.status}`);
                const overviewData = await overviewResp.json();
                renderOverview(overviewData.rows, overviewData);

                if (activeTab === 'benchmarking') {
                    renderRecommendations(globalRecommendations);
                }

                const alertsResp = await fetch(`${API_BASE}/alerts?client_id=${currentClientId}`, { headers });
                if (alertsResp.ok) {
                    const alertsData = await alertsResp.json();
                    renderAlerts(alertsData.alerts);
                }



                if (activeTab === 'categories') {
                    const catsResp = await fetch(`${API_BASE}/account-bsr-categories?account_id=${currentClientId}`, { headers });
                    if (catsResp.ok) {
                        const catsData = await catsResp.json();
                        window.allCategories = catsData.categories; // Store for searching
                        renderCategories(catsData.categories);
                    }
                }

            } catch (err) {
                console.error('Data refresh failed:', err);
                resetKPIs();
                // Optionally show a small error toast or update sub-title
                const subTitle = document.getElementById('sub-title');
                if (subTitle) {
                    subTitle.innerHTML = `<span style="color: var(--danger)">⚠️ Connection Lost: ${err.message}. Database may be disconnected.</span> <a href="#" onclick="refreshData()" style="color: var(--accent); margin-left: 10px; text-decoration: underline; font-size: 11px;">Retry</a>`;
                }
            }
        }



        // Category Search Event
        document.getElementById('category-search').addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            if (!window.allCategories) return;

            if (!term) {
                renderCategories(window.allCategories);
                return;
            }

            // Split commas into alternative phrases. Words inside a phrase must all match.
            const keywordGroups = term
                .split(',')
                .map(phrase => phrase.trim().split(/\s+/).filter(k => k))
                .filter(group => group.length > 0);
            
            if (keywordGroups.length === 0) {
                renderCategories(window.allCategories);
                return;
            }

            // For each category, we check if any of its products match any keyword group.
            const filtered = window.allCategories.map(c => {
                // Filter the products in this category.
                // A product matches if, for every keyword in any group, the keyword matches
                // either the product title, the product ASIN, or the product reference name.
                const matchingProducts = (c.products || []).filter(p => {
                    const titleLower = (p.title || '').toLowerCase();
                    const asinLower = (p.asin || '').toLowerCase();
                    const refLower = (p.reference_name || '').toLowerCase();
                    
                    return keywordGroups.some(group =>
                        group.every(kw =>
                            titleLower.includes(kw) ||
                            asinLower.includes(kw) ||
                            refLower.includes(kw)
                        )
                    );
                });
                
                // If there are matching products, we return this category with the matching products list
                if (matchingProducts.length > 0) {
                    return {
                        ...c,
                        products: matchingProducts
                    };
                }
                return null;
            }).filter(Boolean);

            renderCategories(filtered);
        });

        function generatePricingDistribution(row, rawCompetitors = [], sampleSize = 200, binCount = 10) {
            const min = parseFloat(row.floor_price);
            const p25 = parseFloat(row.p25_price);
            const median = parseFloat(row.median_price);
            const p75 = parseFloat(row.p75_price);
            const max = parseFloat(row.ceiling_price);
            const count = parseInt(row.n_competitors) || 0;

            if (isNaN(min) || isNaN(max) || count === 0) return null;

            // Handle edge case: zero price spread
            if (max <= min) {
                return {
                    bins: [{
                        label: `${min.toFixed(1)}`,
                        mid: min,
                        start: min,
                        end: min,
                        count: count,
                        competitors: rawCompetitors,
                        brands: [],
                        actualAvg: min,
                        actualMedian: min
                    }],
                    min, max, p25, median, p75
                };
            }

            // 1. Synthetic Population Interpolation
            const prices = [];
            for (let i = 0; i <= sampleSize; i++) {
                const q = i / sampleSize;
                let p = 0;
                if (q <= 0.25) {
                    p = min + (q / 0.25) * (p25 - min);
                } else if (q <= 0.50) {
                    p = p25 + ((q - 0.25) / 0.25) * (median - p25);
                } else if (q <= 0.75) {
                    p = median + ((q - 0.50) / 0.25) * (p75 - median);
                } else {
                    p = p75 + ((q - 0.75) / 0.25) * (max - p75);
                }
                
                // Introduce a micro-Gaussian jitter to smooth out density peaks
                const jitter = (Math.random() - 0.5) * 0.015 * (max - min);
                prices.push(Math.max(min, Math.min(max, p + jitter)));
            }

            // 2. Frequency Binning
            const binWidth = (max - min) / binCount;
            if (binWidth <= 0) return null;
            const bins = [];
            for (let i = 0; i < binCount; i++) {
                const binStart = min + i * binWidth;
                const binEnd = binStart + binWidth;
                bins.push({
                    label: `${binStart.toFixed(1)} - ${binEnd.toFixed(1)}`,
                    mid: binStart + binWidth / 2,
                    start: binStart,
                    end: binEnd,
                    count: 0,
                    competitors: [],
                    brands: [],
                    actualAvg: 0,
                    actualMedian: 0
                });
            }

            prices.forEach(price => {
                for (let i = 0; i < binCount; i++) {
                    if (price >= bins[i].start && (i === binCount - 1 ? price <= bins[i].end : price < bins[i].end)) {
                        bins[i].count++;
                        break;
                    }
                }
            });

            // Map actual raw competitors into the bins based on their price securely
            rawCompetitors.forEach(comp => {
                const p = parseFloat(comp.price);
                if (isNaN(p)) return;
                
                // Clamp to prevent dropping items due to database floor_price rounding
                const clampedP = Math.max(min, Math.min(max, p));
                const epsilon = 0.0001; // Absorb floating point JS drift
                let assigned = false;
                
                for (let i = 0; i < binCount; i++) {
                    const isLast = (i === binCount - 1);
                    if (clampedP >= (bins[i].start - epsilon) && (isLast ? clampedP <= (bins[i].end + epsilon) : clampedP < bins[i].end)) {
                        bins[i].competitors.push(comp);
                        assigned = true;
                        break;
                    }
                }
                
                // Absolute safety net guarantees no dropped competitors
                if (!assigned && binCount > 0) {
                    if (clampedP < bins[0].start) bins[0].competitors.push(comp);
                    else bins[binCount - 1].competitors.push(comp);
                }
            });

            // Aggregate brand counts and actual prices per bin
            bins.forEach(b => {
                if (b.competitors.length > 0) {
                    const brandCounts = {};
                    let sum = 0;
                    const compPrices = [];
                    
                    b.competitors.forEach(c => {
                        let brandRaw = c.brand || '';
                        if (brandRaw === 'None' || brandRaw === 'null') {
                            brandRaw = '';
                        }
                        if (!brandRaw || brandRaw.trim() === '') {
                            const titleWords = (c.title || 'Unknown Brand').split(' ').filter(w => w.trim() !== '');
                            // Extract first two words for better identification if no brand exists
                            brandRaw = titleWords.slice(0, 2).join(' ');
                        }
                        
                        // Normalize brand string to group effectively (e.g. "stanley" and "Stanley ")
                        const brand = brandRaw.trim().replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
                        
                        brandCounts[brand] = (brandCounts[brand] || 0) + 1;
                        
                        const p = parseFloat(c.price);
                        sum += p;
                        compPrices.push(p);
                    });
                    
                    b.brands = Object.entries(brandCounts)
                        .map(([name, count]) => ({ name, count }))
                        .sort((a, b) => b.count - a.count);
                    
                    b.actualAvg = sum / b.competitors.length;
                    
                    compPrices.sort((x, y) => x - y);
                    const midIdx = Math.floor(compPrices.length / 2);
                    if (compPrices.length % 2 === 0) {
                        b.actualMedian = (compPrices[midIdx - 1] + compPrices[midIdx]) / 2;
                    } else {
                        b.actualMedian = compPrices[midIdx];
                    }
                }
            });

            // Normalize densities to sum up to N (competitor count)
            const scale = count / prices.length;
            bins.forEach(b => {
                b.count = parseFloat((b.count * scale).toFixed(1));
            });

            return { bins, min, max, p25, median, p75 };
        }

        function renderPricingHistogram(row) {
            const container = document.getElementById('overview-histogram-chart');
            const emptyState = document.getElementById('overview-chart-empty');
            const loader = document.getElementById('overview-chart-loading');
            const panel = document.getElementById('product-metrics-panel');

            if (loader) loader.style.display = 'none';

            if (!row || !row.floor_price || !row.ceiling_price || !row.n_competitors) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                if (panel) panel.style.display = 'none';
                return;
            }

            const count = parseInt(row.n_competitors) || 0;
            if (count === 0) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                if (panel) panel.style.display = 'none';
                return;
            }

            if (container) container.style.display = 'block';
            if (emptyState) emptyState.style.display = 'none';

            const matchedRec = globalRecommendations.find(rec => {
                const recKey = rec.parent_asin || rec.asin;
                const rowKey = row.parent_asin || row.asin;
                return recKey === rowKey || rec.asin === row.asin || rec.parent_asin === row.parent_asin;
            });
            const targetPriceVal = (matchedRec && matchedRec.recommended_price) 
                ? parseFloat(matchedRec.recommended_price) 
                : parseFloat(row.median_price);

            // Update Product-specific Metrics Panel & Break-even calculations
            if (panel) {
                // Store active product row globally for dynamic updates on COGS change
                window.activeProductRow = row;

                const curPriceEl = document.getElementById('product-current-price');
                const bePriceEl = document.getElementById('product-breakeven-price');
                const tgtPriceEl = document.getElementById('product-target-price');
                const badgeEl = document.getElementById('product-profitability-badge');
                const cogsInput = document.getElementById('product-cogs-input');
                
                const yourPriceVal = parseFloat(row.your_price);
                const currency = 'AED';

                if (curPriceEl && bePriceEl && tgtPriceEl && badgeEl && cogsInput) {
                    const parentAsin = row.parent_asin || row.asin;
                    const cogsKey = `saddl_cogs_${currentClientId}_${parentAsin}`;
                    
                    // Setup the input field value from localStorage
                    const savedCogs = localStorage.getItem(cogsKey);
                    
                    // Temporarily remove standard event listener to avoid infinite loops when setting value programmatically
                    cogsInput.oninput = null;
                    cogsInput.value = savedCogs !== null ? savedCogs : '';
                    
                    // Add real-time event listener to save and re-calculate
                    cogsInput.oninput = (e) => {
                        const newCogs = e.target.value.trim();
                        if (newCogs === '' || parseFloat(newCogs) >= 0) {
                            if (newCogs === '') {
                                localStorage.removeItem(cogsKey);
                            } else {
                                localStorage.setItem(cogsKey, newCogs);
                            }
                            // Re-render overview metrics panel in real time
                            if (window.activeProductRow) {
                                renderPricingHistogram(window.activeProductRow);
                            }
                            // Re-render recommendations table to show warnings in real time
                            renderRecommendations(globalRecommendations);
                        }
                    };

                    panel.style.display = 'flex';
                    
                    // Render Current Price
                    if (!isNaN(yourPriceVal) && yourPriceVal >= 0) {
                        curPriceEl.textContent = `${currency} ${yourPriceVal.toFixed(2)}`;
                    } else {
                        curPriceEl.textContent = '--';
                    }

                    // Render Target Price
                    if (targetPriceVal && !isNaN(targetPriceVal)) {
                        tgtPriceEl.textContent = `${currency} ${targetPriceVal.toFixed(2)}`;
                    } else {
                        tgtPriceEl.textContent = '--';
                    }

                    // Render Break-even Price & Profitability Badge
                    const parsedCogs = parseFloat(savedCogs);
                    if (savedCogs !== null && !isNaN(parsedCogs) && parsedCogs > 0) {
                        const breakEvenPrice = parsedCogs / 0.3;
                        bePriceEl.textContent = `${currency} ${breakEvenPrice.toLocaleString('en-AE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        
                        // Margin analysis against Current Price
                        const comparisonPrice = !isNaN(yourPriceVal) ? yourPriceVal : 0;
                        if (comparisonPrice < breakEvenPrice) {
                            badgeEl.style.display = 'inline-block';
                            badgeEl.style.background = 'rgba(239, 68, 68, 0.15)';
                            badgeEl.style.color = 'var(--danger)';
                            badgeEl.style.border = '1px solid rgba(239, 68, 68, 0.2)';
                            badgeEl.textContent = '⚠️ Unsafe Margin';
                        } else {
                            badgeEl.style.display = 'inline-block';
                            badgeEl.style.background = 'rgba(16, 185, 129, 0.15)';
                            badgeEl.style.color = 'var(--success)';
                            badgeEl.style.border = '1px solid rgba(16, 185, 129, 0.2)';
                            badgeEl.textContent = '✓ Margin Safe';
                        }
                    } else if (parsedCogs === 0) {
                        bePriceEl.textContent = `${currency} 0.00`;
                        badgeEl.style.display = 'inline-block';
                        badgeEl.style.background = 'rgba(245, 158, 11, 0.15)';
                        badgeEl.style.color = 'var(--warning)';
                        badgeEl.style.border = '1px solid rgba(245, 158, 11, 0.2)';
                        badgeEl.textContent = '⚠️ Enter COGS';
                    } else {
                        bePriceEl.textContent = '--';
                        badgeEl.style.display = 'none';
                    }
                }
            }

            const rawCompetitors = (matchedRec && matchedRec.metadata && matchedRec.metadata.competitors) 
                ? matchedRec.metadata.competitors 
                : [];

            const dataModel = generatePricingDistribution(row, rawCompetitors, 200, 10);
            if (!dataModel) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            const xLabels = dataModel.bins.map(b => b.mid);
            const densities = dataModel.bins.map(b => b.count);
            
            const yourPrice = parseFloat(row.your_price);
            const currency = 'AED';

            const options = {
                series: [
                    {
                        name: 'Competitor Count (Height)',
                        type: 'column',
                        data: densities
                    },
                    {
                        name: 'Market Pricing Wave',
                        type: 'line',
                        data: densities
                    }
                ],
                chart: {
                    height: 350,
                    type: 'line',
                    toolbar: { show: false },
                    background: 'transparent',
                    foreColor: '#949eb5'
                },
                stroke: {
                    width: [0, 3],
                    curve: 'smooth'
                },
                colors: ['rgba(91, 138, 240, 0.15)', '#5b8af0'],
                fill: {
                    type: ['solid', 'gradient'],
                    gradient: {
                        shade: 'dark',
                        type: 'vertical',
                        shadeIntensity: 0.5,
                        gradientToColors: ['#a78bfa'],
                        inverseColors: false,
                        opacityFrom: 0.8,
                        opacityTo: 0.2
                    }
                },
                dataLabels: {
                    enabled: false
                },
                xaxis: {
                    type: 'numeric',
                    categories: xLabels,
                    labels: {
                        formatter: (value) => `${currency} ${parseFloat(value).toFixed(1)}`,
                        style: { colors: '#949eb5', fontSize: '11px', fontFamily: 'Inter' }
                    },
                    axisBorder: { show: false },
                    axisTicks: { show: false }
                },
                yaxis: {
                    show: true,
                    title: {
                        text: 'Number of Competitors',
                        style: { color: '#949eb5', fontWeight: 500, fontSize: '11px' }
                    },
                    labels: {
                        style: { colors: '#949eb5' }
                    }
                },
                grid: {
                    borderColor: 'rgba(255, 255, 255, 0.05)',
                    strokeDashArray: 4
                },
                tooltip: {
                    shared: true,
                    intersect: false,
                    custom: function({series, seriesIndex, dataPointIndex, w}) {
                        const bin = dataModel.bins[dataPointIndex];
                        if (!bin) return '';
                        
                        let brandsHtml = '';
                        const totalComps = bin.competitors.length;
                        
                        if (totalComps > 0) {
                            const topBrands = bin.brands.slice(0, 4);
                            brandsHtml = `<ul style="list-style: none; padding: 0; margin: 0 0 10px 0;">` +
                                topBrands.map(b => `<li style="font-size: 13px; color: var(--text); margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;"><span style="flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 8px;">• ${b.name}</span><span style="color: var(--text-dim); font-size: 11px;">(${b.count})</span></li>`).join('') +
                                `</ul>`;
                            
                            if (bin.brands.length > 4) {
                                const remaining = bin.brands.length - 4;
                                brandsHtml += `<div style="font-size: 12px; color: var(--text-dim); font-style: italic; margin-bottom: 10px;">+${remaining} more brand${remaining > 1 ? 's' : ''}</div>`;
                            }
                        } else {
                            brandsHtml = `<div style="font-size: 13px; color: var(--text-dim); margin-bottom: 10px; font-style: italic;">No specific brands identified in this slice.</div>`;
                        }

                        const priceRange = `Price range: ${currency} ${(bin.start).toFixed(1)} - ${(bin.end).toFixed(1)}`;
                        
                        let footerHtml = '';
                        if (totalComps > 0) {
                            footerHtml = `
                                <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px; display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim);">
                                    <span>Avg: ${currency} ${bin.actualAvg.toFixed(2)}</span>
                                    <span>Med: ${currency} ${bin.actualMedian.toFixed(2)}</span>
                                </div>
                            `;
                        } else {
                            footerHtml = `<div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px; font-size: 12px; color: var(--text-dim);">Height Density: ${bin.count.toFixed(1)}</div>`;
                        }

                        return `
                            <div class="custom-tooltip" style="background: rgba(22, 25, 35, 0.9); backdrop-filter: blur(12px) saturate(180%); border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-radius: 8px; padding: 16px; min-width: 220px;">
                                <div style="font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 4px; letter-spacing: 0.5px; text-transform: uppercase;">
                                    ${priceRange}
                                </div>
                                <div style="font-size: 13px; color: var(--text); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                                    Competitors Found: <b style="color: white;">${totalComps}</b>
                                </div>
                                ${brandsHtml}
                                ${footerHtml}
                            </div>
                        `;
                    }
                },
                legend: { show: false },
                annotations: {
                    xaxis: [
                        // 1. Target Price Line Annotation
                        {
                            x: targetPriceVal,
                            borderColor: '#f59e0b',
                            strokeDashArray: 5,
                            borderWidth: 2,
                            label: {
                                style: { color: '#fff', background: '#f59e0b', fontSize: '10px', fontWeight: 700, padding: { left: 6, right: 6, top: 4, bottom: 4 } },
                                text: `Target Price: ${currency} ${Number.isFinite(targetPriceVal) ? targetPriceVal.toFixed(2) : '0.00'}`
                            }
                        }
                    ]
                }
            };

            // Add Your Price line if valid
            if (Number.isFinite(yourPrice) && yourPrice > 0) {
                options.annotations.xaxis.push({
                    x: yourPrice,
                    borderColor: '#10b981',
                    strokeDashArray: 0,
                    borderWidth: 3,
                    label: {
                        style: { color: '#fff', background: '#10b981', fontSize: '11px', fontWeight: 800, padding: { left: 8, right: 8, top: 5, bottom: 5 } },
                        text: `Our Price: ${currency} ${yourPrice.toFixed(2)}`
                    }
                });
            }

            if (currentOverviewChartInstance) {
                currentOverviewChartInstance.destroy();
            }

            currentOverviewChartInstance = new ApexCharts(document.getElementById('overview-histogram-chart'), options);
            currentOverviewChartInstance.render();
        }

        function renderOverview(rows, overviewData = {}) {
            if (!rows || rows.length === 0) {
                resetKPIs();
                return;
            }

            // Deduplicate by parent ASIN, keeping only the latest snapshot for each group.
            const latestRowsMap = new Map();
            rows.forEach(r => {
                const key = r.parent_asin || r.asin;
                const existing = latestRowsMap.get(key);
                if (!existing || new Date(r.snapshot_date) > new Date(existing.snapshot_date)) {
                    latestRowsMap.set(key, r);
                }
            });
            const uniqueRows = Array.from(latestRowsMap.values());
            
            // Store global reference for product switching
            overviewSnapshots = uniqueRows;

            // Clear error if any
            const subTitle = document.getElementById('sub-title');
            const simBanner = document.getElementById('sim-banner');
            if (subTitle && subTitle.textContent.includes('Connection Lost')) {
                subTitle.innerHTML = 'Real-time market positioning & repricing intelligence <span id="sim-banner" style="display:none; background: var(--warning-glow); color: var(--warning); padding: 2px 8px; border-radius: 6px; font-size: 11px; margin-left: 10px; border: 1px solid var(--warning);">SIMULATION MODE</span>';
            }

            const avgIndex = uniqueRows.reduce((acc, r) => {
                let val = parseFloat(r.index_vs_median);
                if (isNaN(val)) {
                    const yp = parseFloat(r.your_price);
                    const mp = parseFloat(r.median_price);
                    val = (yp > 0 && mp > 0) ? (yp / mp) * 100 : 100;
                }
                return acc + val;
            }, 0) / (uniqueRows.length || 1);
            window.currentAvgMarketIndex = avgIndex;
            const indexElem = document.getElementById('kpi-index');
            if (indexElem) indexElem.textContent = avgIndex.toFixed(1);

            const activeCategory = (document.getElementById('overview-category-filter') || {}).value || 'all';
            const parentCount = Number(overviewData.parent_asin_count);
            const skusCount = (activeCategory === 'all' && Number.isFinite(parentCount) && parentCount > 0)
                ? parentCount
                : uniqueRows.length;
            const skusElem = document.getElementById('kpi-skus');
            if (skusElem) skusElem.textContent = skusCount;

            // Dynamic Health Score Calculation
            const healthyZones = ['budget', 'value', 'mid_market', 'premium'];
            const healthyCount = uniqueRows.filter(r => healthyZones.includes(r.zone)).length;
            const healthScore = Math.round((healthyCount / uniqueRows.length) * 100);
            const healthElem = document.getElementById('kpi-health');
            if (healthElem) {
                healthElem.textContent = healthScore + '%';
                healthElem.style.color = healthScore > 80 ? 'var(--success)' : (healthScore > 50 ? 'var(--warning)' : 'var(--danger)');
            }

            const portfolioMarker = document.getElementById('portfolio-marker');
            if (portfolioMarker) {
                const zoneMap = { 'below_market': 5, 'budget': 20, 'value': 40, 'mid_market': 60, 'premium': 80, 'above_market': 95 };
                let avgPos = uniqueRows.reduce((acc, r) => acc + (zoneMap[r.zone] || 50), 0) / uniqueRows.length;
                portfolioMarker.style.left = `${avgPos}%`;
            }

            // Populate Overview Product Selector dropdown
            const selector = document.getElementById('overview-product-selector');
            if (selector) {
                const previousSelection = selector.value;
                
                selector.innerHTML = `<option value="" disabled>Select Product to Analyze...</option>` + 
                    uniqueRows.map((r, index) => {
                        const displayName = r.reference_name || r.parent_asin || r.asin;
                        const isSelected = previousSelection 
                            ? (r.asin === previousSelection) 
                            : (index === 0);
                        return `<option value="${r.asin}" ${isSelected ? 'selected' : ''}>
                            ${displayName} (${r.asin})
                        </option>`;
                    }).join('');

                // Render Chart for the currently selected product
                const activeAsin = selector.value;
                const activeRow = uniqueRows.find(r => r.asin === activeAsin);
                if (activeRow) {
                    renderPricingHistogram(activeRow);
                    updatePortfolioMarkers(activeRow);
                } else if (uniqueRows.length > 0) {
                    // Fallback to first if mismatch
                    selector.value = uniqueRows[0].asin;
                    renderPricingHistogram(uniqueRows[0]);
                    updatePortfolioMarkers(uniqueRows[0]);
                } else {
                    renderPricingHistogram(null);
                }
            }
        }

        function updatePortfolioMarkers(selectedRow) {
            if (!selectedRow) return;
            const marketIndex = window.currentAvgMarketIndex || 100;
            
            // Look up in globalRecommendations for accurate min/max/percentile info
            let targetRec = globalRecommendations.find(r => (r.parent_asin || r.asin) === (selectedRow.parent_asin || selectedRow.asin));
            targetRec = targetRec || selectedRow;
            
            const rawMedian = parseFloat(targetRec.median_price || targetRec.recommended_price) || 0;
            const currentPrice = parseFloat(targetRec.your_price || targetRec.current_price) || 0;
            
            const adjMedian = rawMedian * (marketIndex / 100);

            const pMin = parseFloat(targetRec.floor_price) || 0;
            const p25 = parseFloat(targetRec.p25_price) || 0;
            const p50 = adjMedian;
            const p75 = parseFloat(targetRec.p75_price) || 0;
            const pMax = parseFloat(targetRec.ceiling_price) || 0;
            
            function priceToPercentile(p) {
                if (!p || !pMax) return 50;
                if (p <= pMin) return 0;
                if (p >= pMax) return 100;
                if (p <= p25) return 0 + ((p - pMin) / (p25 - pMin || 1)) * 25;
                if (p <= p50) return 25 + ((p - p25) / (p50 - p25 || 1)) * 25;
                if (p <= p75) return 50 + ((p - p50) / (p75 - p50 || 1)) * 25;
                return 75 + ((p - p75) / (pMax - p75 || 1)) * 25;
            }
            
            const adjMedianPct = priceToPercentile(adjMedian);
            const currentPct = priceToPercentile(currentPrice);
            
            const markerOrig = document.getElementById('portfolio-marker');
            const markerAdj = document.getElementById('portfolio-marker-adjusted');
            const markerCurr = document.getElementById('portfolio-marker-current');
            const legend = document.getElementById('portfolio-map-legend');
            
            if (markerOrig) {
                markerOrig.style.display = 'none';
            }
            if (markerAdj) {
                markerAdj.style.display = 'block';
                markerAdj.style.left = `${adjMedianPct}%`;
                markerAdj.title = `Adjusted Median: AED ${adjMedian.toFixed(2)}`;
            }
            if (markerCurr) {
                if (currentPrice > 0) {
                    markerCurr.style.display = 'block';
                    markerCurr.style.left = `${currentPct}%`;
                    markerCurr.title = `Current Price: AED ${currentPrice.toFixed(2)}`;
                } else {
                    markerCurr.style.display = 'none';
                }
            }
            if (legend) {
                legend.style.display = 'flex';
            }
        }

        function renderRecommendations(recs) {
            const body = document.getElementById('recs-body');
            const kpiRecs = document.getElementById('kpi-recs');
            if (!body) return;
            
            if (!recs || recs.length === 0) {
                body.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 40px;">No pending recommendations</td></tr>';
                if (kpiRecs) kpiRecs.textContent = '0';
                return;
            }

            // Deduplicate by Parent ASIN — prefer row where asin === parent_asin as the representative
            const parentMap = new Map();
            recs.forEach(r => {
                const key = r.parent_asin || r.asin;
                if (!parentMap.has(key)) {
                    parentMap.set(key, r);
                } else {
                    const existing = parentMap.get(key);
                    // Prefer the row where the asin IS the parent_asin (canonical representative)
                    const isCurrent = r.asin === r.parent_asin;
                    const existingIsCanonical = existing.asin === existing.parent_asin;
                    if (isCurrent && !existingIsCanonical) {
                        parentMap.set(key, r);
                    }
                }
            });

            let processedRecs = Array.from(parentMap.values());

            // 1. Apply Search Filter
            const searchVal = (document.getElementById('recs-search')?.value || '').toLowerCase().trim();
            if (searchVal) {
                processedRecs = processedRecs.filter(r => {
                    const asin = (r.parent_asin || r.asin || '').toLowerCase();
                    const title = (r.title || '').toLowerCase();
                    const reasoning = (r.reasoning || '').toLowerCase();
                    return asin.includes(searchVal) || title.includes(searchVal) || reasoning.includes(searchVal);
                });
            }

            // 2. Apply Action Filter
            const actionFilter = document.getElementById('recs-action-filter')?.value || 'all';
            if (actionFilter !== 'all') {
                processedRecs = processedRecs.filter(r => (r.action || '').toLowerCase() === actionFilter);
            }

            // 3. Precompute competitor count for each record for easy sorting
            processedRecs.forEach(r => {
                const metaCount = r.metadata && Number(r.metadata.n_competitors);
                const reasonMatch = String(r.reasoning || '').match(/^(\d+)\s+competitors/i);
                r._competitorCount = Number.isFinite(metaCount) ? metaCount : (reasonMatch ? Number(reasonMatch[1]) : 0);
            });

            // 4. Apply Sort
            const sortBy = document.getElementById('recs-sort-by')?.value || 'default';
            if (sortBy === 'default') {
                processedRecs.sort((a, b) => {
                    if (a.action !== b.action) return a.action === 'decrease' ? -1 : 1;
                    return (a.parent_asin || a.asin).localeCompare(b.parent_asin || b.asin);
                });
            } else if (sortBy === 'asin-asc') {
                processedRecs.sort((a, b) => (a.parent_asin || a.asin).localeCompare(b.parent_asin || b.asin));
            } else if (sortBy === 'asin-desc') {
                processedRecs.sort((a, b) => (b.parent_asin || b.asin).localeCompare(a.parent_asin || a.asin));
            } else if (sortBy === 'title-asc') {
                processedRecs.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
            } else if (sortBy === 'title-desc') {
                processedRecs.sort((a, b) => (b.title || '').localeCompare(a.title || ''));
            } else if (sortBy === 'current-desc') {
                processedRecs.sort((a, b) => (b.current_price || 0) - (a.current_price || 0));
            } else if (sortBy === 'current-asc') {
                processedRecs.sort((a, b) => (a.current_price || 0) - (b.current_price || 0));
            } else if (sortBy === 'target-desc') {
                processedRecs.sort((a, b) => (b.recommended_price || 0) - (a.recommended_price || 0));
            } else if (sortBy === 'target-asc') {
                processedRecs.sort((a, b) => (a.recommended_price || 0) - (b.recommended_price || 0));
            } else if (sortBy === 'competitors-desc') {
                processedRecs.sort((a, b) => b._competitorCount - a._competitorCount);
            }

            if (kpiRecs) kpiRecs.textContent = processedRecs.length;

            if (processedRecs.length === 0) {
                body.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 40px;">No matching recommendations</td></tr>';
                return;
            }

            body.innerHTML = processedRecs.map(r => {
                const cogsVal = localStorage.getItem(`saddl_cogs_${currentClientId}_${r.parent_asin || r.asin}`);
                const parsedCogs = parseFloat(cogsVal);
                let breakEvenPrice = null;
                let isUnsafe = false;
                if (cogsVal !== null && !isNaN(parsedCogs) && parsedCogs > 0) {
                    breakEvenPrice = parsedCogs / 0.3;
                    if ((r.recommended_price || 0) < breakEvenPrice) {
                        isUnsafe = true;
                    }
                }
                
                const rawMedian = r.recommended_price || 0;
                const marketIndex = window.currentAvgMarketIndex || 100;
                const adjMedian = rawMedian * (marketIndex / 100);
                
                return `
                <tr data-asin="${r.parent_asin || r.asin}" style="border-left: 3px solid ${isUnsafe ? 'var(--danger)' : 'var(--accent)'}; ${isUnsafe ? 'background: rgba(239, 68, 68, 0.02);' : ''}">
                    <td>
                        <div style="font-weight: 700; color: var(--text); margin-bottom: 6px;">${r.parent_asin || r.asin}</div>
                        <div style="font-weight: 600; color: var(--text); font-size: 13px; line-height: 1.4; max-width: 300px; word-break: break-word;" title="${r.title || 'Parent ASIN Group'}">${r.title || 'Parent ASIN Group'}</div>
                    </td>
                    <td><span class="price-badge" style="color: ${r._competitorCount > 0 ? 'var(--success)' : 'var(--danger)'}">${r._competitorCount.toLocaleString()}</span></td>
                    <td><span class="price-badge">${(r.current_price || 0).toFixed(2)}</span></td>
                    <td>
                        <span class="price-badge" style="color: ${isUnsafe ? 'var(--danger)' : 'var(--accent)'}; font-weight: 700;">${rawMedian.toFixed(2)}</span>
                    </td>
                    <td>
                        <span class="price-badge" style="color: var(--warning); font-weight: 700;">${adjMedian.toFixed(2)}</span>
                    </td>
                    <td>
                        ${breakEvenPrice !== null ? `<div style="font-size: 13px; color: var(--text); font-weight: 500;">AED ${breakEvenPrice.toFixed(2)}</div>` : '--'}
                    </td>
                    <td>
                        <span class="action-chip action-${r.action}">${r.action}</span>
                        ${isUnsafe ? `<span style="background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); font-size: 9px; padding: 2px 8px; border-radius: 4px; display: block; margin-top: 6px; width: fit-content; text-transform: uppercase; font-weight: 700;">⚠️ Unsafe Margin</span>` : ''}
                    </td>
                    <td style="color: var(--text-dim); font-size: 13px; max-width: 400px; line-height: 1.4;">
                        ${isUnsafe ? `
                            <div style="color: var(--danger); font-weight: 600; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                                Potential loss-making pricing: target is below break-even (AED ${breakEvenPrice.toFixed(2)})
                            </div>
                        ` : ''}
                        ${r.reasoning}
                    </td>
                    <td>
                        ${(() => {
                            const hasComp = r._competitorCount > 0;
                            const zone = (r.metadata && r.metadata.zone) || 'mid_market';
                            const zoneMap = { 'below_market': 5, 'budget': 20, 'value': 40, 'mid_market': 60, 'premium': 80, 'above_market': 95 };
                            const pct = hasComp ? (r.metadata && r.metadata.percentile_rank !== undefined ? r.metadata.percentile_rank : (zoneMap[zone] || 50)) : 50;
                            const readableZone = zone.replace(/_/g, ' ');
                            
                            if (hasComp) {
                                return `
                                    <div class="mini-zone-container" title="Percentile: ${pct.toFixed(1)}% | Zone: ${readableZone}">
                                        <div class="mini-zone-bar">
                                            <div class="mini-zone-marker" style="left: ${pct}%;"></div>
                                        </div>
                                        <div class="mini-zone-label zone-text-${zone}">${readableZone}</div>
                                    </div>
                                `;
                            } else {
                                return `
                                    <div class="mini-zone-container" style="opacity: 0.4;">
                                        <div class="mini-zone-bar" style="background: var(--border);"></div>
                                        <div class="mini-zone-label">No Competitors</div>
                                    </div>
                                `;
                            }
                        })()}
                    </td>
                </tr>
            `}).join('');

        }

        function renderAlerts(alerts) {
            renderAlertFeed('alerts-feed', alerts, 10);
        }

        function renderAlertFeed(targetId, alerts, limit = 50) {
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
                        <div class="alert-time">${new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                    </div>
                </div>
            `).join('');
        }



        function renderCategories(cats) {
            const body = document.getElementById('categories-body');
            if (!body) return;
            if (!cats || cats.length === 0) {
                body.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 40px;">No product ranking data found.</td></tr>';
                return;
            }

            let rowsHtml = '';
            
            // Sort categories by their best performing product
            const sortedCats = [...cats].sort((a, b) => {
                const minA = Math.min(...(a.products || []).map(p => Number(p.rank) || 999999));
                const minB = Math.min(...(b.products || []).map(p => Number(p.rank) || 999999));
                return minA - minB;
            });

            sortedCats.forEach((c, cIndex) => {
                const products = Array.isArray(c.products) ? c.products : [];
                if (products.length === 0) return;

                // Sort products within category by Rank
                products.sort((a, b) => (Number(a.rank) || 999999) - (Number(b.rank) || 999999));
                
                const catIdSafe = c.category_name.replace(/[^a-zA-Z0-9]/g, '-');
                const groupClass = `cat-group-${catIdSafe}`;
                window.expandedCategoryGroups = window.expandedCategoryGroups || new Set();
                const isExpanded = window.expandedCategoryGroups.has(groupClass);

                // Category Header Row
                rowsHtml += `
                    <tr style="border-top: 2px solid var(--border); background: rgba(255,255,255,0.02);">
                        <td style="padding: 16px;">
                            <div style="font-weight: 700; color: var(--accent); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">${c.category_name}</div>
                        </td>
                        <td style="padding: 16px;">
                            <button onclick="toggleCategoryGroup('${groupClass}', this)" class="btn-toggle-details ${isExpanded ? 'active' : ''}" style="display: flex; align-items: center; gap: 8px;">
                                <svg class="toggle-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(${isExpanded ? '180deg' : '0deg'});">
                                    <path d="m6 9 6 6 6-6"/>
                                </svg>
                                <b>${products.length} Parent ASINs</b>
                            </button>
                        </td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                    </tr>
                `;

                // Product Rows (Hidden by default)
                products.forEach((p) => {
                    const rank = Number(p.rank || 0);
                    let statusClass = 'action-hold';
                    let statusText = 'Tracking';
                    
                    if (rank > 0 && rank < 10) {
                        statusClass = 'action-increase';
                        statusText = 'Top 10';
                    } else if (rank > 0 && rank < 100) {
                        statusClass = 'action-increase';
                        statusText = 'Top 100';
                    } else if (rank === 0) {
                        statusClass = 'action-hold';
                        statusText = 'Inactive';
                    }

                    // Parse brand exclusions delimiter on render
                    const parts = (p.exclude_keywords || '').split('|brand_exclude:');
                    const excludeKws = (parts[0] || '').trim();
                    const excludeBrands = (parts[1] || '').trim();

                    rowsHtml += `
                        <tr class="${groupClass}" style="display: ${isExpanded ? 'table-row' : 'none'}; background: rgba(0,0,0,0.1);">
                            <td style="padding: 12px 16px;"></td>
                            <td style="padding: 12px 16px;">
                                <div style="font-weight: 600; color: var(--text); font-size: 14px; line-height: 1.4;">${p.title || 'Untitled Product'}</div>
                            </td>
                            <td style="padding: 12px 16px;">
                                <span style="font-family: monospace; color: var(--text-dim); font-size: 12px;">${p.asin}</span>
                            </td>
                            <td style="padding: 12px 16px;">
                                <span class="price-badge" style="color: var(--success); font-weight: 700; background: rgba(0, 200, 83, 0.1);">
                                    ${rank > 0 ? '#' + rank.toLocaleString() : '--'}
                                </span>
                            </td>
                            <td style="padding: 12px 16px; min-width: 320px;">
                                <div style="display: flex; flex-direction: column; gap: 8px;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span style="font-size: 11px; color: var(--text-dim); width: 110px; text-align: right;">Include Keywords:</span>
                                        <input type="text" id="ref-name-${p.asin}" value="${p.reference_name || ''}" placeholder="e.g. Electrolyte Hydration Powder" style="
                                            background: var(--surface-solid);
                                            border: 1px solid var(--border);
                                            padding: 6px 10px;
                                            border-radius: 6px;
                                            color: var(--text);
                                            font-size: 12px;
                                            outline: none;
                                            flex-grow: 1;
                                        ">
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span style="font-size: 11px; color: var(--text-dim); width: 110px; text-align: right;">Exclude Keywords:</span>
                                        <input type="text" id="exclude-keywords-${p.asin}" value="${excludeKws}" placeholder="e.g. plastic, duplicate, charger" style="
                                            background: var(--surface-solid);
                                            border: 1px solid var(--border);
                                            padding: 6px 10px;
                                            border-radius: 6px;
                                            color: var(--text);
                                            font-size: 12px;
                                            outline: none;
                                            flex-grow: 1;
                                        ">
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span style="font-size: 11px; color: var(--text-dim); width: 110px; text-align: right;">Exclude Brands:</span>
                                        <input type="text" id="exclude-brands-${p.asin}" value="${excludeBrands}" placeholder="e.g. Stanley, Owala" style="
                                            background: var(--surface-solid);
                                            border: 1px solid var(--border);
                                            padding: 6px 10px;
                                            border-radius: 6px;
                                            color: var(--text);
                                            font-size: 12px;
                                            outline: none;
                                            flex-grow: 1;
                                        ">
                                    </div>
                                    <div style="display: flex; justify-content: flex-end;">
                                        <button onclick="saveReferenceName('${p.asin}')" class="btn-toggle-details" id="btn-save-${p.asin}" style="margin: 0; padding: 6px 12px; font-size: 11px;">
                                            Save Settings
                                        </button>
                                    </div>
                                </div>
                            </td>
                            <td style="padding: 12px 16px;">
                                <span class="action-chip ${statusClass}">${statusText}</span>
                            </td>
                        </tr>
                    `;
                });
            });

            body.innerHTML = rowsHtml || '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 40px;">No products found in monitored categories.</td></tr>';
        }
        
        async function saveReferenceName(parentAsin) {
            const inputVal = document.getElementById(`ref-name-${parentAsin}`).value;
            const excludeKwsVal = document.getElementById(`exclude-keywords-${parentAsin}`).value.trim();
            const excludeBrandsVal = document.getElementById(`exclude-brands-${parentAsin}`).value.trim();
            const btn = document.getElementById(`btn-save-${parentAsin}`);
            const originalText = btn.innerText;
            btn.innerText = 'Saving...';
            
            // Combine keywords and brands using delimiter
            let finalExcludeVal = excludeKwsVal;
            if (excludeBrandsVal) {
                finalExcludeVal = `${excludeKwsVal}|brand_exclude: ${excludeBrandsVal}`;
            }
            
            try {
                const resp = await fetch(`${API_BASE}/update-reference-name`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Client-Id': currentClientId,
                        'X-Internal-Token': 'saddl_secret_token_123'
                    },
                    body: JSON.stringify({
                        client_id: currentClientId,
                        parent_asin: parentAsin,
                        reference_name: inputVal,
                        exclude_keywords: finalExcludeVal
                    })
                });
                
                if (resp.ok) {
                    const payload = await resp.json();
                    const count = payload.analysis && Number(payload.analysis.priced_competitors);
                    btn.innerText = Number.isFinite(count) ? `${count} matched` : 'Saved!';
                    btn.style.color = 'var(--success)';
                    await refreshData();
                    setTimeout(() => { 
                        btn.innerText = originalText; 
                        btn.style.color = 'var(--accent)';
                    }, 2000);
                } else {
                    btn.innerText = 'Error';
                    btn.style.color = 'var(--danger)';
                    setTimeout(() => { btn.innerText = originalText; }, 2000);
                }
            } catch (e) {
                console.error(e);
                btn.innerText = 'Error';
            }
        }
        window.expandedCategoryGroups = window.expandedCategoryGroups || new Set();
        function toggleCategoryGroup(groupClass, btn) {
            const rows = document.querySelectorAll('.' + groupClass);
            const icon = btn.querySelector('.toggle-icon');
            if (rows.length === 0) return;
            const isVisible = rows[0].style.display !== 'none';

            rows.forEach(row => {
                row.style.display = isVisible ? 'none' : 'table-row';
            });

            if (isVisible) {
                icon.style.transform = 'rotate(0deg)';
                btn.classList.remove('active');
                window.expandedCategoryGroups.delete(groupClass);
            } else {
                icon.style.transform = 'rotate(180deg)';
                btn.classList.add('active');
                window.expandedCategoryGroups.add(groupClass);
            }
        }

        function toggleProductDetails(containerId, btn) {
            const container = document.getElementById(containerId);
            const isVisible = container.classList.contains('visible');
            
            // Close all other containers first (optional, but cleaner)
            // document.querySelectorAll('.product-details-container').forEach(c => c.classList.remove('visible'));
            // document.querySelectorAll('.btn-toggle-details').forEach(b => b.classList.remove('active'));

            if (isVisible) {
                container.classList.remove('visible');
                btn.classList.remove('active');
            } else {
                container.classList.add('visible');
                btn.classList.add('active');
            }
        }


        window.onerror = function(msg, url, line, col, error) {
            console.error('🔥 Dashboard Error:', msg, 'at', line, ':', col);
            return false;
        };

        // Initial Load
        (async function init() {
            try {


                await fetchAccounts();
                switchTab('benchmarking');
                
                // Refresh every 60 seconds
                setInterval(refreshData, 60000);
            } catch (err) {
                console.error('❌ Init failed:', err);
            }
        })();



        // Overview Product Selector Change Event
        const ovProdSelector = document.getElementById('overview-product-selector');
        if (ovProdSelector) {
            ovProdSelector.addEventListener('change', (e) => {
                const selectedAsin = e.target.value;
                const selectedRow = overviewSnapshots.find(r => r.asin === selectedAsin);
                if (selectedRow) {
                    const loader = document.getElementById('overview-chart-loading');
                    if (loader) {
                        loader.style.display = 'flex';
                        setTimeout(() => {
                            renderPricingHistogram(selectedRow);
                            updatePortfolioMarkers(selectedRow);
                        }, 150);
                    } else {
                        renderPricingHistogram(selectedRow);
                        updatePortfolioMarkers(selectedRow);
                    }
                }
            });
        }

        // Repricing Table Row Click Interactive Selection
        const recsBody = document.getElementById('recs-body');
        if (recsBody) {
            recsBody.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                if (!row) return;
                const clickedAsin = row.getAttribute('data-asin');
                if (!clickedAsin) return;

                // Highlight the clicked row
                document.querySelectorAll('#recs-body tr').forEach(tr => tr.classList.remove('selected-row'));
                row.classList.add('selected-row');

                // Find and map to the corresponding snapshot
                const selectedRow = overviewSnapshots.find(s => 
                    s.asin === clickedAsin || 
                    s.parent_asin === clickedAsin || 
                    (s.parent_asin && s.parent_asin === clickedAsin)
                );
                
                if (selectedRow) {
                    const selector = document.getElementById('overview-product-selector');
                    if (selector) {
                        selector.value = selectedRow.asin;
                        
                        // Smoothly trigger loader overlay and ApexCharts transition
                        const loader = document.getElementById('overview-chart-loading');
                        if (loader) {
                            loader.style.display = 'flex';
                            setTimeout(() => {
                                renderPricingHistogram(selectedRow);
                                updatePortfolioMarkers(selectedRow);
                            }, 150);
                        } else {
                            renderPricingHistogram(selectedRow);
                            updatePortfolioMarkers(selectedRow);
                        }
                    }
                }
            });
        }

        // Bind filters & sorting event listeners for Repricing Recommendations
        const recsSearchInput = document.getElementById('recs-search');
        if (recsSearchInput) {
            recsSearchInput.addEventListener('input', () => {
                renderRecommendations(globalRecommendations);
            });
        }

        const recsActionFilter = document.getElementById('recs-action-filter');
        if (recsActionFilter) {
            recsActionFilter.addEventListener('change', () => {
                renderRecommendations(globalRecommendations);
            });
        }

        const recsSortBy = document.getElementById('recs-sort-by');
        if (recsSortBy) {
            recsSortBy.addEventListener('change', () => {
                renderRecommendations(globalRecommendations);
            });
        }
    