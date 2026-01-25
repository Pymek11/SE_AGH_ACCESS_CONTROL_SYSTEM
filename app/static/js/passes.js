document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Passes.js loaded');

    // Load passes data
    loadPasses();

    // Add sorting event listeners
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const column = this.getAttribute('data-column');
            sortPasses(column);
        });
    });
});

// Global variables for sorting and pagination
let passesData = [];
let currentPassSort = { column: null, direction: 'asc' };
let currentPage = 1;
const itemsPerPage = 8;

async function loadPasses() {
    try {
        const response = await fetch('/admin/api/good-entries', {
            headers: {
                'Authorization': 'Basic ' + (sessionStorage.getItem('adminAuth') || btoa('admin:admin1'))
            }
        });
        const data = await response.json();

        if (response.ok && data.good_entries) {
            passesData = data.good_entries;
            currentPage = 1;
            renderPasses();
            updateCounts();
        }
    } catch (error) {
        console.error('Load passes error:', error);
    }
}

function updateCounts() {
    const totalCountEl = document.getElementById('totalPassesCount');
    const recentCountEl = document.getElementById('recentPassesCount');
    const badgeCountEl = document.getElementById('passesCount');

    if (totalCountEl) totalCountEl.textContent = passesData.length;

    // Filter for last 24 hours
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const recentPasses = passesData.filter(entry => {
        const entryTime = new Date(entry.created_at);
        return entryTime >= oneDayAgo;
    });

    if (recentCountEl) recentCountEl.textContent = recentPasses.length;
    if (badgeCountEl) badgeCountEl.textContent = recentPasses.length;
}

function renderPasses() {
    const tbody = document.querySelector('#passesTable tbody');

    if (passesData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No successful access events found</td></tr>';
        return;
    }

    // Pagination
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedData = passesData.slice(startIndex, endIndex);

    tbody.innerHTML = paginatedData.map(entry => `
        <tr>
            <td>${entry.id}</td>
            <td>${new Date(entry.created_at).toLocaleString()}</td>
            <td>${entry.emp_name}</td>
            <td>${entry.emp_id || 'N/A'}</td>
        </tr>
    `).join('');

    renderPagination();
}

function renderPagination() {
    const totalPages = Math.ceil(passesData.length / itemsPerPage);
    let paginationHtml = '';

    if (totalPages > 1) {
        paginationHtml = `
            <nav aria-label="Passes table pagination">
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
    const totalPages = Math.ceil(passesData.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderPasses();
}

function sortPasses(column) {
    if (currentPassSort.column === column) {
        currentPassSort.direction = currentPassSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentPassSort.column = column;
        currentPassSort.direction = 'asc';
    }

    // Update sort icons
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
    });
    const activeTh = document.querySelector(`[data-column="${column}"]`);
    activeTh.classList.add(currentPassSort.direction);

    // Sort data
    passesData.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];

        if (column === 'id' || column === 'emp_id') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        } else if (column === 'created_at') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }

        if (aVal < bVal) return currentPassSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentPassSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    currentPage = 1;
    renderPasses();
}