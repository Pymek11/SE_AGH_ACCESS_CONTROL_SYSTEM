document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOMContentLoaded fired');
    
    // Load users on page load
    loadUsers();
    
    // Handle capture button click
    document.addEventListener('click', async function(e) {
        if (e.target && e.target.id === 'captureUserBtn') {
            console.log('✅ Capture button clicked');
            e.preventDefault();
            
            const fullName = document.getElementById('fullName').value.trim();
            if (!fullName) {
                alert('Please enter a full name');
                return;
            }
            
            const btn = e.target;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Capturing...';
            
            try {
                const formData = new FormData();
                formData.append('fullName', fullName);
                
                const response = await fetch('/admin/face-capture', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Basic ' + sessionStorage.getItem('adminAuth')
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    const modalElement = document.getElementById('newUserModal');
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                        modal.hide();
                    }
                    document.getElementById('addUserForm').reset();
                    
                    // Reload users table
                    loadUsers();
                } else {
                    alert('Error: ' + (data.detail || 'Failed to capture face'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error capturing face: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-camera me-1"></i> Capture Face & Add User';
            }
        }
    });
});

// Load users from backend
async function loadUsers() {
    try {
        const response = await fetch('/admin/users', {
            headers: {
                'Authorization': 'Basic ' + sessionStorage.getItem('adminAuth')
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.users) {
            const tbody = document.querySelector('table tbody');
            
            if (!tbody) {
                console.error('Table tbody not found');
                return;
            }
            
            if (data.users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No users found</td></tr>';
                return;
            }
            
            // ✅ Użyj ikony zamiast obrazka
            tbody.innerHTML = data.users.map((user) => `
                <tr>
                    <td>${user.id}</td>
                    <td>${user.name}</td>
                    <td></td>
                    <td class="text-end">
                        <div class="d-flex justify-content-end">
                            <button class="btn btn-sm btn-warning me-2" onclick="editUser(${user.id})">
                                <i class="fas fa-edit me-1"></i> Edit
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id}, '${user.name}')">
                                <i class="fas fa-trash-alt me-1"></i> Delete
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');

            // Update employee count
            const countElement = document.getElementById('employeeCount');
            if (countElement) {
                countElement.textContent = data.users.length;
            }
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Delete user
async function deleteUser(userId, userName) {
    if (!confirm(`Are you sure you want to delete ${userName}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Basic ' + sessionStorage.getItem('adminAuth')
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message || 'User deleted successfully');
            loadUsers();
        } else {
            alert('Error: ' + (data.detail || 'Failed to delete user'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting user: ' + error.message);
    }
}

// Edit user (placeholder)
function editUser(userId) {
    alert('Edit functionality coming soon for user ID: ' + userId);
}