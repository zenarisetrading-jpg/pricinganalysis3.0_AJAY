
        const API_BASE = '/api/v1/benchmarking';
        let currentClientId = 's2c-uae';
        let activeTab = 'benchmarking';
        let testCatalog = [];
        let simulationActive = false;
        let simulationResults = null;
        let overviewSnapshots = [];
        let globalRecommendations = [];
        let currentOverviewChartInstance = null;
        let currentBubbleChartInstance = null;
        let activeFilterParentAsin = null;
        let childProductsMap = {};
        let childToParentAsin = {};

        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, char => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[char]));
        }

        function findRecommendationForProduct(row) {
            const parentAsin = row?.parent_asin || row?.asin;
            const asin = row?.asin;
            const matches = globalRecommendations.filter(rec => {
                const recParentAsin = rec.parent_asin || rec.asin;
                return recParentAsin === parentAsin ||
                    recParentAsin === asin ||
                    rec.asin === asin ||
                    rec.asin === parentAsin;
            });
            return matches.find(rec => rec.title && rec.asin === rec.parent_asin) ||
                matches.find(rec => rec.title) ||
                matches.find(rec => rec.asin === rec.parent_asin) ||
                matches[0];
        }

        // Draft Persistence Utilities
        const DRAFT_KEY_PREFIX = 'saddl_drafts_';
        function getDraftsKey(clientId) { return `${DRAFT_KEY_PREFIX}${clientId || currentClientId}`; }
        function getDrafts(clientId) {
            try { const stored = localStorage.getItem(getDraftsKey(clientId)); return stored ? JSON.parse(stored) : {}; }
            catch (e) { console.error('Failed to read drafts:', e); return {}; }
        }
        function findOriginalProduct(asin) {
            if (!window.allCategories) return null;
            for (const cat of window.allCategories) {
                if (cat.products) {
                    const prod = cat.products.find(p => p.asin === asin);
                    if (prod) return prod;
                }
            }
            return null;
        }
        function saveDraft(clientId, asin, refName, excludeKws, excludeBrands) {
            try {
                const key = getDraftsKey(clientId);
                const drafts = getDrafts(clientId);
                const origProd = findOriginalProduct(asin);
                let isDifferent = false;
                if (origProd) {
                    const parts = (origProd.exclude_keywords || '').split('|brand_exclude:');
                    if ((refName || '') !== (origProd.reference_name || '') || (excludeKws || '') !== (parts[0] || '').trim() || (excludeBrands || '') !== (parts[1] || '').trim()) isDifferent = true;
                } else if (refName || excludeKws || excludeBrands) { isDifferent = true; }
                if (isDifferent) drafts[asin] = { reference_name: refName, exclude_keywords: excludeKws, exclude_brands: excludeBrands, updatedAt: Date.now() };
                else delete drafts[asin];
                localStorage.setItem(key, JSON.stringify(drafts));
            } catch (e) { console.error('Failed to save draft:', e); }
        }
        function clearDraft(clientId, asin) {
            try {
                const key = getDraftsKey(clientId);
                const drafts = getDrafts(clientId);
                delete drafts[asin];
                localStorage.setItem(key, JSON.stringify(drafts));
            } catch (e) { console.error('Failed to clear draft:', e); }
        }
        const draftSaveTimeouts = {};
        function handleCategoryInput(asin) {
            if (draftSaveTimeouts[asin]) clearTimeout(draftSaveTimeouts[asin]);
            draftSaveTimeouts[asin] = setTimeout(() => {
                const refName = (document.getElementById(`ref-name-${asin}`) || {}).value || '';
                const excludeKws = (document.getElementById(`exclude-keywords-${asin}`) || {}).value || '';
                const excludeBrands = (document.getElementById(`exclude-brands-${asin}`) || {}).value || '';
                saveDraft(currentClientId, asin, refName, excludeKws, excludeBrands);
            }, 500);
        }

        function getParentAsinTitle(row) {
            const matchedRec = findRecommendationForProduct(row);
            return matchedRec?.title || row?.title || row?.reference_name || 'Parent ASIN Group';
        }

        // Tab Switching Logic
        let tabDataLoaded = {
            benchmarking: false,
            categories: false
        };

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = item.getAttribute('data-tab');
                switchTab(tabName);
            });
        });

        function switchTab(tab, forceRefresh = false) {
            activeTab = tab;
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');

            // Hide all sections
            document.getElementById('view-benchmarking').style.display = 'none';
            document.getElementById('view-categories').style.display = 'none';

            // Show active section
            const targetEl = document.getElementById(`view-${tab}`);
            if (targetEl) targetEl.style.display = 'block';

            if (forceRefresh || !tabDataLoaded[tab]) {
                refreshData();
            }
        }

        // Account Selection Logic
        const accountSelector = document.getElementById('account-selector');
        accountSelector.addEventListener('change', (e) => {
            currentClientId = e.target.value;
            simulationActive = false;
            simulationResults = null;
            testCatalog = [];
            tabDataLoaded = { benchmarking: false, categories: false };
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

            const panel = document.getElementById('product-metrics-panel');
            if (panel) panel.style.display = 'none';
        }

        async function refreshData() {
            try {
                const headers = { 
                    'X-Client-Id': currentClientId,
                    'X-Internal-Token': 'saddl_secret_token_123'
                };
                
                const promises = [];

                if (activeTab === 'benchmarking') {
                      const fetchBenchmarking = async () => {
                          const selectedTier = document.getElementById('dashboard-tier-filter')?.value || 'All';
                          let recsResp, overviewResp, alertsResp;
                          
                          if (selectedTier === 'All') {
                              [recsResp, overviewResp, alertsResp] = await Promise.all([
                                  fetch(`${API_BASE}/recommendations?client_id=${currentClientId}`, { headers }).catch(e => { console.error('Failed to fetch recommendations:', e); return null; }),
                                  fetch(`${API_BASE}/overview?client_id=${currentClientId}`, { headers }),
                                  fetch(`${API_BASE}/alerts?client_id=${currentClientId}`, { headers }).catch(e => { console.error('Failed to fetch alerts:', e); return null; })
                              ]);
                              
                              if (recsResp && recsResp.ok) {
                                  const recsData = await recsResp.json();
                                  globalRecommendations = recsData.recommendations || [];
                              }

                              if (!overviewResp.ok) throw new Error(`HTTP ${overviewResp.status}`);
                              const overviewData = await overviewResp.json();

                              renderOverview(overviewData.rows, overviewData);
                              renderRecommendations(globalRecommendations);
                          } else {
                              // Use the recalculate endpoint when a specific tier is filtered
                              const recalcResp = await fetch(`${API_BASE}/recalculate-dashboard?client_id=${currentClientId}&tier=${encodeURIComponent(selectedTier)}`, { method: 'POST', headers });
                              if (!recalcResp.ok) throw new Error(`HTTP ${recalcResp.status}`);
                              const recalcData = await recalcResp.json();
                              
                              globalRecommendations = recalcData.recommendations || [];
                              // Pass parent_asin_count so renderOverview can update the global cache.
                              // This is the TOTAL universe count (not the tier-filtered count) so the
                              // "Tracked Parent ASINs" KPI stays consistent across tier selections.
                              renderOverview(recalcData.snapshots, {
                                  rows: recalcData.snapshots,
                                  parent_asin_count: recalcData.parent_asin_count,
                              });
                              renderRecommendations(globalRecommendations);
                              
                              // Still fetch alerts normally
                              alertsResp = await fetch(`${API_BASE}/alerts?client_id=${currentClientId}`, { headers }).catch(e => null);
                          }

                          if (alertsResp && alertsResp.ok) {
                              const alertsData = await alertsResp.json();
                              renderAlerts(alertsData.alerts);
                          }
                    };
                    promises.push(fetchBenchmarking());
                }

                if (activeTab === 'categories') {
                    const fetchCategories = async () => {
                        const catsResp = await fetch(`${API_BASE}/account-bsr-categories?account_id=${currentClientId}`, { headers });
                        if (catsResp.ok) {
                            const catsData = await catsResp.json();
                            window.allCategories = catsData.categories; // Store for searching
                            renderCategories(catsData.categories);
                        }
                    };
                    promises.push(fetchCategories());
                }

                await Promise.all(promises);
                tabDataLoaded[activeTab] = true;

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
            const rawMin = parseFloat(row.floor_price);
            const p25 = parseFloat(row.p25_price);
            const median = parseFloat(row.median_price);
            const p75 = parseFloat(row.p75_price);
            const rawMax = parseFloat(row.ceiling_price);
            const count = parseInt(row.n_competitors) || 0;

            if (isNaN(rawMin) || isNaN(rawMax) || count === 0) return null;

            // Handle edge case: zero price spread
            if (rawMax <= rawMin) {
                return {
                    bins: [{
                        label: `${rawMin.toFixed(1)}`,
                        mid: rawMin,
                        start: rawMin,
                        end: rawMin,
                        count: count,
                        competitors: rawCompetitors,
                        brands: [],
                        actualAvg: rawMin,
                        actualMedian: rawMin
                    }],
                    min: rawMin, max: rawMax, p25, median, p75
                };
            }

            // Find matching recommendation to get Our Price and Median Price
            let targetRec = globalRecommendations.find(r => (r.parent_asin || r.asin) === (row.parent_asin || row.asin));
            targetRec = targetRec || row;

            let ourSellingPrice = parseFloat(targetRec.current_price);
            if (isNaN(ourSellingPrice) || ourSellingPrice <= 0) {
                ourSellingPrice = parseFloat(targetRec.your_price);
            }
            if (isNaN(ourSellingPrice) || ourSellingPrice <= 0) {
                ourSellingPrice = parseFloat(row.current_price) || parseFloat(row.your_price) || 0;
            }

            const marketIndex = window.currentAvgMarketIndex || 100;
            const meta = targetRec.metadata || targetRec;
            let rawMedianVal = parseFloat(meta?.median_price) || parseFloat(targetRec?.median_price) || parseFloat(targetRec?.recommended_price) || parseFloat(row?.median_price) || 0;
            const targetPriceVal = rawMedianVal;

            // Expand bounds to cover competitor range, our selling price, and Median Price
            let finalMin = rawMin;
            let finalMax = rawMax;
            if (ourSellingPrice > 0) {
                finalMin = Math.min(finalMin, ourSellingPrice);
                finalMax = Math.max(finalMax, ourSellingPrice);
            }
            if (targetPriceVal > 0) {
                finalMin = Math.min(finalMin, targetPriceVal);
                finalMax = Math.max(finalMax, targetPriceVal);
            }

            // Buffer padding to ensure lines are not right on the edge of the graph
            const spread = finalMax - finalMin;
            const minBound = Math.max(0, finalMin - (spread * 0.08));
            const maxBound = finalMax + (spread * 0.08);

            // 1. Resolve Competitor Prices (Real or Quartile-based)
            let prices = [];
            let competitorSource = [];

            if (count <= 5) {
                if (rawCompetitors && rawCompetitors.length > 0) {
                    rawCompetitors.forEach(c => {
                        const p = parseFloat(c.price);
                        if (!isNaN(p) && p > 0) {
                            prices.push(p);
                            competitorSource.push(c);
                        }
                    });
                }
                
                if (prices.length < count) {
                    const missingCount = count - prices.length;
                    const quartiles = [];
                    if (count === 1) {
                        quartiles.push(median);
                    } else if (count === 2) {
                        quartiles.push(rawMin, rawMax);
                    } else if (count === 3) {
                        quartiles.push(rawMin, median, rawMax);
                    } else if (count === 4) {
                        quartiles.push(rawMin, p25, p75, rawMax);
                    } else {
                        quartiles.push(rawMin, p25, median, p75, rawMax);
                    }
                    
                    for (let i = 0; i < missingCount; i++) {
                        const priceVal = quartiles[i % quartiles.length] || median;
                        prices.push(priceVal);
                        competitorSource.push({
                            price: priceVal,
                            brand: 'Competitor'
                        });
                    }
                }
            } else {
                // High competitors (count > 5): Synthetic Population Interpolation
                for (let i = 0; i <= sampleSize; i++) {
                    const q = i / sampleSize;
                    let p = 0;
                    if (q <= 0.25) {
                        p = rawMin + (q / 0.25) * (p25 - rawMin);
                    } else if (q <= 0.50) {
                        p = p25 + ((q - 0.25) / 0.25) * (median - p25);
                    } else if (q <= 0.75) {
                        p = median + ((q - 0.50) / 0.25) * (p75 - median);
                    } else {
                        p = p75 + ((q - 0.75) / 0.25) * (rawMax - p75);
                    }
                    
                    const jitter = (Math.random() - 0.5) * 0.015 * (rawMax - rawMin);
                    prices.push(Math.max(rawMin, Math.min(rawMax, p + jitter)));
                }

                // Resolve competitor source for high competitor count
                competitorSource = rawCompetitors || [];
                if (competitorSource.length === 0) {
                    const step = prices.length / count;
                    competitorSource = [];
                    for (let i = 0; i < count; i++) {
                        const priceIndex = Math.min(prices.length - 1, Math.floor(i * step));
                        competitorSource.push({
                            price: prices[priceIndex],
                            brand: 'Competitor'
                        });
                    }
                }
            }

            // 2. Frequency Binning across the expanded bounds
            const binWidth = (maxBound - minBound) / binCount;
            if (binWidth <= 0) return null;
            const bins = [];
            for (let i = 0; i < binCount; i++) {
                const binStart = minBound + i * binWidth;
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

            // Map actual or simulated competitors into the bins based on their price securely
            competitorSource.forEach(comp => {
                const p = parseFloat(comp.price);
                if (isNaN(p)) return;
                
                // Clamp to prevent dropping items due to database floor_price rounding
                const clampedP = Math.max(minBound, Math.min(maxBound, p));
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

            // Normalize densities to sum up to N (competitor count) if count > 5
            if (count > 5) {
                const scale = count / prices.length;
                bins.forEach(b => {
                    b.count = parseFloat((b.count * scale).toFixed(1));
                });
            }

            return { bins, min: rawMin, max: rawMax, p25, median, p75 };
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
            const rawMedian = parseFloat(row.median_price) || 0;
            const marketIndex = window.currentAvgMarketIndex || 100;
            const targetPriceVal = rawMedian;

            // Update Product-specific Metrics Panel & Break-even calculations
            if (panel) {
                // Store active product row globally for dynamic updates on COGS change
                window.activeProductRow = row;
                updateTierFilterBanner(row.asin);

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
                    if (document.activeElement !== cogsInput) {
                        cogsInput.value = savedCogs !== null ? savedCogs : '';
                    }
                    
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
            
            let yourPrice = parseFloat(row.your_price);
            if (isNaN(yourPrice)) yourPrice = parseFloat(row.current_price);
            if (matchedRec && (isNaN(yourPrice) || yourPrice <= 0)) {
                yourPrice = parseFloat(matchedRec.calculatedCurrentPrice) || parseFloat(matchedRec.current_price) || parseFloat(matchedRec.your_price) || 0;
            }
            if (isNaN(yourPrice)) yourPrice = 0;

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
                    toolbar: { 
                        show: true,
                        autoSelected: 'zoom',
                        tools: { download: false, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true }
                    },
                    zoom: { enabled: true },
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
                    xaxis: []
                }
            };

            // 1. Median Line Annotation
            if (targetPriceVal > 0) {
                options.annotations.xaxis.push({
                    x: targetPriceVal,
                    borderColor: 'var(--warning)',
                    strokeDashArray: 0,
                    label: {
                        borderColor: 'var(--warning)',
                        style: { color: '#fff', background: 'var(--warning)', fontSize: '11px', fontWeight: 600, padding: { left: 8, right: 8, top: 4, bottom: 4 } },
                        text: `Median: ${currency} ${Number.isFinite(targetPriceVal) ? targetPriceVal.toFixed(2) : '0.00'}`
                    }
                });
            }

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

        // ── Canonical Tier Colour Palette (used in bubble chart) ─────────────
        const TIER_COLORS = {
            'Entry': '#60a5fa',
            'Mass': '#34d399',
            'Mid-Premium': '#fb923c',
            'Premium': '#a78bfa',
        };
        const TIER_ORDER = ['Entry', 'Mass', 'Mid-Premium', 'Premium'];
        const TIER_DEFAULT = '#94a3b8';

        function renderRatingVsPriceBubbleChart(row) {
            const container = document.getElementById('overview-bubble-chart');
            const emptyState = document.getElementById('overview-bubble-empty');
            const loader = document.getElementById('overview-bubble-loading');

            if (loader) loader.style.display = 'none';

            if (!row || !row.asin) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            // ── Step 1: Get raw competitor list from globalRecommendations ────────────
            // The matchedRec.metadata.competitors contains the FULL competitor list for
            // this parent ASIN (already tier-filtered by backend when a tier is active).
            const matchedRec = globalRecommendations.find(rec => {
                const recKey = rec.parent_asin || rec.asin;
                const rowKey = row.parent_asin || row.asin;
                return recKey === rowKey || rec.asin === row.asin || rec.parent_asin === row.parent_asin;
            });

            const rawCompetitors = (matchedRec && matchedRec.metadata && matchedRec.metadata.competitors) 
                ? matchedRec.metadata.competitors 
                : [];

            // ── Step 2: Read user-defined include/exclude filters ──────────────────────
            const parentAsin = row.parent_asin || row.asin;
            const domInclude    = document.getElementById(`ref-name-${parentAsin}`);
            const domExcludeKws = document.getElementById(`exclude-keywords-${parentAsin}`);
            const domExcludeBrands = document.getElementById(`exclude-brands-${parentAsin}`);
            
            let referenceName = domInclude ? domInclude.value : (row.reference_name || '');
            let excludeKeywordsStr = '';
            if (domExcludeKws || domExcludeBrands) {
                const kwsVal    = domExcludeKws    ? domExcludeKws.value.trim()    : '';
                const brandsVal = domExcludeBrands ? domExcludeBrands.value.trim() : '';
                excludeKeywordsStr = kwsVal;
                if (brandsVal) excludeKeywordsStr = `${kwsVal}|brand_exclude: ${brandsVal}`;
            } else {
                excludeKeywordsStr = row.exclude_keywords || (matchedRec && matchedRec.exclude_keywords) || '';
            }

            let excludeKeywords = [];
            let excludeBrands   = [];
            if (excludeKeywordsStr && excludeKeywordsStr.trim()) {
                const parts      = excludeKeywordsStr.split('|brand_exclude:');
                const kwsPart    = parts[0] || '';
                const brandsPart = parts[1] || '';
                excludeKeywords = kwsPart.split(',').map(kw => kw.trim().toLowerCase()).filter(Boolean);
                excludeBrands   = brandsPart.split(',').map(b => b.trim().toLowerCase()).filter(Boolean);
            }

            if (rawCompetitors.length === 0) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            if (container) container.style.display = 'block';
            if (emptyState) emptyState.style.display = 'none';

            const ourPrice     = parseFloat(row.your_price) || 0;
            let ourRatingRaw   = parseFloat(row.rating) || 0;
            let ourRatingEstimated = false;
            if (!ourRatingRaw || ourRatingRaw <= 0) { ourRatingRaw = 4.5; ourRatingEstimated = true; }
            const ourRating  = ourRatingRaw;
            const ourReviews = parseInt(row.reviews) || 0;

            // ── Step 3: Clean + filter individual competitor records ───────────────────
            // FIX: reference-name filter runs HERE (pre-aggregation) so brand grouping is
            // correct. Previously it ran post-aggregation at the brand level, silently
            // dropping brands whose sample title didn't match even though other products
            // of that brand did match.
            const cleanCompetitors = rawCompetitors.map(c => {
                let p  = parseFloat(c.floor_price) || parseFloat(c.price) || parseFloat(c.competitor_price) || 0;
                let r  = parseFloat(c.rating) || 0;
                let isEstimatedRating = false;
                if (!r || r <= 0) { r = 4.0; isEstimatedRating = true; }
                let rev = parseInt(c.reviews) || 0;
                return {
                    asin:  c.asin,
                    title: c.title || c.asin || 'Competitor Offer',
                    brand: (c.brand && c.brand !== 'null' && c.brand !== 'None') ? c.brand : '',
                    price: p,
                    rating: r,
                    reviews: rev,
                    isEstimatedRating,
                    // carry through tier tag from backend (already assigned correctly)
                    tier: c.tier || null,
                };
            }).filter(c => {
                if (c.price <= 0) return false;
                
                const titleLower = c.title.toLowerCase();
                const brandLower = c.brand.toLowerCase();

                // A. Exclude title keywords
                if (excludeKeywords.some(kw => titleLower.includes(kw))) return false;

                // B. Exclude brands
                if (excludeBrands.length > 0) {
                    const compBrandClean = brandLower.replace(/\s+/g, ' ').trim();
                    let matchesExcludedBrand = false;
                    for (const brand of excludeBrands) {
                        const brandClean = brand.replace(/\s+/g, ' ').trim();
                        if (!brandClean) continue;
                        if (compBrandClean === brandClean) { matchesExcludedBrand = true; break; }
                        const escaped = brandClean.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                        if (new RegExp('\\b' + escaped + '\\b').test(compBrandClean)) { matchesExcludedBrand = true; break; }
                    }
                    if (matchesExcludedBrand) return false;
                }

                // C. Include keywords (reference name) — evaluated per individual product
                if (referenceName && referenceName.trim()) {
                    const refLower = referenceName.trim().toLowerCase();
                    const phrases  = refLower.split(',').map(p => p.trim()).filter(Boolean);
                    if (phrases.length > 0) {
                        const matchesAnyPhrase = phrases.some(phrase => {
                            const kws = phrase.split(/\s+/).map(kw => kw.trim()).filter(Boolean);
                            return kws.length > 0 && kws.every(kw => titleLower.includes(kw));
                        });
                        if (!matchesAnyPhrase) return false;
                    }
                }
                
                return true;
            });

            if (cleanCompetitors.length === 0) {
                if (container) container.style.display = 'none';
                if (emptyState) emptyState.style.display = 'flex';
                return;
            }

            // ── Step 4: Compute CCS normalization bounds from full cleaned set ─────────
            const allReviews = [...cleanCompetitors.map(c => c.reviews), ourReviews];
            const maxReviews = Math.max(...allReviews, 1);
            const minReviews = Math.min(...allReviews, 0);

            const allRatings = [...cleanCompetitors.map(c => c.rating), ourRating];
            const maxRating  = Math.max(...allRatings, 5);
            const minRating  = Math.min(...allRatings, 1);

            function normalizeMetric(val, min, max) {
                if (max === min) return 1;
                return (val - min) / (max - min);
            }
            function calcCCS(rating, reviews) {
                return (0.4615 * normalizeMetric(rating, minRating, maxRating))
                     + (0.5385 * normalizeMetric(reviews, minReviews, maxReviews));
            }

            // ── Step 5: Aggregate individual products into per-brand summary points ─────
            const brandGroups = {};
            cleanCompetitors.forEach(c => {
                const brandKey = c.brand ? c.brand.trim().toUpperCase() : 'UNKNOWN BRAND';
                if (!brandGroups[brandKey]) {
                    brandGroups[brandKey] = {
                        brand: c.brand ? c.brand.trim() : 'Unknown Brand',
                        prices: [], ratings: [], reviewsArr: [], ccsArr: [], asins: [], titles: [],
                        // Carry backend-assigned tier if present (used for summary panel only)
                        backendTier: c.tier || null,
                    };
                }
                brandGroups[brandKey].prices.push(c.price);
                brandGroups[brandKey].ratings.push(c.rating);
                brandGroups[brandKey].reviewsArr.push(c.reviews);
                brandGroups[brandKey].ccsArr.push(calcCCS(c.rating, c.reviews));
                brandGroups[brandKey].asins.push(c.asin);
                brandGroups[brandKey].titles.push(c.title);
            });

            const brandMetrics = Object.values(brandGroups).map(g => {
                const sortedPrices = [...g.prices].sort((a, b) => a - b);
                const sortedCcs    = [...g.ccsArr].sort((a, b) => a - b);
                return {
                    brand:        g.brand,
                    medianPrice:  sortedPrices[Math.floor(sortedPrices.length / 2)],
                    medianCcs:    sortedCcs[Math.floor(sortedCcs.length / 2)],
                    avgRating:    g.ratings.reduce((a, b) => a + b, 0) / g.ratings.length,
                    totalReviews: g.reviewsArr.reduce((a, b) => a + b, 0),
                    nListings:    g.prices.length,
                    sampleTitle:  g.titles[0],
                    asins:        g.asins,
                    backendTier:  g.backendTier,
                };
            });

            // ── Step 6: Compute tier boundaries from the COMPLETE brand set ────────────
            // FIX: Tier boundaries MUST be computed from ALL brands visible in the current
            // dataset (post-filter). The internal tier assignment is used ONLY for the
            // tier-summary panel and color coding. It is NOT used for filtering — the
            // backend already handles tier filtering before this function is called.
            const sortedBrandPrices = brandMetrics.map(b => b.medianPrice).sort((a, b) => a - b);
            function quartile(arr, pct) {
                if (arr.length === 0) return 0;
                return arr[Math.max(0, Math.floor(pct * (arr.length - 1)))];
            }
            const q1Price = quartile(sortedBrandPrices, 0.25);
            const q2Price = quartile(sortedBrandPrices, 0.50);
            const q3Price = quartile(sortedBrandPrices, 0.75);
            function assignTierLocal(price) {
                if (price <= q1Price) return 'Entry';
                if (price <= q2Price) return 'Mass';
                if (price <= q3Price) return 'Mid-Premium';
                return 'Premium';
            }

            // ── Step 7: Build final formatted points — one per brand ──────────────────
            const ourCcs = calcCCS(ourRating, ourReviews);
            const formattedOurProduct = [{
                x: ourCcs, y: ourPrice, z: 8,
                title: row.title || row.reference_name || 'Our Product Group',
                brand: 'S2C', asin: row.asin,
                totalReviews: ourReviews, avgRating: ourRating, nListings: 1,
                isEstimatedRating: ourRatingEstimated,
                tier: assignTierLocal(ourPrice), tierColor: '#10b981',
            }];

            // ALL brands that survived steps 3–5 are plotted. No second filter.
            const formattedCompetitors = brandMetrics.map(b => {
                const tier = b.backendTier || assignTierLocal(b.medianPrice);
                return {
                    x: b.medianCcs, y: b.medianPrice, z: 8,
                    title: b.nListings > 1 ? `${b.sampleTitle} (+${b.nListings - 1} more)` : b.sampleTitle,
                    brand: b.brand,
                    totalReviews: b.totalReviews, avgRating: b.avgRating, nListings: b.nListings,
                    isEstimatedRating: false,
                    tier, tierColor: TIER_COLORS[tier] || TIER_DEFAULT,
                    asins: b.asins,
                };
            });

            console.log(`[VALIDATION] Bubble chart: ${cleanCompetitors.length} competitor products → ${brandMetrics.length} unique brands plotted`);

            // Compute reference lines (median CCS + median price across all visible brands)
            const allPriceVals = [...formattedCompetitors.map(pt => pt.y), formattedOurProduct[0].y].sort((a, b) => a - b);
            const marketMedianPrice = allPriceVals.length > 0 ? allPriceVals[Math.floor(allPriceVals.length / 2)] : ourPrice;
            const allCcsVals = [...formattedCompetitors.map(pt => pt.x), formattedOurProduct[0].x].sort((a, b) => a - b);
            const marketMedianCcs = allCcsVals.length > 0 ? allCcsVals[Math.floor(allCcsVals.length / 2)] : 0.5;

            const currency = 'AED';

            // ── Step 8: Render (no internal tier filter — backend already did it) ──────
            // FIX: renderChart no longer applies a second tier filter. It displays EVERY
            // brand that was passed in. The dashboard tier dropdown controls what the
            // backend sends; this function only displays what it receives.
            function renderChart() {
                const tierSeriesData = [];
                if (formattedCompetitors.length > 0) {
                    tierSeriesData.push({
                        name: 'Competitors',
                        color: '#6366f1',
                        points: formattedCompetitors,
                    });
                }

                const allSeries = [
                    ...tierSeriesData.map(s => ({
                        name: s.name,
                        data: s.points.map(pt => [pt.x, pt.y, pt.z]),
                    })),
                ];
                if (formattedOurProduct.length > 0) {
                    allSeries.push({
                        name: '★ Our Product (S2C)',
                        data: formattedOurProduct.map(pt => [pt.x, pt.y, pt.z]),
                    });
                }

                const seriesColors = tierSeriesData.map(s => s.color);
                if (formattedOurProduct.length > 0) seriesColors.push('#10b981');

                // allFormattedPoints keeps index-aligned series order for tooltip lookups
                const allFormattedPoints = [
                    ...tierSeriesData.map(s => s.points),
                ];
                if (formattedOurProduct.length > 0) allFormattedPoints.push(formattedOurProduct);

                // FIX: X-axis auto-scales to the actual CCS range instead of hardcoded 0–1.
                // Hardcoded boundaries were clipping brands whose CCS landed at exactly 0 or 1.
                const ccsValues = allSeries.flatMap(s => s.data.map(d => d[0]));
                const ccsMin = Math.max(0, Math.min(...ccsValues) - 0.05);
                const ccsMax = Math.min(1, Math.max(...ccsValues) + 0.05);

                const options = {
                    series: allSeries,
                    chart: {
                        height: 420,
                        type: 'bubble',
                        background: 'transparent',
                        foreColor: '#949eb5',
                        toolbar: {
                            show: true,
                            autoSelected: 'zoom',
                            tools: { download: false, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true },
                        },
                        zoom: { enabled: true, type: 'xy' },
                    },
                    dataLabels: { enabled: false },
                    fill: {
                        opacity: [...Array(tierSeriesData.length).fill(0.65), (formattedOurProduct.length > 0 ? 0.95 : undefined)].filter(x => x !== undefined),
                    },
                    colors: seriesColors,
                    xaxis: {
                        // FIX: dynamic bounds instead of hardcoded 0–1
                        min: ccsMin,
                        max: ccsMax,
                        tickAmount: 5,
                        labels: {
                            formatter: (val) => parseFloat(val).toFixed(2),
                            style: { colors: '#949eb5', fontSize: '11px', fontFamily: 'Inter' },
                        },
                        title: {
                            text: 'Median Customer Competitiveness Score (CCS)',
                            style: { color: '#949eb5', fontWeight: 500, fontSize: '11px', fontFamily: 'Inter' },
                        },
                        axisBorder: { show: false },
                        axisTicks:  { show: false },
                    },
                    yaxis: {
                        tickAmount: 8,
                        labels: {
                            formatter: (val) => `${currency} ${parseFloat(val).toFixed(0)}`,
                            style: { colors: '#949eb5' },
                        },
                        title: {
                            text: 'Median Selling Price (AED)',
                            style: { color: '#949eb5', fontWeight: 500, fontSize: '11px', fontFamily: 'Inter' },
                        },
                    },
                    grid: { borderColor: 'rgba(255, 255, 255, 0.05)', strokeDashArray: 4 },
                    legend: {
                        show: true, position: 'top', horizontalAlign: 'right',
                        fontFamily: 'Inter', fontSize: '12px',
                        labels: { colors: '#f0f2f5' },
                        markers: { radius: 12 },
                    },
                    annotations: {
                        xaxis: [{
                            x: marketMedianCcs,
                            borderColor: 'rgba(255, 255, 255, 0.25)',
                            strokeDashArray: 4,
                            label: {
                                style: { color: '#fff', background: 'rgba(245, 158, 11, 0.4)', fontSize: '9px', fontWeight: 600 },
                                text: `Market Median CCS: ${marketMedianCcs.toFixed(2)}`,
                            },
                        }],
                        yaxis: [
                            {
                                y: marketMedianPrice,
                                borderColor: 'rgba(255, 255, 255, 0.25)',
                                strokeDashArray: 4,
                                label: {
                                    style: { color: '#fff', background: 'rgba(91, 138, 240, 0.4)', fontSize: '9px', fontWeight: 600 },
                                    text: `Median Price: ${currency} ${marketMedianPrice.toFixed(0)}`,
                                },
                            },
                            {
                                y: q1Price,
                                borderColor: 'rgba(96, 165, 250, 0.3)',
                                strokeDashArray: 6,
                                label: {
                                    style: { color: '#60a5fa', background: 'rgba(96, 165, 250, 0.12)', fontSize: '8px', fontWeight: 500 },
                                    text: `Budget→Value: ${currency} ${q1Price.toFixed(0)}`,
                                },
                            },
                            {
                                y: q3Price,
                                borderColor: 'rgba(167, 139, 250, 0.3)',
                                strokeDashArray: 6,
                                label: {
                                    style: { color: '#a78bfa', background: 'rgba(167, 139, 250, 0.12)', fontSize: '8px', fontWeight: 500 },
                                    text: `Mid-Mkt→Prem: ${currency} ${q3Price.toFixed(0)}`,
                                },
                            },
                        ],
                    },
                    tooltip: {
                        shared: false,
                        intersect: true,
                        custom: function ({ seriesIndex, dataPointIndex }) {
                            const seriesPoints = allFormattedPoints[seriesIndex];
                            const pt = seriesPoints ? seriesPoints[dataPointIndex] : null;
                            if (!pt) return '';

                            const isOurs = (formattedOurProduct.length > 0 && seriesIndex === allSeries.length - 1);
                            const tierColor = isOurs ? '#10b981' : (pt.tierColor || '#6366f1');

                            let segment = '', segmentColor = '';
                            if (pt.x >= marketMedianCcs) {
                                segment = pt.y <= marketMedianPrice ? 'Value Leader Zone' : 'Premium Segment';
                                segmentColor = pt.y <= marketMedianPrice ? 'var(--success)' : 'var(--accent)';
                            } else {
                                segment = pt.y <= marketMedianPrice ? 'Budget Zone' : 'Overpriced / Vulnerable';
                                segmentColor = pt.y <= marketMedianPrice ? 'var(--warning)' : 'var(--danger)';
                            }

                            const brandLabel = pt.brand
                                ? pt.brand.trim().replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase())
                                : 'Unknown Brand';
                            const truncatedTitle = pt.title && pt.title.length > 60 ? pt.title.substring(0, 60) + '...' : (pt.title || '');

                            // Build ASIN list for tooltip (up to 3)
                            const asinList = (pt.asins || []).slice(0, 3);
                            const asinHtml = asinList.length > 0
                                ? `<div style="display:flex;justify-content:space-between;"><span>ASINs:</span><span style="color:white;font-family:monospace;font-size:10px;">${asinList.join(', ')}${pt.asins && pt.asins.length > 3 ? ' …' : ''}</span></div>`
                                : '';

                            return `
                                <div class="custom-tooltip" style="
                                    background: rgba(22, 25, 35, 0.95);
                                    backdrop-filter: blur(12px) saturate(180%);
                                    border: 1.5px solid ${isOurs ? 'var(--success)' : tierColor};
                                    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                                    border-radius: 8px;
                                    padding: 14px;
                                    min-width: 260px;
                                    color: var(--text);
                                    font-family: var(--font-main);
                                    line-height: 1.4;
                                ">
                                    <div style="font-size: 11px; font-weight: 700; color: ${isOurs ? 'var(--success)' : tierColor}; margin-bottom: 6px; letter-spacing: 0.5px; text-transform: uppercase;">
                                        ${isOurs ? '★ Our Product (S2C)' : brandLabel}
                                    </div>
                                    <div style="font-size: 12px; font-weight: 600; color: white; margin-bottom: 10px; line-height: 1.4;">
                                        ${truncatedTitle}
                                    </div>
                                    <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;margin-bottom:8px;color:var(--text-dim);">
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Median Price:</span> <b style="color:white;font-family:monospace;">AED ${pt.y.toFixed(2)}</b>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Median CCS:</span> <b style="color:white;">${pt.x.toFixed(3)}</b>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Avg Rating:</span> <b style="color:white;">${pt.avgRating.toFixed(1)} ★</b>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Total Reviews:</span> <b style="color:white;">${pt.totalReviews.toLocaleString()}</b>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Listings:</span> <b style="color:white;">${pt.nListings}</b>
                                        </div>
                                        ${asinHtml}
                                        ${!isOurs ? `
                                        <div style="display:flex;justify-content:space-between;">
                                            <span>Tier:</span> <b style="color:${tierColor};">${pt.tier}</b>
                                        </div>` : ''}
                                    </div>
                                    <div style="font-size:10px;font-weight:700;color:${segmentColor};text-transform:uppercase;letter-spacing:0.5px;border-top:1px solid rgba(255,255,255,0.05);padding-top:6px;">
                                        ${segment}
                                    </div>
                                </div>
                            `;
                        },
                    },
                };

                if (currentBubbleChartInstance) {
                    currentBubbleChartInstance.destroy();
                }
                currentBubbleChartInstance = new ApexCharts(document.getElementById('overview-bubble-chart'), options);
                currentBubbleChartInstance.render().then(() => {
                    // ── Tier Breakdown Summary Panel ────────────────────────────────────────
                    const tierPanel = document.getElementById('bubble-tier-summary');
                    const tierStats = document.getElementById('bubble-tier-stats');
                    if (tierPanel && tierStats) {
                        const tierCounts = {};
                        const tierPrices = {};
                        TIER_ORDER.forEach(t => { tierCounts[t] = 0; tierPrices[t] = []; });

                        // Summary always uses the complete formattedCompetitors (all brands shown)
                        formattedCompetitors.forEach(pt => {
                            tierCounts[pt.tier] = (tierCounts[pt.tier] || 0) + 1;
                            (tierPrices[pt.tier] = tierPrices[pt.tier] || []).push(pt.y);
                        });

                        tierStats.innerHTML = TIER_ORDER.map(t => {
                            const count  = tierCounts[t] || 0;
                            const prices = tierPrices[t] || [];
                            const avg    = prices.length ? (prices.reduce((a, b) => a + b, 0) / prices.length) : null;
                            const color  = TIER_COLORS[t] || TIER_DEFAULT;
                            return `
                                <div style="flex:1;min-width:110px;padding:8px 10px;border-radius:8px;
                                    border-left:3px solid ${color};
                                    background:rgba(255,255,255,0.02);">
                                    <div style="font-weight:700;color:var(--text);margin-bottom:3px;font-size:11px;">${t}</div>
                                    <div style="color:var(--text);font-size:11px;">${count} brand${count !== 1 ? 's' : ''}</div>
                                    ${avg !== null ? `<div style="color:var(--text-dim);font-size:10px;">Med: AED ${avg.toFixed(0)}</div>` : ''}
                                </div>`;
                        }).join('');

                        tierPanel.style.display = 'block';
                    }
                });
            }

            // Use the GLOBAL dashboard tier filter (top-right header dropdown)
            const tierSelect = document.getElementById('dashboard-tier-filter');
            let currentFilter = 'All';
            if (tierSelect && tierSelect.value) {
                currentFilter = tierSelect.value;
            }

            // Initial render with current global filter
            renderChart(currentFilter);
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

            // ── Avg. Market Index ──────────────────────────────────────────
            // VALIDATION: Value-weighted ratio: Sum(Our Prices) / Sum(Median Prices) * 100
            // This avoids double-averaging and correctly weights the index by product value.
            // Only rows where BOTH your_price > 0 AND median_price > 0 are included.
            let sumYourPrice = 0;
            let sumMedianPrice = 0;
            uniqueRows.forEach(r => {
                const yp = parseFloat(r.your_price);
                let mp = parseFloat(r.median_price);
                // Fallback: derive median from index_vs_median if available
                if ((isNaN(mp) || mp <= 0) && !isNaN(parseFloat(r.index_vs_median)) && parseFloat(r.index_vs_median) > 0 && yp > 0) {
                    mp = (yp / parseFloat(r.index_vs_median)) * 100;
                }
                if (yp > 0 && mp > 0) {
                    sumYourPrice += yp;
                    sumMedianPrice += mp;
                }
            });
            const avgIndex = sumMedianPrice > 0 ? (sumYourPrice / sumMedianPrice) * 100 : 100;
            window.currentAvgMarketIndex = avgIndex;
            console.log(`[VALIDATION] Avg. Market Index: Sum(YourPrice)=${sumYourPrice.toFixed(2)} / Sum(MedianPrice)=${sumMedianPrice.toFixed(2)} = ${avgIndex.toFixed(2)}`);
            const indexElem = document.getElementById('kpi-index');
            if (indexElem) indexElem.textContent = avgIndex.toFixed(1);

            // ── Parent ASIN Count (Tier-Stable) ───────────────────────────
            // The ONLY authoritative source for the universe count is the /overview
            // endpoint (which counts from BSR categories). The /recalculate-dashboard
            // endpoint uses pb_recommendations as its source — a different table that
            // may have a different count. To keep the KPI consistent across all tier
            // changes, we ONLY update the global cache when "All Tiers" is selected.
            const activeTierFilter = document.getElementById('dashboard-tier-filter')?.value || 'All';
            const parentCount = Number(overviewData.parent_asin_count);
            if (activeTierFilter === 'All' && Number.isFinite(parentCount) && parentCount > 0) {
                // This is the /overview response — it has the real BSR-based universe count.
                window.globalParentAsinCount = parentCount;
                console.log(`[VALIDATION] Parent ASIN universe count set from /overview: ${parentCount}`);
            }
            // Always display the cached universe count so tier switching never changes it.
            // Falls back to uniqueRows.length only if the cache hasn't been populated yet.
            const skusCount = window.globalParentAsinCount || uniqueRows.length;
            const skusElem = document.getElementById('kpi-skus');
            if (skusElem) skusElem.textContent = skusCount;
            console.log(`[VALIDATION] Parent ASIN Count: displayed=${skusCount} | activeTier='${activeTierFilter}' | tierRows=${uniqueRows.length}`);

            // ── Health Score ───────────────────────────────────────────────
            // VALIDATION: Only rows with active competitor data participate in the denominator.
            // Products with zone='no_competitors' have no market context and must NOT
            // drag down the score by inflating the denominator.
            const healthyZones = ['budget', 'value', 'mid_market', 'premium'];
            const rowsWithCompetitors = uniqueRows.filter(r => r.zone && r.zone !== 'no_competitors');
            const healthyCount = rowsWithCompetitors.filter(r => healthyZones.includes(r.zone)).length;
            const healthDenominator = rowsWithCompetitors.length || 1;
            const healthScore = Math.round((healthyCount / healthDenominator) * 100);
            console.log(`[VALIDATION] Health Score: healthy=${healthyCount} / withCompetitors=${healthDenominator} = ${healthScore}%`);
            const healthElem = document.getElementById('kpi-health');
            if (healthElem) {
                healthElem.textContent = healthScore + '%';
                healthElem.style.color = healthScore > 80 ? 'var(--success)' : (healthScore > 50 ? 'var(--warning)' : 'var(--danger)');
            }

            const portfolioMarker = document.getElementById('portfolio-marker');
            if (portfolioMarker) {
                // Feature removed per user request
            }

            // Populate Overview Product Selector — child ASINs only (SKU + variation title)
            childProductsMap = overviewData.child_products || {};
            childToParentAsin = {};
            Object.entries(childProductsMap).forEach(([par, children]) => {
                children.forEach(ch => { childToParentAsin[ch.asin] = par; });
            });

            const selector = document.getElementById('overview-product-selector');
            if (selector) {
                const previousSelection = selector.value;

                // Expand each parent row into its child variants
                const childOptions = [];
                uniqueRows.forEach(row => {
                    const parentAsin = row.parent_asin || row.asin;
                    const children = childProductsMap[parentAsin] || [];
                    if (children.length > 0) {
                        children.forEach(child => {
                            const skuDisplay = (child.sku && child.sku !== child.asin) ? child.sku : child.asin;
                            childOptions.push({ value: child.asin, label: `${skuDisplay} — ${child.title || child.asin}`, parentAsin });
                        });
                    } else {
                        childOptions.push({ value: row.asin, label: `${row.asin} — ${getParentAsinTitle(row)}`, parentAsin });
                    }
                });

                selector.innerHTML = `<option value="" disabled>Select Product to Analyze...</option>` +
                    childOptions.map((opt, index) => {
                        const isSelected = previousSelection ? opt.value === previousSelection : index === 0;
                        return `<option value="${escapeHtml(opt.value)}" title="${escapeHtml(opt.label)}" ${isSelected ? 'selected' : ''}>${escapeHtml(opt.label)}</option>`;
                    }).join('');
                selector.title = selector.options[selector.selectedIndex]?.textContent.trim() || '';

                const activeChildAsin = selector.value;
                const activeParentAsin = childToParentAsin[activeChildAsin] || activeChildAsin;
                const activeRow = uniqueRows.find(r => (r.parent_asin || r.asin) === activeParentAsin) || uniqueRows[0];

                if (activeRow) {
                    activeFilterParentAsin = activeRow.parent_asin || activeRow.asin;
                    renderPricingHistogram(activeRow);
                    renderRatingVsPriceBubbleChart(activeRow);
                    updatePortfolioMarkers(activeRow);
                    renderRecommendations(globalRecommendations);
                    renderCompetitorsSection(activeRow);
                } else {
                    renderPricingHistogram(null);
                    renderRatingVsPriceBubbleChart(null);
                }
            }
        }

        function calculateMarketPosition(price, competitors = [], targetMedian = 0) {
            const compCount = competitors ? competitors.length : 0;
            if (compCount === 0) {
                return { pct: 50, zone: 'no_competitors' };
            }

            if (price <= 0) {
                return { pct: 0, zone: 'below_market' };
            }

            if (price === targetMedian) {
                return { pct: 50, zone: 'mid_market' };
            }

            let pct = 50;
            let zone = 'mid_market';

            if (price < targetMedian) {
                pct = (price / (targetMedian || 1)) * 50;
                if (pct < 15) zone = 'below_market';
                else if (pct < 35) zone = 'budget';
                else zone = 'value';
            } else {
                const over = price - targetMedian;
                pct = Math.min(100.0, 50.0 + (over / (targetMedian || 1)) * 50.0);
                if (pct > 85) zone = 'above_market';
                else if (pct > 65) zone = 'premium';
                else zone = 'mid_market';
            }

            return { pct, zone };
        }

        function updatePortfolioMarkers(selectedRow) {
            if (!selectedRow) return;
            const marketIndex = window.currentAvgMarketIndex || 100;
            
            // Look up in globalRecommendations for accurate min/max/percentile info
            let targetRec = globalRecommendations.find(r => (r.parent_asin || r.asin) === (selectedRow.parent_asin || selectedRow.asin));
            targetRec = targetRec || selectedRow;
            
            const meta = targetRec.metadata || targetRec;
            
            let rawMedian = parseFloat(meta?.median_price);
            if (isNaN(rawMedian)) rawMedian = parseFloat(targetRec?.median_price);
            if (isNaN(rawMedian)) rawMedian = parseFloat(targetRec?.recommended_price);
            if (isNaN(rawMedian)) rawMedian = parseFloat(selectedRow?.median_price);
            if (isNaN(rawMedian)) rawMedian = 0;

            let currentPrice = parseFloat(targetRec?.current_price);
            if (isNaN(currentPrice)) currentPrice = parseFloat(targetRec?.your_price);
            if (isNaN(currentPrice)) currentPrice = parseFloat(selectedRow?.current_price);
            if (isNaN(currentPrice)) currentPrice = parseFloat(selectedRow?.your_price);
            if (isNaN(currentPrice)) currentPrice = 0;

            const targetMedian = rawMedian;

            let competitors = meta?.competitors || [];
            let nCompetitors = competitors.length;
            if (nCompetitors === 0) {
                const metaCount = meta?.n_competitors || targetRec?.n_competitors || selectedRow?.n_competitors;
                const reasonMatch = String(targetRec?.reasoning || selectedRow?.reasoning || '').match(/^(\d+)\s+competitors/i);
                const count = Number.isFinite(metaCount) ? metaCount : (reasonMatch ? Number(reasonMatch[1]) : 0);
                if (count > 0) {
                    competitors = new Array(count).fill({});
                    nCompetitors = count;
                }
            }

            const adjMedianPos = calculateMarketPosition(targetMedian, competitors, targetMedian);
            const currentPos = calculateMarketPosition(currentPrice, competitors, targetMedian);

            const adjMedianPct = adjMedianPos.pct;
            const currentPct = currentPos.pct;
            
            const markerOrig = document.getElementById('portfolio-marker-original');
            const markerAdj = document.getElementById('portfolio-marker-adjusted');
            const markerCurr = document.getElementById('portfolio-marker-current');
            const legend = document.getElementById('portfolio-map-legend');
            
            if (nCompetitors === 0) {
                if (markerOrig) markerOrig.style.display = 'none';
                if (markerAdj) markerAdj.style.display = 'none';
                if (markerCurr) markerCurr.style.display = 'none';
                if (legend) legend.style.display = 'none';
                return;
            }

            if (markerOrig) {
                markerOrig.style.display = 'none';
            }
            if (markerAdj) {
                markerAdj.style.display = 'block';
                markerAdj.style.left = `${adjMedianPct}%`;
                markerAdj.title = `Median: AED ${targetMedian.toFixed(2)}`;
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
                                body.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 40px;">No pending recommendations</td></tr>';
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

                            // Precompute properties for consistency in filters, sorting, and rendering
                            processedRecs.forEach(r => {
                                const rawMedian = (r.metadata && r.metadata.median_price) ? Number(r.metadata.median_price) : (r.recommended_price || 0);
                                const marketIndex = window.currentAvgMarketIndex || 100;
                                r.calculatedAdjMedian = rawMedian * (marketIndex / 100);
                                
                                let currentPrice = parseFloat(r.current_price);
                                if (isNaN(currentPrice)) currentPrice = parseFloat(r.your_price);
                                if (isNaN(currentPrice)) currentPrice = 0;
                                r.calculatedCurrentPrice = currentPrice;

            // Precompute properties for consistency in filters, sorting, and rendering
            processedRecs.forEach(r => {
                const rawMedian = (r.metadata && r.metadata.median_price) ? Number(r.metadata.median_price) : (r.recommended_price || 0);
                const marketIndex = window.currentAvgMarketIndex || 100;
                r.calculatedAdjMedian = rawMedian * (marketIndex / 100);

                                // Precompute competitor range dynamically (with robust fallback to competitors array)
                                let pMin = parseFloat(r.metadata && r.metadata.floor_price) || 0;
                                let pMax = parseFloat(r.metadata && r.metadata.ceiling_price) || 0;
                                if (pMin === 0 || pMax === 0) {
                                    if (r.metadata && r.metadata.competitors && r.metadata.competitors.length > 0) {
                                        const prices = r.metadata.competitors.map(c => parseFloat(c.price)).filter(p => !isNaN(p) && p > 0);
                                        if (prices.length > 0) {
                                            pMin = Math.min(...prices);
                                            pMax = Math.max(...prices);
                                        }
                                    }
                                }
                                r.calculatedFloorPrice = pMin;
                                r.calculatedCeilingPrice = pMax;

                                // Calculate Market Position dynamically using direct Adj. Median comparison
                                let competitors = (r.metadata && r.metadata.competitors) || [];
                                if (competitors.length === 0 && r._competitorCount > 0) {
                                    competitors = new Array(r._competitorCount).fill({});
                                }
                                const marketPos = calculateMarketPosition(r.calculatedCurrentPrice, competitors, r.calculatedAdjMedian);
                                r.calculatedPct = marketPos.pct;
                                r.calculatedZone = marketPos.zone;

                                // Build dynamic reasoning text
                                const zoneMessageMap = {
                                    'below_market': 'Currently below market floor.',
                                    'budget': 'Currently in budget zone.',
                                    'value': 'Currently in value zone.',
                                    'mid_market': 'Currently in mid-market zone.',
                                    'premium': 'Currently in premium zone.',
                                    'above_market': 'Currently above market ceiling.'
                                };
                                const zoneMsg = zoneMessageMap[marketPos.zone] || '';
                                const targetMsg = `Mid-market strategy: adjusted median (AED ${r.calculatedAdjMedian.toFixed(2)}).`;
                                const compMsg = `${r._competitorCount} competitors. Range AED ${pMin.toFixed(2)}-AED ${pMax.toFixed(2)}. Adjusted Median AED ${r.calculatedAdjMedian.toFixed(2)}.`;
                                r.calculatedReasoning = `${compMsg} | ${zoneMsg} | ${targetMsg}`;
                            });

                            // 1. Apply Search Filter
                            const searchVal = (document.getElementById('recs-search')?.value || '').toLowerCase().trim();
                            if (searchVal) {
                                processedRecs = processedRecs.filter(r => {
                                    const asin = (r.parent_asin || r.asin || '').toLowerCase();
                                    const title = (r.title || '').toLowerCase();
                                    const reasoning = (r.calculatedReasoning || r.reasoning || '').toLowerCase();
                                    return asin.includes(searchVal) || title.includes(searchVal) || reasoning.includes(searchVal);
                                });
                            }

                            // 2. Apply Action Filter
                            const actionFilter = document.getElementById('recs-action-filter')?.value || 'all';
                            if (actionFilter !== 'all') {
                                processedRecs = processedRecs.filter(r => (r.calculatedAction || '').toLowerCase() === actionFilter);
                            }

                            // 3. Apply Product Filter (from chart product selector)
                            const badge = document.getElementById('recs-product-filter-badge');
                            if (activeFilterParentAsin) {
                                processedRecs = processedRecs.filter(r => (r.parent_asin || r.asin) === activeFilterParentAsin);
                                if (badge) badge.style.display = 'flex';
                            } else {
                                if (badge) badge.style.display = 'none';
                            }

                            // 4. Apply Sort
                            const sortBy = document.getElementById('recs-sort-by')?.value || 'default';
                            if (sortBy === 'default') {
                                processedRecs.sort((a, b) => {
                                    if (a.calculatedAction !== b.calculatedAction) return a.calculatedAction === 'decrease' ? -1 : 1;
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
                                processedRecs.sort((a, b) => (b.calculatedCurrentPrice || 0) - (a.calculatedCurrentPrice || 0));
                            } else if (sortBy === 'current-asc') {
                                processedRecs.sort((a, b) => (a.calculatedCurrentPrice || 0) - (b.calculatedCurrentPrice || 0));
                            } else if (sortBy === 'target-desc') {
                                processedRecs.sort((a, b) => (b.calculatedAdjMedian || 0) - (a.calculatedAdjMedian || 0));
                            } else if (sortBy === 'target-asc') {
                                processedRecs.sort((a, b) => (a.calculatedAdjMedian || 0) - (b.calculatedAdjMedian || 0));
                            } else if (sortBy === 'competitors-desc') {
                                processedRecs.sort((a, b) => b._competitorCount - a._competitorCount);
                            }

                            body.innerHTML = processedRecs.map(r => {
                                const adjMedian = r.calculatedAdjMedian;
                                const currentPrice = r.calculatedCurrentPrice;
                                const pct = r.calculatedPct;
                                const zone = r.calculatedZone;
                                const action = r.calculatedAction;
                                const reasoning = r.calculatedReasoning;
                                const readableZone = (zone || 'Unknown').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

                                return `
                                <tr data-asin="${r.parent_asin || r.asin}" style="border-left: 3px solid var(--accent);">
                                    <td>
                                        <div style="font-weight: 700; color: var(--text); margin-bottom: 6px;">${r.parent_asin || r.asin}</div>
                                        <div style="font-weight: 600; color: var(--text); font-size: 13px; line-height: 1.4; max-width: 300px; word-break: break-word;" title="${r.title || 'Parent ASIN Group'}">${r.title || 'Parent ASIN Group'}</div>
                                    </td>
                                    <td><span class="price-badge" style="color: ${r._competitorCount > 0 ? 'var(--success)' : 'var(--danger)'}">${r._competitorCount.toLocaleString()}</span></td>
                                    <td><span class="price-badge">${(currentPrice || 0).toFixed(2)}</span></td>
                                    <td>
                                        <span class="price-badge" style="color: var(--text);">${(r.metadata?.median_price || r.recommended_price || 0).toFixed(2)}</span>
                                    </td>
                                    <td>
                                        <span class="price-badge" style="color: var(--warning); font-weight: 700;">${adjMedian.toFixed(2)}</span>
                                    </td>
                                    <td>
                                        <span class="action-chip action-${action}">${action}</span>
                                    </td>
                                    <td style="color: var(--text-dim); font-size: 13px; max-width: 400px; line-height: 1.4;">
                                        ${reasoning}
                                    </td>
                                    <td>
                                        ${(() => {
                                            if (r._competitorCount > 0) {
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
