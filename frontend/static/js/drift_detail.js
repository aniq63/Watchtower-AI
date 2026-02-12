// Drift Detail Page - Tabbed Interface with Distribution Charts
let currentProjectId = null;
let currentDriftId = null;
let driftData = null;
let charts = {};

// Check authentication and load data
document.addEventListener('DOMContentLoaded', async () => {
    const token = sessionStorage.getItem('session_token');
    if (!token) {
        console.error('No session token found, redirecting to login');
        window.location.href = '/login';
        return;
    }

    currentProjectId = document.getElementById('project-id').value;
    currentDriftId = document.getElementById('drift-id').value;

    console.log('Starting drift detail page load...');
    console.log('Project ID:', currentProjectId);
    console.log('Drift ID:', currentDriftId);
    console.log('Session Token:', token ? 'Present' : 'Missing');

    await loadDriftDetails();
});

// Load drift details
async function loadDriftDetails() {
    const token = sessionStorage.getItem('session_token');
    const url = `/projects/${currentProjectId}/drift-runs/${currentDriftId}`;

    console.log('Fetching drift data from:', url);

    try {
        const response = await fetch(url, {
            headers: { 'session_token': token }
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (response.ok) {
            driftData = await response.json();
            console.log('✅ Drift data loaded successfully:', driftData);
            console.log('Feature stats keys:', Object.keys(driftData.feature_stats || {}));
            console.log('Drift tests keys:', Object.keys(driftData.drift_tests || {}));
            console.log('Alerts:', driftData.alerts);

            renderDriftAnalysis();
        } else {
            const errorText = await response.text();
            console.error('❌ Failed to load drift analysis. Status:', response.status);
            console.error('Error response:', errorText);
            showError(`Failed to load drift analysis: ${response.status} ${errorText}`);
        }
    } catch (error) {
        console.error('❌ Error loading drift details:', error);
        showError(`Error loading drift analysis: ${error.message}`);
    }
}

// Show error in all tabs
function showError(message) {
    const errorHtml = `<tr><td colspan="9" class="empty-cell" style="color: #dc2626;">${message}</td></tr>`;
    document.getElementById('mean-shift-tbody').innerHTML = errorHtml;
    document.getElementById('median-shift-tbody').innerHTML = errorHtml;
    document.getElementById('variance-shift-tbody').innerHTML = errorHtml;
    document.getElementById('ks-test-tbody').innerHTML = errorHtml.replace('colspan="9"', 'colspan="8"');
    document.getElementById('psi-tbody').innerHTML = errorHtml.replace('colspan="9"', 'colspan="7"');
    document.getElementById('model-drift-empty').textContent = message;
    document.getElementById('model-drift-empty').style.display = 'block';
    document.getElementById('model-drift-container').style.display = 'none';
}

// Render drift analysis
// Helper to safely parse JSON strings (recursively if needed)
function safeParseJSON(data) {
    if (!data) return {};
    let parsed = data;
    let attempts = 0;
    // Recursively parse if string, up to 3 times to handle double-encoding
    while (typeof parsed === 'string' && attempts < 3) {
        try {
            parsed = JSON.parse(parsed);
        } catch (e) {
            console.error("JSON parse failed", e);
            break;
        }
        attempts++;
    }
    return parsed;
}

// Simple Markdown renderer for LLM text
function formatMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
        .replace(/### (.*?)\n/g, '<h3>$1</h3>')          // H3
        .replace(/## (.*?)\n/g, '<h2>$1</h2>')           // H2
        .replace(/# (.*?)\n/g, '<h1>$1</h1>')            // H1
        .replace(/- (.*?)\n/g, '<li>$1</li>')            // List items
        .replace(/\n/g, '<br>');                         // Newlines
}

// Render drift analysis
function renderDriftAnalysis() {
    console.log('🎨 Starting to render drift analysis...');

    // Robustly parse all JSON fields
    driftData.feature_stats = safeParseJSON(driftData.feature_stats);
    driftData.drift_tests = safeParseJSON(driftData.drift_tests);
    driftData.alerts = Array.isArray(driftData.alerts) ? driftData.alerts : safeParseJSON(driftData.alerts);

    // Extra validation logging
    console.log('Final feature_stats keys:', Object.keys(driftData.feature_stats || {}));
    console.log('Final drift_tests keys:', Object.keys(driftData.drift_tests || {}));

    // Update status banner
    const statusBanner = document.getElementById('drift-status-banner');
    const statusText = document.getElementById('drift-status-text');

    const driftScore = driftData.drift_score || 0.5;

    if (driftData.overall_drift) {
        statusBanner.className = 'drift-status-banner drift-detected';
        statusText.textContent = `Dataset Drift is DETECTED. Drift Score: ${driftScore.toFixed(2)}`;
    } else {
        statusBanner.className = 'drift-status-banner no-drift';
        statusText.textContent = `Dataset Drift is NOT detected. Drift Score: ${driftScore.toFixed(2)}`;
    }

    // Calculate summary stats
    const features = Object.keys(driftData.feature_stats || {});
    const totalColumns = features.length;
    // Ensure alerts is an array
    const alerts = Array.isArray(driftData.alerts) ? driftData.alerts : [];
    const driftedColumns = alerts.length;
    const driftShare = totalColumns > 0 ? (driftedColumns / totalColumns) : 0;

    console.log(`📊 Summary: ${totalColumns} columns, ${driftedColumns} drifted (${(driftShare * 100).toFixed(1)}%)`);

    document.getElementById('total-columns').textContent = totalColumns;
    document.getElementById('drifted-columns').textContent = driftedColumns;
    document.getElementById('drift-share').textContent = driftShare.toFixed(3);

    // Update summary text
    const summaryText = `Drift is detected for ${(driftShare * 100).toFixed(3)}% of columns (${driftedColumns} out of ${totalColumns}).`;
    document.getElementById('summary-text').textContent = summaryText;

    // Show LLM interpretation if available
    if (driftData.llm_interpretation) {
        document.getElementById('llm-interpretation-box').style.display = 'block';
        // Use Markdown formatting
        document.getElementById('llm-interpretation-text').innerHTML = formatMarkdown(driftData.llm_interpretation);
    }

    // Render all tabs
    console.log('📋 Rendering all tabs...');
    renderAllTabs();
}

// Render all tabs
function renderAllTabs() {
    console.log('📋 Rendering all tabs...');
    console.log('=== FULL DRIFT DATA STRUCTURE ===');
    console.log('drift_tests:', JSON.stringify(driftData.drift_tests, null, 2));
    console.log('feature_stats:', JSON.stringify(driftData.feature_stats, null, 2));
    console.log('=================================');

    // Check what tests are available
    const driftTests = driftData.drift_tests || {};
    const testCounts = {
        mean_shift: 0,
        median_shift: 0,
        variance_shift: 0,
        ks_test: 0,
        psi: 0
    };

    for (const [column, tests] of Object.entries(driftTests)) {
        console.log(`Column "${column}" has tests:`, Object.keys(tests));
        if (tests.mean_shift) testCounts.mean_shift++;
        if (tests.median_shift) testCounts.median_shift++;
        if (tests.variance_shift) testCounts.variance_shift++;
        if (tests.ks_test) testCounts.ks_test++;
        if (tests.psi) testCounts.psi++;
    }

    console.log('Test counts:', testCounts);

    renderMeanShiftTab();
    renderMedianShiftTab();
    renderVarianceShiftTab();
    renderKSTestTab();
    renderKSTestTab();
    renderPSITab();
    renderModelBasedDriftTab();
    console.log('✅ All tabs rendered');
}

// Render Mean Shift Tab
function renderMeanShiftTab() {
    const tbody = document.getElementById('mean-shift-tbody');
    const driftTests = driftData.drift_tests || {};

    console.log('📊 Rendering Mean Shift Tab...');
    console.log('Total drift_tests entries:', Object.keys(driftTests).length);

    const rows = [];
    let index = 0;

    for (const [column, tests] of Object.entries(driftTests)) {
        if (tests.mean_shift) {
            const stats = driftData.feature_stats[column];
            const test = tests.mean_shift;
            const isDrift = test.drift_detected;

            // Check for baseline (required). Current is optional - use fallback if missing
            if (!stats || !stats.baseline) {
                console.warn(`  ⚠️ Column "${column}" missing baseline stats:`, stats);
                continue;
            }

            console.log(`  ✓ Column "${column}" has mean_shift test, drift=${isDrift}`);

            const baselineMean = stats.baseline.mean ?? 0;
            const currentMean = stats.current?.mean ?? stats.baseline.mean ?? 0;
            const changeValue = test.value ?? 0;
            const threshold = test.threshold ?? 0.1;

            rows.push(`
                <tr class="${isDrift ? 'drift-row' : 'normal-row'}">
                    <td><strong>${column}</strong></td>
                    <td>num</td>
                    <td>${baselineMean.toFixed(4)}</td>
                    <td>${currentMean.toFixed(4)}</td>
                    <td>${changeValue.toFixed(4)}</td>
                    <td>${threshold}</td>
                    <td><span class="status-badge ${isDrift ? 'status-drift' : 'status-normal'}">
                        ${isDrift ? 'Detected' : 'Not Detected'}
                    </span></td>
                </tr>
            `);

            index++;
        }
    }

    if (rows.length > 0) {
        tbody.innerHTML = rows.join('');
        console.log(`✅ Mean Shift Tab: Rendered ${rows.length} rows`);
    } else {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-cell">No mean shift tests available for this drift run</td></tr>';
        console.log('⚠️ Mean Shift Tab: No data found');
    }
}

// Render Median Shift Tab
function renderMedianShiftTab() {
    const tbody = document.getElementById('median-shift-tbody');
    const driftTests = driftData.drift_tests || {};

    console.log('📊 Rendering Median Shift Tab...');

    const rows = [];

    for (const [column, tests] of Object.entries(driftTests)) {
        if (tests.median_shift) {
            const stats = driftData.feature_stats[column];
            const test = tests.median_shift;
            const isDrift = test.drift_detected;

            if (!stats || !stats.baseline) {
                console.warn(`  ⚠️ Column "${column}" missing baseline stats`);
                continue;
            }

            const baselineMedian = stats.baseline.median ?? 0;
            const currentMedian = stats.current?.median ?? stats.baseline.median ?? 0;
            const changeValue = test.value ?? 0;
            const threshold = test.threshold ?? 0.1;

            rows.push(`
                <tr class="${isDrift ? 'drift-row' : 'normal-row'}">
                    <td><strong>${column}</strong></td>
                    <td>num</td>
                    <td>${baselineMedian.toFixed(4)}</td>
                    <td>${currentMedian.toFixed(4)}</td>
                    <td>${changeValue.toFixed(4)}</td>
                    <td>${threshold}</td>
                    <td><span class="status-badge ${isDrift ? 'status-drift' : 'status-normal'}">
                        ${isDrift ? 'Detected' : 'Not Detected'}
                    </span></td>
                </tr>
            `);
        }
    }

    tbody.innerHTML = rows.length > 0 ? rows.join('') : '<tr><td colspan="7" class="empty-cell">No median shift tests available</td></tr>';
    console.log(`✅ Median Shift Tab: ${rows.length} rows`);
}

// Render Variance Shift Tab
function renderVarianceShiftTab() {
    const tbody = document.getElementById('variance-shift-tbody');
    const driftTests = driftData.drift_tests || {};

    console.log('📊 Rendering Variance Shift Tab...');

    const rows = [];

    for (const [column, tests] of Object.entries(driftTests)) {
        if (tests.variance_shift) {
            const stats = driftData.feature_stats[column];
            const test = tests.variance_shift;
            const isDrift = test.drift_detected;

            if (!stats || !stats.baseline) {
                console.warn(`  ⚠️ Column "${column}" missing baseline stats`);
                continue;
            }

            const baselineVar = stats.baseline.std ? Math.pow(stats.baseline.std, 2) : 0;
            const currentVar = (stats.current?.std ?? stats.baseline.std) ? Math.pow(stats.current?.std ?? stats.baseline.std, 2) : 0;
            const changeValue = test.value ?? 0;
            const threshold = test.threshold ?? 0.2;

            rows.push(`
                <tr class="${isDrift ? 'drift-row' : 'normal-row'}">
                    <td><strong>${column}</strong></td>
                    <td>num</td>
                    <td>${baselineVar.toFixed(4)}</td>
                    <td>${currentVar.toFixed(4)}</td>
                    <td>${changeValue.toFixed(4)}</td>
                    <td>${threshold}</td>
                    <td><span class="status-badge ${isDrift ? 'status-drift' : 'status-normal'}">
                        ${isDrift ? 'Detected' : 'Not Detected'}
                    </span></td>
                </tr>
            `);
        }
    }

    tbody.innerHTML = rows.length > 0 ? rows.join('') : '<tr><td colspan="7" class="empty-cell">No variance shift tests available</td></tr>';
    console.log(`✅ Variance Shift Tab: ${rows.length} rows`);
}

// Render KS Test Tab
function renderKSTestTab() {
    const tbody = document.getElementById('ks-test-tbody');
    const driftTests = driftData.drift_tests || {};

    console.log('📊 Rendering KS Test Tab...');

    const rows = [];

    for (const [column, tests] of Object.entries(driftTests)) {
        if (tests.ks_test) {
            const stats = driftData.feature_stats[column];
            const test = tests.ks_test;
            const isDrift = test.drift_detected;

            if (!stats || !stats.baseline) {
                console.warn(`  ⚠️ Column "${column}" missing baseline stats`);
                continue;
            }

            const ksStatistic = test.statistic ?? 0;
            const pValue = test.p_value ?? 1;
            const threshold = test.threshold ?? 0.05;

            rows.push(`
                <tr class="${isDrift ? 'drift-row' : 'normal-row'}">
                    <td><strong>${column}</strong></td>
                    <td>num</td>
                    <td>${ksStatistic.toFixed(6)}</td>
                    <td>${pValue.toExponential(4)}</td>
                    <td>${threshold}</td>
                    <td><span class="status-badge ${isDrift ? 'status-drift' : 'status-normal'}">
                        ${isDrift ? 'Detected' : 'Not Detected'}
                    </span></td>
                </tr>
            `);
        }
    }

    tbody.innerHTML = rows.length > 0 ? rows.join('') : '<tr><td colspan="6" class="empty-cell">No KS tests available</td></tr>';
    console.log(`✅ KS Test Tab: ${rows.length} rows`);
}

// Render PSI Tab
function renderPSITab() {
    const tbody = document.getElementById('psi-tbody');
    const driftTests = driftData.drift_tests || {};

    console.log('📊 Rendering PSI Tab...');

    const rows = [];

    for (const [column, tests] of Object.entries(driftTests)) {
        if (tests.psi) {
            const stats = driftData.feature_stats[column];
            const test = tests.psi;
            const severity = test.severity || 'low';
            const isDrift = severity === 'high';

            if (!stats || !stats.baseline) {
                console.warn(`  ⚠️ Column "${column}" missing baseline stats`);
                continue;
            }

            const psiValue = test.value ?? 0;

            rows.push(`
                <tr class="${isDrift ? 'drift-row' : severity === 'medium' ? 'warning-row' : 'normal-row'}">
                    <td><strong>${column}</strong></td>
                    <td>num</td>
                    <td>${psiValue.toFixed(6)}</td>
                    <td><span class="severity-badge severity-${severity}">${severity.toUpperCase()}</span></td>
                    <td><span class="status-badge ${isDrift ? 'status-drift' : severity === 'medium' ? 'status-warning' : 'status-normal'}">
                        ${isDrift ? 'Detected' : severity === 'medium' ? 'Moderate' : 'Not Detected'}
                    </span></td>
                </tr>
            `);
        }
    }

    tbody.innerHTML = rows.length > 0 ? rows.join('') : '<tr><td colspan="5" class="empty-cell">No PSI tests available</td></tr>';
    console.log(`✅ PSI Tab: ${rows.length} rows`);
}

// Render mini distribution chart
function renderMiniChart(canvasId, stats, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas not found: ${canvasId}`);
        return;
    }

    const ctx = canvas.getContext('2d');

    // Create histogram visualization using actual stats
    const mean = stats?.mean || 0;
    const std = stats?.std || 1;

    // Generate normal distribution approximation
    const bins = 12;
    const data = [];
    for (let i = 0; i < bins; i++) {
        const x = mean + (i - bins / 2) * (std / 2);
        const y = Math.exp(-0.5 * Math.pow((x - mean) / std, 2));
        data.push(y);
    }

    // Destroy existing chart if it exists
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }

    // Create new chart
    charts[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Array(bins).fill(''),
            datasets: [{
                data: data,
                backgroundColor: color,
                borderColor: color,
                borderWidth: 0,
                barPercentage: 1.0,
                categoryPercentage: 1.0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            }
        }
    });
}

// Render Model-Based Drift Tab
function renderModelBasedDriftTab() {
    console.log('📊 Rendering Model-Based Drift Tab...');
    const modelDrift = driftData.model_based_drift;
    const container = document.getElementById('model-drift-container');
    const emptyState = document.getElementById('model-drift-empty');
    
    if (!modelDrift) {
        container.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    container.style.display = 'block';
    emptyState.style.display = 'none';
    
    document.getElementById('model-drift-score').textContent = modelDrift.drift_score.toFixed(4);
    document.getElementById('model-drift-threshold').textContent = modelDrift.alert_threshold.toFixed(4);
    
    const statusEl = document.getElementById('model-drift-status');
    if (modelDrift.alert_triggered) {
        statusEl.textContent = 'DRIFT DETECTED';
        statusEl.className = 'status-badge status-drift';
    } else {
        statusEl.textContent = 'NO DRIFT';
        statusEl.className = 'status-badge status-normal';
    }
}


// Switch tabs
function switchTab(tabName) {
    console.log('Switching to tab:', tabName);

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}-pane`).classList.add('active');
}

// Logout
function handleLogout() {
    sessionStorage.removeItem('session_token');
    window.location.href = '/login';
}
