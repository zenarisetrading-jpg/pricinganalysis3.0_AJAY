const processedRecs = [];
let body = {};
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
                                </tr>
                            `}).join('');

            }

        function renderAlerts(alerts) {
                    renderAlertFeed('alerts-feed', alerts, 10);
                }

        function renderAlertFeed(targetId, alerts, limit = 50) {
