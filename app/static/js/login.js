// Toggle password visibility
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.querySelector('.toggle-password i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
    }
}

// Form validation and submission
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('loginForm').addEventListener('submit', function (e) {
        e.preventDefault();

        // Clear previous messages
        document.getElementById('generalError').style.display = 'none';
        document.getElementById('generalSuccess').style.display = 'none';
        document.getElementById('usernameError').style.display = 'none';
        document.getElementById('passwordError').style.display = 'none';

        // Get form values
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        // Validation
        let hasError = false;

        if (!username) {
            document.getElementById('usernameError').textContent = 'Username is required';
            document.getElementById('usernameError').style.display = 'block';
            hasError = true;
        }

        if (!password) {
            document.getElementById('passwordError').textContent = 'Password is required';
            document.getElementById('passwordError').style.display = 'block';
            hasError = true;
        }

        if (password.length < 6 && password) {
            document.getElementById('passwordError').textContent = 'Password must be at least 6 characters';
            document.getElementById('passwordError').style.display = 'block';
            hasError = true;
        }

        if (!hasError) {
            // Check for admin credentials
            if (username === 'admin' && password === 'admin1') {
                // Admin login
                const credentials = btoa(`${username}:${password}`);
                sessionStorage.setItem('adminAuth', credentials);

                document.getElementById('generalSuccess').textContent = 'Admin login successful! Redirecting...';
                document.getElementById('generalSuccess').style.display = 'block';

                setTimeout(function () {
                    window.location.href = '/admin/dashboard';
                }, 1000);
            } else {
                // Regular user login (not implemented yet)
                document.getElementById('generalError').textContent = 'Invalid credentials. Only admin login is available.';
                document.getElementById('generalError').style.display = 'block';
            }
        }
    });
});