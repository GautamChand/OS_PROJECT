// dashboard.js — Controller for the main dashboard view

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    setupQuickActions();
    
    // Set up drag-and-drop folder monitoring
    if (typeof initDragAndDrop === 'function') {
        initDragAndDrop('dropzone', (newPath) => {
            loadDashboardData();
        });
    }
    
    // Callback for folder updates
    window.onFolderUpdated = function(path) {
        document.getElementById('currentFolderPathText').innerText = path;
        loadDashboardData();
    };
});

async function loadDashboardData() {
    try {
        // Show shimmer/loading states if we had any
        
        // 1. Get Folder info
        const folderInfo = await API.get('/api/folders/current');
        const folderPathText = document.getElementById('currentFolderPathText');
        if (folderPathText) {
            folderPathText.innerText = folderInfo.path || 'Not Set';
        }
        
        // 2. Get Overview statistics
        const stats = await API.get('/api/dashboard/overview');
        animateCounter('statTotalFiles', stats.total_files);
        animateCounter('statTotalSize', stats.total_size, 1500, (v) => UI.formatBytes(v));
        animateCounter('statSavedSize', stats.space_saved, 1500, (v) => UI.formatBytes(v));
        
        const savingsRatio = stats.total_size > 0 ? (stats.space_saved / stats.total_size) : 0;
        animateCounter('statSavingsRatio', savingsRatio, 1500, (v) => UI.formatPercent(v));
        
        // Update progress bar
        const progressFill = document.getElementById('dashboardProgressFill');
        const progressLabel = document.getElementById('dashboardProgressLabel');
        if (progressFill && progressLabel) {
            const savingsPercent = (savingsRatio * 100).toFixed(1);
            progressFill.style.width = `${savingsPercent}%`;
            progressLabel.innerText = `${savingsPercent}% Space Optimized`;
        }
        
        // 3. Get Temperature distribution & render chart
        const temps = await API.get('/api/dashboard/file-temperatures');
        if (typeof createTemperatureChart === 'function') {
            createTemperatureChart(
                'temperatureChartCanvas', 
                temps.hot || 0, 
                temps.warm || 0, 
                temps.cold || 0, 
                temps.archive || 0
            );
        }
        
        // 4. Get Recommendations
        const recs = await API.get('/api/dashboard/recommendations');
        renderRecommendations(recs);
        
        // 5. Get Recent Activity
        const activity = await API.get('/api/dashboard/recent-activity');
        renderActivityLog(activity);
        
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

function renderRecommendations(recommendations) {
    const container = document.getElementById('recommendationsContainer');
    if (!container) return;
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="text-align:center; padding:30px; color:var(--text-muted);">
                <div style="font-size:32px; margin-bottom:8px;">💡</div>
                <p>System fully optimized. No recommendations at this time.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = recommendations.map(rec => {
        let badgeClass = 'primary';
        if (rec.category === 'savings') badgeClass = 'success';
        if (rec.category === 'warning') badgeClass = 'warm';
        if (rec.category === 'danger') badgeClass = 'danger';
        
        return `
            <div class="glass-card recommendation-card ${badgeClass}" id="rec-card-${rec.id}" style="margin-bottom:12px; padding:16px; display:flex; justify-content:space-between; align-items:center; border-left:4px solid var(--accent-${rec.category === 'savings' ? 'green' : (rec.category === 'warning' ? 'orange' : 'red')});">
                <div>
                    <p class="rec-message" style="font-weight:500; font-size:13.5px; color:var(--text-primary);">${rec.message}</p>
                    ${rec.potential_savings > 0 ? `<span class="rec-savings" style="font-size:11px; font-weight:600; color:var(--accent-green); background:rgba(16,185,129,0.1); padding:2px 6px; border-radius:var(--radius-full); margin-top:4px; display:inline-block;">Est. Savings: ${UI.formatBytes(rec.potential_savings)}</span>` : ''}
                </div>
                <div style="display:flex; gap:8px;">
                    ${rec.action_type ? `<button class="btn btn-primary btn-sm" onclick="executeRecommendation(${rec.id}, '${rec.action_type}', '${rec.action_data}')">Apply</button>` : ''}
                    <button class="btn btn-secondary btn-sm" onclick="dismissRecommendation(${rec.id})">Dismiss</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderActivityLog(activities) {
    const container = document.getElementById('activityLogContainer');
    if (!container) return;
    
    if (!activities || activities.length === 0) {
        container.innerHTML = `
            <p style="text-align:center; padding:20px; color:var(--text-muted); font-size:13px;">No recent operations recorded.</p>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="activity-timeline" style="position:relative; padding-left:20px; border-left:2px solid var(--border-subtle);">
            ${activities.map(act => {
                const isCompress = act.operation === 'compress';
                const dotColor = isCompress ? 'var(--primary)' : 'var(--accent-green)';
                return `
                    <div class="activity-item" style="position:relative; margin-bottom:16px;">
                        <span class="activity-dot" style="position:absolute; left:-25px; top:5px; width:10px; height:10px; border-radius:50%; background:${dotColor}; border:2px solid var(--bg-card);"></span>
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div>
                                <p style="font-weight:600; font-size:13px; color:var(--text-primary); margin:0;">
                                    ${isCompress ? 'Compressed' : 'Decompressed'} <code>${act.filename}</code>
                                </p>
                                <p style="font-size:11px; color:var(--text-muted); margin:2px 0 0 0;">
                                    Algorithm: <span style="font-weight:600; color:var(--text-secondary);">${act.algorithm || 'zlib'}</span> | 
                                    Saved: <span style="font-weight:600; color:var(--accent-green);">${UI.formatBytes(act.savings_bytes || 0)}</span> | 
                                    Time: ${act.duration_ms.toFixed(1)}ms
                                </p>
                            </div>
                            <span style="font-size:11px; color:var(--text-muted); white-space:nowrap;">${UI.formatRelativeTime(act.performed_at)}</span>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function executeRecommendation(id, actionType, actionData) {
    UI.showToast('Executing recommendation...', 'info');
    try {
        if (actionType === 'compress_folder') {
            await API.post('/api/compress/batch', { temperature: actionData });
        } else if (actionType === 'compress_file') {
            await API.post('/api/compress/file', { file_id: parseInt(actionData) });
        }
        UI.showToast('Recommendation applied successfully!', 'success');
        dismissRecommendation(id);
        loadDashboardData();
    } catch (error) {
        // Error already handled
    }
}

async function dismissRecommendation(id) {
    try {
        // In database, we can mark as dismissed
        await fetch(`/api/dashboard/recommendations/dismiss/${id}`, { method: 'POST' });
        const el = document.getElementById(`rec-card-${id}`);
        if (el) {
            el.style.transform = 'translateX(100px)';
            el.style.opacity = '0';
            setTimeout(() => {
                el.remove();
                // Check if any recommendation card left
                const container = document.getElementById('recommendationsContainer');
                if (container && container.children.length === 0) {
                    renderRecommendations([]);
                }
            }, 300);
        }
    } catch (error) {
        console.error("Error dismissing recommendation:", error);
    }
}

function setupQuickActions() {
    const btnScan = document.getElementById('btnScanNow');
    if (btnScan) {
        btnScan.addEventListener('click', async () => {
            btnScan.disabled = true;
            btnScan.innerHTML = '⚡ Scanning...';
            UI.showToast('Scanning file system metadata...', 'info');
            try {
                const res = await API.get('/api/folders/scan');
                UI.showToast(`Scan complete. Tracked ${res.scanned} files.`, 'success');
                loadDashboardData();
            } catch (err) {
                // error handled
            } finally {
                btnScan.disabled = false;
                btnScan.innerHTML = '⚡ Scan Now';
            }
        });
    }
    
    const btnScheduler = document.getElementById('btnRunScheduler');
    if (btnScheduler) {
        btnScheduler.addEventListener('click', async () => {
            btnScheduler.disabled = true;
            btnScheduler.innerHTML = '⚙️ Optimizing...';
            UI.showToast('Running background compression cycle...', 'info');
            try {
                const res = await API.post('/api/scheduler/run-now');
                if (res.processed > 0) {
                    UI.showToast(`Scheduler processed ${res.processed} cold/archive files.`, 'success');
                } else {
                    UI.showToast('Scheduler finished. No files required compression.', 'info');
                }
                loadDashboardData();
            } catch (err) {
                // error handled
            } finally {
                btnScheduler.disabled = false;
                btnScheduler.innerHTML = '⚙️ Run Scheduler';
            }
        });
    }
    
    const btnSimulate = document.getElementById('btnRunSimulation');
    if (btnSimulate) {
        btnSimulate.addEventListener('click', async () => {
            btnSimulate.disabled = true;
            btnSimulate.innerHTML = '🔍 Simulating...';
            UI.showToast('Simulating compression and estimating savings...', 'info');
            try {
                const res = await API.post('/api/compress/simulate');
                UI.showToast(`Simulation complete! Estimated savings: ${UI.formatBytes(res.estimated_savings_bytes)} (${UI.formatPercent(res.estimated_ratio)} ratio)`, 'success');
                loadDashboardData();
            } catch (err) {
                // error handled
            } finally {
                btnSimulate.disabled = false;
                btnSimulate.innerHTML = '🔍 Run Simulation';
            }
        });
    }
    
    const btnChangeFolder = document.getElementById('btnChangeFolder');
    if (btnChangeFolder) {
        btnChangeFolder.addEventListener('click', () => {
            if (typeof promptForPath === 'function') {
                promptForPath();
            }
        });
    }
}
