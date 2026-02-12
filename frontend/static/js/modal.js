// Modal functionality
function openAuthModal(mode) {
    const modal = document.getElementById('authModal');
    modal.classList.add('active');
    
    if (mode === 'signin') {
        showSignIn();
    } else if (mode === 'signup') {
        showSignUp();
    }
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    modal.classList.remove('active');
    
    // Clear error messages
    clearError('signin');
    clearError('signup');
    
    // Re-enable body scroll
    document.body.style.overflow = 'auto';
}

function showSignIn() {
    document.getElementById('signinForm').style.display = 'block';
    document.getElementById('signupForm').style.display = 'none';
    clearError('signin');
    clearError('signup');
}

function showSignUp() {
    document.getElementById('signinForm').style.display = 'none';
    document.getElementById('signupForm').style.display = 'block';
    clearError('signin');
    clearError('signup');
}

function switchToSignUp(event) {
    event.preventDefault();
    showSignUp();
}

function switchToSignIn(event) {
    event.preventDefault();
    showSignIn();
}

function clearError(formType) {
    const errorElement = document.getElementById(`${formType}-error`);
    if (errorElement) {
        errorElement.classList.remove('active');
        errorElement.textContent = '';
    }
}

function showError(formType, message) {
    const errorElement = document.getElementById(`${formType}-error`);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('active');
    }
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeAuthModal();
            }
        });
    }
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.classList.contains('active')) {
            closeAuthModal();
        }
    });
});
