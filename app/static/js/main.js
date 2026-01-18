document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Main.js loaded');
    
    // Załaduj listę użytkowników na starcie
    loadUsers();
    
    // --- OBSŁUGA PRZEŁĄCZNIKA (PLIK / KAMERA) ---
    const radioFile = document.getElementById('methodFile');
    const radioCamera = document.getElementById('methodCamera');
    const sectionFile = document.getElementById('sectionFile');
    const sectionCamera = document.getElementById('sectionCamera');

    function toggleMethod() {
        if (radioFile.checked) {
            sectionFile.classList.remove('d-none');
            sectionCamera.classList.add('d-none');
        } else {
            sectionFile.classList.add('d-none');
            sectionCamera.classList.remove('d-none');
        }
    }

    if(radioFile && radioCamera) {
        radioFile.addEventListener('change', toggleMethod);
        radioCamera.addEventListener('change', toggleMethod);
    }

    // --- OBSŁUGA PRZYCISKU SAVE ---
    const saveBtn = document.getElementById('saveUserBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            // 1. Walidacja Imienia
            const fullNameInput = document.getElementById('fullName');
            const fullName = fullNameInput.value.trim();
            
            if (!fullName) {
                alert('Please enter a full name');
                fullNameInput.focus();
                return;
            }

            // 2. Blokada przycisku
            const originalBtnText = saveBtn.innerHTML;
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processing...';

            try {
                const formData = new FormData();
                formData.append('fullName', fullName);

                let url = '';
                
                // 3. Sprawdzenie wybranej metody
                if (radioFile.checked) {
                    // --- METODA: PLIK ---
                    const fileInput = document.getElementById('facePhoto');
                    if (fileInput.files.length === 0) {
                        throw new Error("Please select a photo file.");
                    }
                    formData.append('facePhoto', fileInput.files[0]);
                    url = '/admin/users'; // Endpoint do uploadu
                } else {
                    // --- METODA: KAMERA ---
                    // Tutaj nie wysyłamy pliku, backend sam weźmie klatkę z kamery
                    url = '/admin/face-capture'; // Endpoint do capture
                }

                // 4. Wysłanie żądania
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        // Basic Auth pobieramy z sesji (zakładając, że logowanie go tam zapisało)
                        // Jeśli nie masz logowania, usuń headers 'Authorization'
                        'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
                    },
                    body: formData 
                });

                const data = await response.json();

                if (response.ok) {
                    alert('✅ Success: ' + (data.message || 'User added!'));
                    
                    // Zamknij modal
                    const modalEl = document.getElementById('newUserModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    
                    // Reset formularza
                    document.getElementById('addUserForm').reset();
                    // Przywrócenie domyślnego widoku (plik)
                    radioFile.checked = true;
                    toggleMethod();
                    
                    // Odśwież tabelę
                    loadUsers();
                } else {
                    throw new Error(data.detail || 'Unknown server error');
                }

            } catch (error) {
                console.error('Error:', error);
                alert('❌ Error: ' + error.message);
            } finally {
                // Przywrócenie przycisku
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalBtnText;
            }
        });
    }
});

async function loadUsers() {
    try {
        const response = await fetch('/admin/users', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();
        
        if (response.ok && data.users) {
            const tbody = document.querySelector('table tbody');
            const countEl = document.getElementById('employeeCount');
            
            if (countEl) countEl.textContent = data.users.length;

            if (data.users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No users found</td></tr>';
                return;
            }

            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${user.id}</td>
                    <td>${user.name}</td>
                    <td><i class="fas fa-check-circle text-success"></i> Active</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id}, '${user.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Load users error:', error);
    }
}

async function deleteUser(id, name) {
    if(!confirm(`Delete user ${name}?`)) return;
    
    try {
        const response = await fetch(`/admin/users/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        if(response.ok) {
            loadUsers();
        } else {
            alert("Failed to delete");
        }
    } catch(e) {
        console.error(e);
    }
}