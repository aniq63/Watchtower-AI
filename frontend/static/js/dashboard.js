// Dashboard functionality

// Check authentication on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Check if user is authenticated
    if (!isAuthenticated()) {
        // Redirect to landing page if not authenticated
        window.location.href = '/';
        return;
    }
    
    // Load user information and projects
    await loadUserInfo();
    await loadApiKey();
    await loadProjects();
});

// Load user information
async function loadUserInfo() {
    try {
        const user = await getCurrentUser();
        
        if (!user) {
            // If user fetch fails, redirect to landing page
            console.error('Failed to fetch user information');
            window.location.href = '/';
            return;
        }
        
        // Update welcome message
        const welcomeMessage = document.getElementById('welcome-message');
        if (welcomeMessage) {
            welcomeMessage.textContent = `Welcome back, ${user.name}!`;
        }
        
        // Update header user name
        const headerUserName = document.getElementById('header-user-name');
        if (headerUserName) {
            headerUserName.textContent = user.name;
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Load API key
async function loadApiKey() {
    try {
        const user = await getCurrentUser();
        
        if (user && user.api_key) {
            // Show API key
            const apiKeyDisplay = document.getElementById('api-key-display');
            const apiKeyText = document.getElementById('api-key-text');
            const generateBtn = document.getElementById('generate-api-btn');
            
            if (apiKeyDisplay && apiKeyText) {
                apiKeyDisplay.style.display = 'block';
                apiKeyText.textContent = user.api_key;
                generateBtn.textContent = 'Regenerate API Key';
            }
        }
    } catch (error) {
        console.error('Error loading API key:', error);
    }
}

// Generate API key
async function generateApiKey() {
    const token = sessionStorage.getItem('session_token');
    const generateBtn = document.getElementById('generate-api-btn');
    
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    // Confirm regeneration if key already exists
    const apiKeyDisplay = document.getElementById('api-key-display');
    if (apiKeyDisplay.style.display === 'block') {
        if (!confirm('Are you sure you want to regenerate your API key? The old key will stop working.')) {
            return;
        }
    }
    
    // Add loading state
    generateBtn.classList.add('loading');
    generateBtn.disabled = true;
    
    try {
        const response = await fetch('/get_api/generate_api_key', {
            method: 'POST',
            headers: {
                'session_token': token
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Display API key
            const apiKeyDisplay = document.getElementById('api-key-display');
            const apiKeyText = document.getElementById('api-key-text');
            
            if (apiKeyDisplay && apiKeyText) {
                apiKeyDisplay.style.display = 'block';
                apiKeyText.textContent = data.api_key;
                generateBtn.textContent = 'Regenerate API Key';
                
                // Show success message
                showToast('API Key generated successfully!', 'success');
            }
        } else {
            showToast('Failed to generate API key', 'error');
        }
    } catch (error) {
        console.error('Error generating API key:', error);
        showToast('An error occurred', 'error');
    } finally {
        generateBtn.classList.remove('loading');
        generateBtn.disabled = false;
    }
}

// Copy API key to clipboard
async function copyApiKey() {
    const apiKeyText = document.getElementById('api-key-text');
    
    if (apiKeyText) {
        try {
            await navigator.clipboard.writeText(apiKeyText.textContent);
            showToast('API Key copied to clipboard!', 'success');
        } catch (error) {
            console.error('Failed to copy:', error);
            showToast('Failed to copy API key', 'error');
        }
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Hide and remove toast
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
