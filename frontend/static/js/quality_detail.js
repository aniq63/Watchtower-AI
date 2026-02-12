// Quality Detail Page JavaScript

let qualityData = null;
const projectId = document.getElementById('project-id')?.value;
const checkId = document.getElementById('check-id')?.value;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', async () => {
    const token = sessionStorage.getItem('session_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Load quality check details
    await loadQualityCheck();
});

// Load quality check details
async function loadQualityCheck() {
    const token = sessionStorage.getItem('session_token');

    try {
        const response = await fetch(`/data-quality/check/${checkId}`, {
            headers: { 'session_token': token }
        });

        if (response.ok) {
            qualityData = await response.json();
            console.log('Quality data loaded:', qualityData);
            renderQualityDetails();
        } else {
            console.error('Failed to load quality check');
            document.getElementById('missing-values-body').innerHTML =
                '<tr><td colspan="4" class="error-cell">Failed to load quality check data</td></tr>';
        }
    } catch (error) {
        console.error('Error loading quality check:', error);
        document.getElementById('missing-values-body').innerHTML =
            '<tr><td colspan="4" class="error-cell">Error loading data</td></tr>';
    }
}

// Render quality details
function renderQualityDetails() {
    if (!qualityData) return;

    // Update overview cards
    document.getElementById('batch-number').textContent = qualityData.batch_number || '--';
    document.getElementById('check-timestamp').textContent =
        qualityData.check_timestamp ? new Date(qualityData.check_timestamp).toLocaleString() : '--';
    document.getElementById('total-rows').textContent = qualityData.total_rows_checked?.toLocaleString() || '0';
    document.getElementById('total-columns').textContent = qualityData.total_columns_checked || '0';
    document.getElementById('columns-with-missing').textContent = qualityData.columns_with_missing || '0';
    document.getElementById('duplicate-percentage').textContent =
        (qualityData.duplicate_percentage || 0).toFixed(2) + '%';

    // Update duplicate info section
    document.getElementById('total-duplicates').textContent =
        qualityData.total_duplicate_rows?.toLocaleString() || '0';
    document.getElementById('duplicate-percent-detail').textContent =
        (qualityData.duplicate_percentage || 0).toFixed(2) + '%';

    // Render missing values table
    renderMissingValuesTable();
}

// Render missing values table
function renderMissingValuesTable() {
    const tbody = document.getElementById('missing-values-body');
    const missingValues = qualityData.missing_values_summary || {};

    if (Object.keys(missingValues).length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">No missing values data available</td></tr>';
        return;
    }

    const rows = [];
    for (const [column, data] of Object.entries(missingValues)) {
        const count = data.count || 0;
        const percentage = data.percentage || 0;
        const status = percentage > 10 ? 'high' : percentage > 5 ? 'medium' : 'low';

        rows.push(`
            <tr class="${status === 'high' ? 'row-warning' : ''}">
                <td><strong>${column}</strong></td>
                <td>${count.toLocaleString()}</td>
                <td>${percentage.toFixed(2)}%</td>
                <td>
                    <span class="status-badge ${status === 'high' ? 'status-fail' : status === 'medium' ? 'status-warning' : 'status-pass'}">
                        ${status === 'high' ? '⚠️ High' : status === 'medium' ? '⚡ Moderate' : '✓ Low'}
                    </span>
                </td>
            </tr>
        `);
    }

    tbody.innerHTML = rows.length > 0 ? rows.join('') :
        '<tr><td colspan="4" class="empty-cell">No missing values detected</td></tr>';
}

// Logout handler
function handleLogout() {
    sessionStorage.removeItem('session_token');
    window.location.href = '/';
}
