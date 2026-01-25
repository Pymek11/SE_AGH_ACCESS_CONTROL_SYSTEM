document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Main.js loaded');
    
    // Załaduj listę użytkowników na starcie
    loadUsers();
    
    // Load successful access count
    loadSuccessfulAccessCount();
    
    // Add sorting event listeners
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const column = this.getAttribute('data-column');
            sortUsers(column);
        });
    });
    
    // Załaduj listę nieudanych prób na starcie
    loadAttempts();
    
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

// Global variables for sorting and pagination
let usersData = [];
let currentUserSort = { column: null, direction: 'asc' };
let currentPage = 1;
const itemsPerPage = 8;

async function loadUsers() {
    try {
        const response = await fetch('/admin/users', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();
        
        if (response.ok && data.users) {
            usersData = data.users;
            currentPage = 1;
            renderUsers();
        }
    } catch (error) {
        console.error('Load users error:', error);
    }
}

function renderUsers() {
    const tbody = document.getElementById('users-tbody');
    const countEl = document.getElementById('employeeCount');
    
    if (countEl) countEl.textContent = usersData.length;

    if (usersData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No users found</td></tr>';
        return;
    }

    // Pagination
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedData = usersData.slice(startIndex, endIndex);

    tbody.innerHTML = paginatedData.map(user => `
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

    renderPagination();
}

function renderPagination() {
    const totalPages = Math.ceil(usersData.length / itemsPerPage);
    let paginationHtml = '';

    if (totalPages > 1) {
        paginationHtml = `
            <nav aria-label="User table pagination">
                <ul class="pagination justify-content-center mt-3">
                    <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">
                            <i class="fas fa-chevron-left"></i>
                        </a>
                    </li>`;

        for (let i = 1; i <= totalPages; i++) {
            paginationHtml += `
                    <li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                    </li>`;
        }

        paginationHtml += `
                    <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">
                            <i class="fas fa-chevron-right"></i>
                        </a>
                    </li>
                </ul>
            </nav>`;
    }

    // Insert after the table
    const tableContainer = document.querySelector('.table-responsive');
    let paginationEl = tableContainer.querySelector('.pagination-nav');
    if (!paginationEl) {
        paginationEl = document.createElement('div');
        paginationEl.className = 'pagination-nav';
        tableContainer.appendChild(paginationEl);
    }
    paginationEl.innerHTML = paginationHtml;
}

function changePage(page) {
    const totalPages = Math.ceil(usersData.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderUsers();
}

function sortUsers(column) {
    if (currentUserSort.column === column) {
        currentUserSort.direction = currentUserSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentUserSort.column = column;
        currentUserSort.direction = 'asc';
    }

    // Update sort icons
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
    });
    const activeTh = document.querySelector(`[data-column="${column}"]`);
    activeTh.classList.add(currentUserSort.direction);

    // Sort data
    usersData.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];

        if (column === 'id') {
            aVal = parseInt(aVal);
            bVal = parseInt(bVal);
        }

        if (aVal < bVal) return currentUserSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentUserSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    currentPage = 1;
    renderUsers();
}

async function loadAttempts() {
    try {
        const response = await fetch('/admin/api/failed-attempts', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();
        
        if (response.ok && data.failed_attempts) {
            const tbody = document.querySelector('#attemptsTable tbody');
            const countEl = document.getElementById('attemptCount');
            const cardCountEl = document.getElementById('failedAttemptsCount');
            
            // Filter attempts from last 24 hours
            //const now = new Date();
            //const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            
            const last24hAttempts = data.failed_attempts.filter(attempt => {
                const attemptTime = new Date(attempt.created_at);
                return attemptTime
            });
            
            // Update both counters
            if (countEl) countEl.textContent = last24hAttempts.length;
            if (cardCountEl) cardCountEl.textContent = last24hAttempts.length;

            if (last24hAttempts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No failed attempts in the last 24 hours</td></tr>';
                return;
            }

            tbody.innerHTML = last24hAttempts.map(attempt => `
                <tr>
                    <td>${attempt.id}</td>
                    <td>${new Date(attempt.created_at).toLocaleString()}</td>
                    <td>${attempt.qr_text || 'Unknown'}</td>
                    <td><img src="data:image/jpeg;base64,${attempt.photo}" alt="Photo" style="max-width: 50px; max-height: 50px;"></td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Load attempts error:', error);
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

async function loadSuccessfulAccessCount() {
    try {
        const response = await fetch('/admin/api/good-entries', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();

        if (response.ok && data.good_entries) {
            const countEl = document.getElementById('successfulAccessCount');
            if (countEl) countEl.textContent = data.good_entries.length;
        }
    } catch (error) {
        console.error('Load successful access count error:', error);
    }
}