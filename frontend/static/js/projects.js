// Projects management functionality

// Load all projects
async function loadProjects() {
    const token = sessionStorage.getItem('session_token');
    const projectsGrid = document.getElementById('projects-grid');

    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch('/projects/', {
            headers: {
                'session_token': token
            }
        });

        if (response.ok) {
            const projects = await response.json();
            displayProjects(projects);
        } else {
            projectsGrid.innerHTML = '<p class="error-text">Failed to load projects</p>';
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        projectsGrid.innerHTML = '<p class="error-text">An error occurred while loading projects</p>';
    }
}

// Display projects in grid
function displayProjects(projects) {
    const projectsGrid = document.getElementById('projects-grid');

    if (projects.length === 0) {
        projectsGrid.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M9 11l3 3L22 4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <h3>No Projects Yet</h3>
                <p>Create your first project to start monitoring your ML models</p>
                <button class="btn btn-primary" onclick="openCreateProjectModal()">Create Project</button>
            </div>
        `;
        return;
    }

    projectsGrid.innerHTML = projects.map(project => `
        <div class="project-card" onclick="viewProject(${project.project_id})">
            <div class="project-header">
                <h3>${escapeHtml(project.project_name)}</h3>
                <button class="btn-delete" onclick="deleteProject(${project.project_id}, event)" title="Delete Project">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
            <p class="project-description">${escapeHtml(project.project_description)}</p>
            <div class="project-meta">
                <span class="project-date">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="10" stroke-width="2"/>
                        <path d="M12 6v6l4 2" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                    ${formatDate(project.created_at)}
                </span>
            </div>
        </div>
    `).join('');
}

// Delete project
async function deleteProject(projectId, event) {
    event.stopPropagation(); // Prevent card click

    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
        return;
    }

    const token = sessionStorage.getItem('session_token');
    try {
        const response = await fetch(`/projects/${projectId}`, {
            method: 'DELETE',
            headers: {
                'session_token': token
            }
        });

        if (response.ok) {
            showToast('Project deleted successfully', 'success');
            loadProjects(); // Reload list
        } else {
            const data = await response.json();
            showToast(data.detail || 'Failed to delete project', 'error');
        }
    } catch (error) {
        console.error('Error deleting project:', error);
        showToast('An error occurred while deleting project', 'error');
    }
}

// Copy project token
async function copyToken(token) {
    try {
        await navigator.clipboard.writeText(token);
        showToast('Access token copied to clipboard!', 'success');
    } catch (error) {
        console.error('Failed to copy:', error);
        showToast('Failed to copy token', 'error');
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Open create project modal
function openCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Clear form
    document.getElementById('project-name').value = '';
    document.getElementById('project-description').value = '';
    clearProjectError();
}

// Close create project modal
function closeCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
    clearProjectError();
}

// Clear project error
function clearProjectError() {
    const errorElement = document.getElementById('create-project-error');
    if (errorElement) {
        errorElement.classList.remove('active');
        errorElement.textContent = '';
    }
}

// Show project error
function showProjectError(message) {
    const errorElement = document.getElementById('create-project-error');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('active');
    }
}

// Handle create project
async function handleCreateProject(event) {
    event.preventDefault();

    const token = sessionStorage.getItem('session_token');
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const projectName = form.querySelector('#project-name').value;
    const projectDescription = form.querySelector('#project-description').value;
    const projectType = form.querySelector('#project-type').value;

    if (!token) {
        window.location.href = '/';
        return;
    }

    // Clear previous errors
    clearProjectError();

    // Add loading state
    submitButton.classList.add('loading');
    submitButton.disabled = true;

    try {
        const response = await fetch('/projects/create_project', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'session_token': token
            },
            body: JSON.stringify({
                project_name: projectName,
                project_description: projectDescription,
                project_type: projectType,
                created_at: new Date().toISOString()
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Close modal
            closeCreateProjectModal();

            // Show success message
            showToast('Project created successfully!', 'success');

            // Reload projects
            await loadProjects();
        } else {
            // Show error message
            showProjectError(data.detail || 'Failed to create project');
        }
    } catch (error) {
        console.error('Error creating project:', error);
        showProjectError('An error occurred. Please try again.');
    } finally {
        // Remove loading state
        submitButton.classList.remove('loading');
        submitButton.disabled = false;
    }
}

// View project details
function viewProject(projectId) {
    window.location.href = `/project/${projectId}`;
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('createProjectModal');
    if (modal) {
        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                closeCreateProjectModal();
            }
        });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('active')) {
            closeCreateProjectModal();
        }
    });
});
