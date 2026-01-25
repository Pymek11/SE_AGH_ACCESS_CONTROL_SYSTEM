document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Denials.js loaded');

    // Load denials data
    loadDenials();

    // Add sorting event listeners
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const column = this.getAttribute('data-column');
            sortDenials(column);
        });
    });
});

// Global variables for sorting and pagination
let denialsData = [];
let currentDenialSort = { column: null, direction: 'asc' };
let currentPage = 1;
const itemsPerPage = 8;

async function loadDenials() {
    try {
        const response = await fetch('/admin/api/failed-attempts', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();

        if (response.ok && data.failed_attempts) {
            denialsData = data.failed_attempts;
            currentPage = 1;
            renderDenials();
            updateCounts();
        }
    } catch (error) {
        console.error('Load denials error:', error);
    }
}

function updateCounts() {
    const totalCountEl = document.getElementById('totalDenialsCount');
    const recentCountEl = document.getElementById('recentDenialsCount');
    const badgeCountEl = document.getElementById('attemptCount');

    if (totalCountEl) totalCountEl.textContent = denialsData.length;

    // Filter for last 24 hours
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const recentDenials = denialsData.filter(attempt => {
        const attemptTime = new Date(attempt.created_at);
        return attemptTime >= oneDayAgo;
    });

    if (recentCountEl) recentCountEl.textContent = recentDenials.length;
    if (badgeCountEl) badgeCountEl.textContent = recentDenials.length;
}

function renderDenials() {
    const tbody = document.querySelector('#denialsTable tbody');

    if (denialsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No failed attempts found</td></tr>';
        return;
    }

    // Pagination
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedData = denialsData.slice(startIndex, endIndex);

    tbody.innerHTML = paginatedData.map(attempt => `
        <tr>
            <td>${attempt.id}</td>
            <td>${new Date(attempt.created_at).toLocaleString()}</td>
            <td>${attempt.qr_text || 'Unknown'}</td>
            <td><img src="data:image/jpeg;base64,${attempt.photo}" alt="Photo" style="max-width: 50px; max-height: 50px;"></td>
        </tr>
    `).join('');

    renderPagination();
}

function renderPagination() {
    const totalPages = Math.ceil(denialsData.length / itemsPerPage);
    let paginationHtml = '';

    if (totalPages > 1) {
        paginationHtml = `
            <nav aria-label="Denials table pagination">
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
    const totalPages = Math.ceil(denialsData.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderDenials();
}

function sortDenials(column) {
    if (currentDenialSort.column === column) {
        currentDenialSort.direction = currentDenialSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentDenialSort.column = column;
        currentDenialSort.direction = 'asc';
    }

    // Update sort icons
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
    });
    const activeTh = document.querySelector(`[data-column="${column}"]`);
    activeTh.classList.add(currentDenialSort.direction);

    // Sort data
    denialsData.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];

        if (column === 'id') {
            aVal = parseInt(aVal);
            bVal = parseInt(bVal);
        } else if (column === 'created_at') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }

        if (aVal < bVal) return currentDenialSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentDenialSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    currentPage = 1;
    renderDenials();
}