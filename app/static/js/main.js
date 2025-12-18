document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOMContentLoaded fired');
    
    // Load users on page load
    loadUsers();
    
    // Face photo preview
    document.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'facePhoto') {
            console.log('✅ Face photo selected');
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const previewImg = document.getElementById('facePreviewImg');
                    const preview = document.getElementById('facePreview');
                    if (previewImg && preview) {
                        previewImg.src = event.target.result;
                        preview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        }
    });
    
    // Form submission - użyj event.submitter zamiast querySelector
    document.addEventListener('submit', async function(e) {
        console.log('✅ Submit event fired on:', e.target);
        
        if (e.target && e.target.id === 'addUserForm') {
            console.log('✅ Form matched: addUserForm');
            e.preventDefault();
            
            const form = e.target;
            const formData = new FormData(form);
            
            // ✅ Użyj e.submitter (przycisk który wywołał submit)
            const submitBtn = e.submitter || document.getElementById('submitUserBtn');
            
            console.log('Submit button:', submitBtn);
            console.log('Form data:', Array.from(formData.entries()));
            
            if (!submitBtn) {
                console.error('❌ Submit button not found');
                // Ale kontynuuj wysyłanie!
            }
            
            // Disable button during submission
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
            }
            
            try {
                const response = await fetch('/admin/users', {
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
                    form.reset();
                    const facePreview = document.getElementById('facePreview');
                    if (facePreview) {
                        facePreview.style.display = 'none';
                    }
                    
                    // Reload users table
                    loadUsers();
                } else {
                    alert('Error: ' + (data.detail || 'Failed to add user'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error adding user: ' + error.message);
            } finally {
                // Re-enable button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save User';
                }
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
                    <td>
                        <div class="bg-secondary rounded-circle d-inline-flex align-items-center justify-content-center" style="width:40px;height:40px;">
                            <i class="fas fa-user text-white"></i>
                        </div>
                    </td>
                    <td>${user.name}</td>
                    <td>
                        <button class="btn btn-sm btn-warning me-2" onclick="editUser(${user.id})">
                            <i class="fas fa-edit me-1"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id}, '${user.name}')">
                            <i class="fas fa-trash-alt me-1"></i> Delete
                        </button>
                    </td>
                </tr>
            `).join('');
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