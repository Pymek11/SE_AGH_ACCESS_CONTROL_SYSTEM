 document.getElementById('facePhoto').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                document.getElementById('facePreviewImg').src = event.target.result;
                document.getElementById('facePreview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
    
    document.getElementById('qrPhoto').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                document.getElementById('qrPreviewImg').src = event.target.result;
                document.getElementById('qrPreview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Form submission (you'll need to add backend endpoint later)
    document.getElementById('addUserForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        try {
            const response = await fetch('/admin/users', {
                method: 'POST',
                headers: {
                    'Authorization': 'Basic ' + sessionStorage.getItem('adminAuth')
                },
                body: formData
            });
            
            if (response.ok) {
                alert('User added successfully!');
                bootstrap.Modal.getInstance(document.getElementById('newUserModal')).hide();
                this.reset();
                document.getElementById('facePreview').style.display = 'none';
                document.getElementById('qrPreview').style.display = 'none';
                // TODO: Reload users table
            } else {
                alert('Error adding user');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error adding user');
        }
    });