// Authentication API integration

// Sign In Handler
async function handleSignIn(event) {
    event.preventDefault();

    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const username = form.querySelector('#signin-username').value;
    const password = form.querySelector('#signin-password').value;

    // Clear previous errors
    clearError('signin');

    // Add loading state
    submitButton.classList.add('loading');
    submitButton.disabled = true;

    try {
        const response = await fetch('/User-Authentication/company_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Store session token
            sessionStorage.setItem('session_token', data.access_token);
            console.log('Login successful, token stored:', data.access_token.substring(0, 10) + '...');

            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            // Show error message
            showError('signin', data.detail || 'Invalid credentials. Please try again.');
        }
    } catch (error) {
        console.error('Sign in error:', error);
        showError('signin', 'An error occurred. Please try again.');
    } finally {
        // Remove loading state
        submitButton.classList.remove('loading');
        submitButton.disabled = false;
    }
}

// Sign Up Handler
async function handleSignUp(event) {
    event.preventDefault();

    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const name = form.querySelector('#signup-name').value;
    const email = form.querySelector('#signup-email').value;
    const companyName = form.querySelector('#signup-company').value;
    const password = form.querySelector('#signup-password').value;

    // Clear previous errors
    clearError('signup');

    // Validate password length
    if (password.length < 6) {
        showError('signup', 'Password must be at least 6 characters long.');
        return;
    }

    // Add loading state
    submitButton.classList.add('loading');
    submitButton.disabled = true;

    try {
        const response = await fetch('/User-Authentication/register_company', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                email: email,
                company_name: companyName,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Registration successful, now auto-login
            await autoLogin(name, password);
        } else {
            // Show error message
            showError('signup', data.detail || 'Registration failed. Please try again.');
        }
    } catch (error) {
        console.error('Sign up error:', error);
        showError('signup', 'An error occurred. Please try again.');
    } finally {
        // Remove loading state
        submitButton.classList.remove('loading');
        submitButton.disabled = false;
    }
}

// Auto-login after successful registration
async function autoLogin(username, password) {
    try {
        const response = await fetch('/User-Authentication/company_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Store session token
            sessionStorage.setItem('session_token', data.access_token);
            console.log('Auto-login successful, token stored');

            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            // If auto-login fails, show success message and switch to sign in
            showError('signup', 'Account created! Please sign in.');
            setTimeout(() => {
                switchToSignIn(new Event('click'));
            }, 2000);
        }
    } catch (error) {
        console.error('Auto-login error:', error);
        showError('signup', 'Account created! Please sign in.');
        setTimeout(() => {
            switchToSignIn(new Event('click'));
        }, 2000);
    }
}

// Logout Handler
async function handleLogout() {
    const token = sessionStorage.getItem('session_token');

    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        await fetch('/User-Authentication/logout_company', {
            method: 'POST',
            headers: {
                'session_token': token
            }
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear session token
        sessionStorage.removeItem('session_token');

        // Redirect to landing page
        window.location.href = '/';
    }
}

// Check if user is authenticated
function isAuthenticated() {
    const token = sessionStorage.getItem('session_token');
    console.log('Checking authentication, token exists:', !!token);
    return token !== null;
}

// Get current user
async function getCurrentUser() {
    const token = sessionStorage.getItem('session_token');

    if (!token) {
        console.log('No session token found');
        return null;
    }

    console.log('Fetching current user with token:', token.substring(0, 10) + '...');

    try {
        const response = await fetch('/User-Authentication/me', {
            method: 'GET',
            headers: {
                'session_token': token
            }
        });

        console.log('User fetch response status:', response.status);

        if (response.ok) {
            const userData = await response.json();
            console.log('User data fetched successfully:', userData.name);
            return userData;
        } else {
            // Token is invalid, clear it
            console.error('Invalid session token, status:', response.status);
            const errorData = await response.json().catch(() => ({}));
            console.error('Error details:', errorData);
            sessionStorage.removeItem('session_token');
            return null;
        }
    } catch (error) {
        console.error('Get current user error:', error);
        // Don't clear token on network error, might be temporary
        return null;
    }
}
