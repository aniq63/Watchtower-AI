// Project Detail Dashboard JavaScript
let currentProjectId = null;
let currentProjectType = null;
let toxicityChart = null;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', async () => {
    const token = sessionStorage.getItem('session_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Get project ID from hidden input
    currentProjectId = document.getElementById('project-id').value;

    // Load project details and overview
    await loadProjectDetails();
    await loadOverviewStats();

    // Load toxicity chart (only for LLM projects, handled in updateUIForProjectType usually, but we can leave it or move it)
    // We will move data loading triggers to updateUIForProjectType via switchTab
});

// Load project details
async function loadProjectDetails() {
    const token = sessionStorage.getItem('session_token');

    try {
        console.log('Loading project details for project:', currentProjectId);
        const response = await fetch(`/projects/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        console.log('Project details response status:', response.status);

        if (response.ok) {
            const project = await response.json();
            console.log('Project data:', project);
            document.getElementById('project-name').textContent = project.project_name;
            document.getElementById('project-description').textContent = project.project_description || 'No description provided';
            document.getElementById('config-project-name').value = project.project_name;
            document.getElementById('config-project-description').value = project.project_description || '';
            document.getElementById('config-access-token').textContent = project.access_token || 'No token available';

            // Store project type globally
            currentProjectType = project.project_type;

            // Apply UI filtering based on project type
            updateUIForProjectType(project.project_type);

        } else {
            console.error('Failed to load project details:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
        }
    } catch (error) {
        console.error('Error loading project details:', error);
    }
}

// Load overview statistics
async function loadOverviewStats() {
    const token = sessionStorage.getItem('session_token');

    try {
        console.log('Loading overview stats for project:', currentProjectId);
        const response = await fetch(`/projects/${currentProjectId}/overview`, {
            headers: { 'session_token': token }
        });

        console.log('Overview stats response status:', response.status);

        if (response.ok) {
            const data = await response.json();
            console.log('Overview data:', data);
            document.getElementById('total-data-points').textContent = data.total_data_points || 0;
            document.getElementById('drift-runs-count').textContent = data.drift_runs || 0;
            document.getElementById('quality-runs-count').textContent = data.quality_runs || 0;
            document.getElementById('llm-queries').textContent = data.llm_queries || 0;

            if (data.last_updated) {
                const date = new Date(data.last_updated);
                document.getElementById('last-updated').textContent = `Last updated: ${date.toLocaleString()}`;
            }

            document.getElementById('project-status').textContent = data.status === 'active' ? 'Active' : 'Inactive';
        } else {
            console.error('Failed to load overview stats:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
        }
    } catch (error) {
        console.error('Error loading overview stats:', error);
    }
}

// Load drift runs
async function loadDriftRuns() {
    const token = sessionStorage.getItem('session_token');
    const tbody = document.getElementById('drift-runs-body');

    try {
        console.log('Loading drift runs for project:', currentProjectId);
        const response = await fetch(`/projects/${currentProjectId}/drift-runs`, {
            headers: { 'session_token': token }
        });

        console.log('Drift runs response status:', response.status);

        if (response.ok) {
            const runs = await response.json();
            console.log('Drift runs data:', runs);

            if (runs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="empty-state">
                            No drift detection runs yet. Runs will appear here once data drift analysis is performed.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = runs.map(run => `
                <tr>
                    <td>${run.drift_id}</td>
                    <td>${run.baseline_window}</td>
                    <td>${run.current_window}</td>
                    <td>
                        <span class="badge ${run.overall_drift ? 'badge-error' : 'badge-success'}">
                            ${run.overall_drift ? 'Drift Detected' : 'No Drift'}
                        </span>
                    </td>
                    <td>${(run.drift_score * 100).toFixed(1)}%</td>
                    <td>${run.alerts_count}</td>
                    <td>${new Date(run.created_at).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewDriftDetails(${run.drift_id})">
                            View Details
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            console.error('Failed to load drift runs:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="error-state">
                        Error loading drift runs: ${response.status} ${response.statusText}
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading drift runs:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="error-state">
                    Error loading drift runs. Please check console for details.
                </td>
            </tr>
        `;
    }
}

// Load quality runs
async function loadQualityRuns() {
    const token = sessionStorage.getItem('session_token');
    const tbody = document.getElementById('quality-runs-body');

    try {
        const response = await fetch(`/projects/${currentProjectId}/quality-runs`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const runs = await response.json();

            if (runs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="empty-state">
                            No quality check runs yet. Runs will appear here once data quality checks are performed.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = runs.map(run => `
                <tr>
                    <td>${run.batch_number}</td>
                    <td>${run.feature_start_row || 'N/A'} - ${run.feature_end_row || 'N/A'} (${run.total_rows_checked})</td>
                    <td>${run.total_columns_checked}</td>
                    <td>${run.columns_with_missing}</td>
                    <td>${run.duplicate_percentage.toFixed(2)}%</td>
                    <td>
                        <span class="badge ${run.check_status === 'completed' ? 'badge-success' : 'badge-warning'}">
                            ${run.check_status}
                        </span>
                    </td>
                    <td>${new Date(run.check_timestamp).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewQualityDetails(${run.check_id})">
                            View Details
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading quality runs:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="error-state">
                    Error loading quality runs. Please try again.
                </td>
            </tr>
        `;
    }
}

// Load validation history
async function loadValidationHistory() {
    const token = sessionStorage.getItem('session_token');
    const tbody = document.getElementById('validation-history-body');

    try {
        const response = await fetch(`/feature/validation/history/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const data = await response.json();
            const records = data.results || [];

            if (records.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="empty-state">
                            No validation checks yet.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = records.map(record => `
                <tr>
                    <td>${record.batch_number}</td>
                    <td>
                        <span class="badge ${record.status === 'Valid' ? 'badge-success' : 'badge-error'}">
                            ${record.status}
                        </span>
                    </td>
                    <td>
                        <span class="status-indicator ${record.column_check === 'Passed' ? 'status-good' : 'status-bad'}">
                            ${record.column_check}
                        </span>
                    </td>
                    <td>
                        <span class="status-indicator ${record.type_check === 'Passed' ? 'status-good' : 'status-bad'}">
                            ${record.type_check}
                        </span>
                    </td>
                    <td>
                        <span class="status-indicator ${record.null_check === 'Passed' ? 'status-good' : 'status-bad'}">
                            ${record.null_check}
                        </span>
                    </td>
                    <td>${new Date(record.timestamp).toLocaleString()}</td>
                </tr>
            `).join('');
        } else {
            console.error('Failed to load validation history:', response.status);
            tbody.innerHTML = `<tr><td colspan="6" class="error-state">Error loading history: ${response.statusText}</td></tr>`;
        }
    } catch (error) {
        console.error('Error loading validation history:', error);
        tbody.innerHTML = `<tr><td colspan="6" class="error-state">Error loading history</td></tr>`;
    }
}

// Load LLM queries
async function loadLLMQueries() {
    const token = sessionStorage.getItem('session_token');
    const tbody = document.getElementById('llm-queries-body');

    try {
        const response = await fetch(`/projects/${currentProjectId}/llm-queries`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const queries = await response.json();

            if (queries.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="empty-state">
                            No LLM monitoring data yet. Queries will appear here once LLM responses are monitored.
                        </td>
                    </tr>
                `;
                return;
            }

            // Calculate metrics
            const totalQueries = queries.length;
            const avgToxicity = queries.reduce((sum, q) => sum + q.toxicity_score, 0) / totalQueries;
            const toxicCount = queries.filter(q => q.is_toxic).length;

            document.getElementById('total-queries-metric').textContent = totalQueries;
            document.getElementById('avg-toxicity').textContent = avgToxicity.toFixed(3);
            document.getElementById('toxic-count').textContent = toxicCount;

            tbody.innerHTML = queries.map(query => {
                const toxicityClass = query.toxicity_score > 0.6 ? 'toxicity-high' :
                    query.toxicity_score > 0.3 ? 'toxicity-medium' : 'toxicity-low';

                return `
                    <tr class="${query.is_toxic ? 'row-flagged' : ''}">
                        <td>${query.query_id}</td>
                        <td title="${query.input_text}">${query.input_text.substring(0, 100)}${query.input_text.length > 100 ? '...' : ''}</td>
                        <td title="${query.response_text}">${query.response_text.substring(0, 100)}${query.response_text.length > 100 ? '...' : ''}</td>
                        <td>
                            <span class="toxicity-score ${toxicityClass}">
                                ${query.toxicity_score.toFixed(3)}
                            </span>
                        </td>
                        <td>
                            <span class="badge ${query.is_toxic ? 'badge-error' : 'badge-success'}">
                                ${query.is_toxic ? 'Yes' : 'No'}
                            </span>
                        </td>
                        <td>${new Date(query.created_at).toLocaleString()}</td>
                    </tr>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading LLM queries:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="error-state">
                    Error loading LLM queries. Please try again.
                </td>
            </tr>
        `;
    }
}



// Tab switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load tab-specific data (lazy loading)
    if (tabName === 'drift' && !document.getElementById('drift-runs-body').dataset.loaded) {
        loadDriftRuns();
        document.getElementById('drift-runs-body').dataset.loaded = 'true';
    } else if (tabName === 'quality' && !document.getElementById('quality-runs-body').dataset.loaded) {
        loadQualityRuns();
        document.getElementById('quality-runs-body').dataset.loaded = 'true';
    } else if (tabName === 'validation' && !document.getElementById('validation-history-body').dataset.loaded) {
        loadValidationHistory();
        document.getElementById('validation-history-body').dataset.loaded = 'true';
    } else if (tabName === 'llm') {
        if (!document.getElementById('llm-queries-body').dataset.loaded) {
            loadLLMQueries();
            loadLLMDrift();
            document.getElementById('llm-queries-body').dataset.loaded = 'true';
        }
    } else if (tabName === 'prediction') {
        if (!document.getElementById('prediction-drift-body').dataset.loaded) {
            loadPredictionDrift();
            document.getElementById('prediction-drift-body').dataset.loaded = 'true';
        }
    } else if (tabName === 'config') {
        if (currentProjectType === 'llm_monitoring') {
            loadLLMConfig();
        } else if (currentProjectType === 'prediction_monitoring') {
            loadPredictionConfig();
            loadPredictionDriftConfig();
        } else {
            // Default to drift config for feature monitoring
            loadFeatureConfig();
            loadDriftConfig();
        }
    }
}

// Update UI based on project type
function updateUIForProjectType(projectType) {
    console.log('Updating UI for project type:', projectType);

    // UI Elements
    const elements = {
        drift: [
            document.getElementById('card-drift'),
            document.getElementById('card-quality'),
            document.getElementById('btn-tab-drift'),
            document.getElementById('btn-tab-quality'),
            document.getElementById('btn-tab-validation'),
            document.getElementById('section-feature-config'),
            document.getElementById('section-drift-config')
        ],
        llm: [
            document.getElementById('card-llm'),
            document.getElementById('btn-tab-llm'),
            document.getElementById('section-llm-config')
        ],
        prediction: [
            document.getElementById('btn-tab-prediction'),
            document.getElementById('section-prediction-config'),
            document.getElementById('section-prediction-drift-config')
        ],
    };

    // Helper to toggle visibility
    const setVisible = (els, visible) => {
        els.forEach(el => {
            if (el) el.style.display = visible ? '' : 'none';
        });
    };

    if (projectType === 'feature_monitoring') {
        setVisible(elements.drift, true);
        setVisible(elements.llm, false);
        setVisible(elements.prediction, false);
        switchTab('drift');

    } else if (projectType === 'llm_monitoring') {
        setVisible(elements.drift, false);
        setVisible(elements.llm, true);
        setVisible(elements.prediction, false);
        switchTab('llm');

    } else if (projectType === 'prediction_monitoring') {
        setVisible(elements.drift, false);
        setVisible(elements.llm, false);
        setVisible(elements.prediction, true);
        switchTab('prediction');
    } else {
        // Fallback
        console.warn('Unknown project type:', projectType);
        setVisible(elements.drift, true);
        switchTab('config');
    }
}

// Open config tab
function openConfigTab() {
    switchTab('config');
}

// Load feature config
async function loadFeatureConfig() {
    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/feature/config/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const data = await response.json();
            const config = data.config;
            if (config) {
                document.getElementById('config-feature-baseline-batch').value = config.baseline_batch_size;
                document.getElementById('config-feature-monitor-batch').value = config.monitor_batch_size;
            }
        }
    } catch (error) {
        console.error('Error loading feature config:', error);
    }
}

// Save feature config
async function saveFeatureConfig() {
    const token = sessionStorage.getItem('session_token');
    const statusEl = document.getElementById('feature-config-save-status');

    const configData = {
        baseline_batch_size: parseInt(document.getElementById('config-feature-baseline-batch').value) || 1000,
        monitor_batch_size: parseInt(document.getElementById('config-feature-monitor-batch').value) || 500
    };

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'save-status';

        const response = await fetch(`/feature/config/${currentProjectId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            statusEl.textContent = '✓ Saved';
            statusEl.className = 'save-status success';
            showToast('Feature configuration saved!');
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } else {
            statusEl.textContent = '✗ Failed';
            statusEl.className = 'save-status error';
        }
    } catch (error) {
        console.error('Error saving feature config:', error);
        statusEl.textContent = '✗ Error';
        statusEl.className = 'save-status error';
    }
}

// Load drift config
async function loadDriftConfig() {
    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/projects/${currentProjectId}/drift-config`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const config = await response.json();

            // Populate form fields
            document.getElementById('config-mean-threshold').value = config.mean_threshold;
            document.getElementById('config-median-threshold').value = config.median_threshold;
            document.getElementById('config-variance-threshold').value = config.variance_threshold;
            document.getElementById('config-ks-threshold').value = config.ks_pvalue_threshold;
            document.getElementById('config-alert-threshold').value = config.alert_threshold;
        }
    } catch (error) {
        console.error('Error loading drift config:', error);
    }
}

// Save drift config
async function saveDriftConfig() {
    const token = sessionStorage.getItem('session_token');
    const statusEl = document.getElementById('config-save-status');

    const configData = {
        mean_threshold: parseFloat(document.getElementById('config-mean-threshold').value) || 0.1,
        median_threshold: parseFloat(document.getElementById('config-median-threshold').value) || 0.1,
        variance_threshold: parseFloat(document.getElementById('config-variance-threshold').value) || 0.2,
        ks_pvalue_threshold: parseFloat(document.getElementById('config-ks-threshold').value) || 0.05,
        alert_threshold: parseInt(document.getElementById('config-alert-threshold').value) || 2
    };

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'save-status';

        const response = await fetch(`/projects/${currentProjectId}/drift-config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            statusEl.textContent = '✓ Saved';
            statusEl.className = 'save-status success';
            showToast('Drift configuration saved successfully!');
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } else {
            statusEl.textContent = '✗ Failed';
            statusEl.className = 'save-status error';
        }
    } catch (error) {
        console.error('Error saving drift config:', error);
        statusEl.textContent = '✗ Error';
        statusEl.className = 'save-status error';
    }
}

// Copy config token
function copyConfigToken() {
    const token = document.getElementById('config-access-token').textContent;
    navigator.clipboard.writeText(token).then(() => {
        showToast('Access token copied to clipboard!');
    });
}

// View drift details (drill-down)
function viewDriftDetails(driftId) {
    // TODO: Navigate to drift detail page or open modal
    window.location.href = `/project/${currentProjectId}/drift/${driftId}`;
}

// View quality details (drill-down)
function viewQualityDetails(checkId) {
    // TODO: Navigate to quality detail page or open modal
    window.location.href = `/project/${currentProjectId}/quality/${checkId}`;
}

// View LLM details (drill-down)
function viewLLMDetails(queryId) {
    // TODO: Navigate to LLM detail page or open modal
    window.location.href = `/project/${currentProjectId}/llm/${queryId}`;
}

// Show toast notification
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Load LLM config
async function loadLLMConfig() {
    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/llm/config/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const data = await response.json();
            const config = data.config;

            if (config) {
                // Populate form fields
                document.getElementById('config-llm-baseline-batch').value = config.baseline_batch_size;
                document.getElementById('config-llm-monitor-batch').value = config.monitor_batch_size;
                document.getElementById('config-llm-toxicity').value = config.toxicity_threshold;
                document.getElementById('config-llm-token-drift').value = config.token_drift_threshold;
            }
        }
    } catch (error) {
        console.error('Error loading LLM config:', error);
    }
}

// Load LLM Drift History
// Load LLM Drift History
async function loadLLMDrift() {
    const tbody = document.getElementById('llm-drift-body');
    const token = sessionStorage.getItem('session_token');

    try {
        const response = await fetch(`/llm/drift/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const data = await response.json();
            const drifts = data.drift_records;

            if (drifts.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">No drift history found</td></tr>`;
                return;
            }

            tbody.innerHTML = drifts.map(drift => {
                const isDrift = drift.has_drift;
                const statusClass = isDrift ? 'status-fail' : 'status-pass';
                const statusText = isDrift ? 'Drift Detected' : 'Stable';

                return `
                    <tr class="${isDrift ? 'row-flagged' : ''}">
                        <td>#${drift.id}</td>
                        <td>${drift.token_length_change ? drift.token_length_change.toFixed(3) : '0.000'}</td>
                        <td>${drift.baseline_avg_tokens ? drift.baseline_avg_tokens.toFixed(1) : 'N/A'}</td>
                        <td>${drift.monitor_avg_tokens ? drift.monitor_avg_tokens.toFixed(1) : 'N/A'}</td>
                        <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                        <td>${formatDate(drift.created_at)}</td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="6" class="error-cell">Failed to load drift history</td></tr>`;
        }
    } catch (error) {
        console.error('Error loading LLM drift:', error);
        tbody.innerHTML = `<tr><td colspan="6" class="error-cell">Error loading data</td></tr>`;
    }
}

// Save LLM config
async function saveLLMConfig() {
    const token = sessionStorage.getItem('session_token');
    const statusEl = document.getElementById('llm-config-save-status');

    const configData = {
        baseline_batch_size: parseInt(document.getElementById('config-llm-baseline-batch').value) || 500,
        monitor_batch_size: parseInt(document.getElementById('config-llm-monitor-batch').value) || 250,
        toxicity_threshold: parseFloat(document.getElementById('config-llm-toxicity').value) || 0.5,
        token_drift_threshold: parseFloat(document.getElementById('config-llm-token-drift').value) || 0.15
    };

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'save-status';

        const response = await fetch(`/llm/config/${currentProjectId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            statusEl.textContent = '✓ Saved';
            statusEl.className = 'save-status success';
            showToast('LLM configuration saved successfully!');
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } else {
            statusEl.textContent = '✗ Failed';
            statusEl.className = 'save-status error';
            showToast('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving LLM config:', error);
        statusEl.textContent = '✗ Error';
        statusEl.className = 'save-status error';
        showToast('An error occurred', 'error');
    }
}

// ==========================================
// Prediction Monitoring Functions
// ==========================================

async function loadPredictionDrift() {
    const token = sessionStorage.getItem('session_token');
    const tbody = document.getElementById('prediction-drift-body');

    try {
        const response = await fetch(`/prediction/drift/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const data = await response.json();
            const records = data.results || [];

            if (records.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="empty-state">
                            No prediction drift runs yet.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = records.map(run => `
                <tr>
                    <td>${run.drift_id}</td>
                    <td>${run.window_start} - ${run.window_end}</td>
                    <td>
                        <span class="badge ${run.is_drift ? 'badge-error' : 'badge-success'}">
                            ${run.is_drift ? 'Drift Detected' : 'No Drift'}
                        </span>
                    </td>
                    <td>${new Date(run.timestamp).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary">Details</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading prediction drift:', error);
        tbody.innerHTML = `<tr><td colspan="5" class="error-state">Error loading data</td></tr>`;
    }
}

async function loadPredictionConfig() {
    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/prediction/config/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const config = await response.json();
            if (config) {
                document.getElementById('config-pred-baseline-batch').value = config.baseline_batch_size;
                document.getElementById('config-pred-monitor-batch').value = config.monitor_batch_size;
            }
        }
    } catch (error) {
        console.error('Error loading prediction config:', error);
    }
}

// Save Prediction config (batch sizes)
async function savePredictionConfig() {
    const token = sessionStorage.getItem('session_token');
    const statusEl = document.getElementById('prediction-config-save-status');

    const configData = {
        baseline_batch_size: parseInt(document.getElementById('config-pred-baseline-batch').value) || 1000,
        monitor_batch_size: parseInt(document.getElementById('config-pred-monitor-batch').value) || 500
    };

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'save-status';

        const response = await fetch(`/prediction/config/${currentProjectId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            statusEl.textContent = '✓ Saved';
            statusEl.className = 'save-status success';
            showToast('Prediction configuration saved successfully!');
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } else {
            statusEl.textContent = '✗ Failed';
            statusEl.className = 'save-status error';
        }
    } catch (error) {
        console.error('Error saving prediction config:', error);
        statusEl.textContent = '✗ Error';
        statusEl.className = 'save-status error';
    }
}

async function loadPredictionDriftConfig() {
    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/prediction/drift-config/${currentProjectId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            const config = await response.json();
            if (config) {
                document.getElementById('config-pred-mean-threshold').value = config.mean_threshold;
                document.getElementById('config-pred-median-threshold').value = config.median_threshold;
                document.getElementById('config-pred-variance-threshold').value = config.variance_threshold;
                document.getElementById('config-pred-ks-threshold').value = config.ks_pvalue_threshold;
            }
        }
    } catch (error) {
        console.error('Error loading prediction drift config:', error);
    }
}

async function savePredictionDriftConfig() {
    const token = sessionStorage.getItem('session_token');
    const statusEl = document.getElementById('prediction-drift-save-status');

    const configData = {
        mean_threshold: parseFloat(document.getElementById('config-pred-mean-threshold').value) || 0.1,
        median_threshold: parseFloat(document.getElementById('config-pred-median-threshold').value) || 0.1,
        variance_threshold: parseFloat(document.getElementById('config-pred-variance-threshold').value) || 0.2,
        ks_pvalue_threshold: parseFloat(document.getElementById('config-pred-ks-threshold').value) || 0.05
    };

    try {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'save-status';

        const response = await fetch(`/prediction/drift-config/${currentProjectId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            statusEl.textContent = '✓ Saved';
            statusEl.className = 'save-status success';
            showToast('Drift configuration saved!');
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } else {
            statusEl.textContent = '✗ Failed';
            statusEl.className = 'save-status error';
        }
    } catch (error) {
        console.error('Error saving prediction drift config:', error);
        statusEl.textContent = '✗ Error';
        statusEl.className = 'save-status error';
    }
}

// Logout handler
function handleLogout() {
    sessionStorage.removeItem('session_token');
    window.location.href = '/login';
}

async function deleteCurrentProject() {
    if (!confirm('Are you sure you want to delete this project? This process will delete all data including feature records, drift history, and configurations. This action cannot be undone.')) {
        return;
    }

    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/projects/${currentProjectId}`, {
            method: 'DELETE',
            headers: {
                'session_token': token
            }
        });

        if (response.ok) {
            showToast('Project deleted successfully', 'success');
            // Redirect to dashboard after a short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            const data = await response.json();
            showToast(data.detail || 'Failed to delete project', 'error');
        }
    } catch (error) {
        console.error('Error deleting project:', error);
        showToast('An error occurred while deleting project', 'error');
    }
}

// Utility function to format dates
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
}
