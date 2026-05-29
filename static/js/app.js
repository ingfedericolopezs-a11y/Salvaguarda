// Frontend JavaScript Controller for ROESAN-SALVAGUARDAR - SIMPLIFIED UI

document.addEventListener('DOMContentLoaded', () => {
    let state = {
        masterFile: null,
        movementFiles: [],
        previewData: { movements: [], master: [] },
        currentPreviewTab: 'movements',
        historyData: []
    };

    // DOM Elements
    const elements = {
        tabBtns: document.querySelectorAll('.tab-btn'),
        tabContents: document.querySelectorAll('.tab-content'),

        uploadForm: document.getElementById('upload-form'),
        masterDropzone: document.getElementById('master-dropzone'),
        masterInput: document.getElementById('master_file'),
        masterSize: document.getElementById('master-size'),
        movementsDropzone: document.getElementById('movements-dropzone'),
        movementsInput: document.getElementById('movement_files'),
        movementsList: document.getElementById('movements-list'),
        btnProcess: document.getElementById('btn-process'),

        // Results States
        processingState: document.getElementById('processing-state'),
        loadingState: document.getElementById('loading-state'),
        successState: document.getElementById('success-state'),

        statIngresos: document.getElementById('stat-ingresos'),
        statRetiros: document.getElementById('stat-retiros'),
        statMasterAfter: document.getElementById('stat-master-after'),
        dlMovements: document.getElementById('dl-movements'),
        dlMaster: document.getElementById('dl-master'),

        // Preview section
        previewSection: document.getElementById('preview-section'),
        btnShowMovements: document.getElementById('btn-show-movements'),
        btnShowMaster: document.getElementById('btn-show-master'),
        previewSearch: document.getElementById('preview-search'),
        tableHeaders: document.getElementById('table-headers'),
        tableBody: document.getElementById('table-body'),
        previewCounter: document.getElementById('preview-counter'),

        // Search tab
        searchInput: document.getElementById('search-input'),
        btnSearch: document.getElementById('btn-search'),
        searchLoader: document.getElementById('search-loader'),
        searchResultsWrapper: document.getElementById('search-results-wrapper'),
        searchResultsList: document.getElementById('search-results-list'),
        resultsCount: document.getElementById('results-count'),
        searchEmptyState: document.getElementById('search-empty-state'),

        historyListBody: document.getElementById('history-list-body')
    };

    // --- Tab Navigation ---
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            elements.tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTab) content.classList.add('active');
            });
            if (targetTab === 'history-tab') loadHistory();
        });
    });

    // --- Helper functions ---
    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    function validateInputs() {
        elements.btnProcess.disabled = !(state.masterFile && state.movementFiles.length > 0);
    }

    function showState(stateName) {
        elements.processingState.classList.add('hidden');
        elements.loadingState.classList.add('hidden');
        elements.successState.classList.add('hidden');

        if (stateName === 'processing') elements.processingState.classList.remove('hidden');
        else if (stateName === 'loading') elements.loadingState.classList.remove('hidden');
        else if (stateName === 'success') elements.successState.classList.remove('hidden');
    }

    // --- File Upload Handlers ---
    function setupDropzone(zone, input, onFilesSelected) {
        zone.addEventListener('click', () => input.click());
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) onFilesSelected(e.dataTransfer.files);
        });
        input.addEventListener('change', () => {
            if (input.files.length > 0) onFilesSelected(input.files);
        });
    }

    // Master File
    setupDropzone(elements.masterDropzone, elements.masterInput, (files) => {
        const file = files[0];
        if (!file.name.endsWith('.xlsx')) {
            alert('❌ Error: El archivo debe ser Excel (.xlsx)\n\nArchivo seleccionado: ' + file.name);
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('❌ Error: El archivo es demasiado grande (máx. 10MB)');
            return;
        }
        state.masterFile = file;
        elements.masterSize.textContent = `✓ ${formatBytes(file.size)}`;
        elements.masterSize.classList.remove('hidden');
        validateInputs();
    });

    // Movement Files
    setupDropzone(elements.movementsDropzone, elements.movementsInput, (files) => {
        const allFiles = Array.from(files);
        const validFiles = allFiles.filter(f => f.name.endsWith('.xlsx'));
        const invalidFiles = allFiles.filter(f => !f.name.endsWith('.xlsx'));

        if (invalidFiles.length > 0) {
            alert(`⚠️ ${invalidFiles.length} archivo(s) no son válidos (deben ser .xlsx):\n\n${invalidFiles.map(f => f.name).join('\n')}`);
        }

        if (validFiles.length > 0) {
            state.movementFiles = validFiles;
            updateMovementsList();
            validateInputs();
        } else if (invalidFiles.length > 0) {
            alert('❌ No hay archivos válidos para cargar');
        }
    });

    function updateMovementsList() {
        elements.movementsList.innerHTML = '';
        if (state.movementFiles.length === 0) {
            elements.movementsList.classList.add('hidden');
            return;
        }

        const totalSize = state.movementFiles.reduce((sum, f) => sum + f.size, 0);
        state.movementFiles.forEach((file, idx) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-item-index">${idx + 1}</span>
                <span class="file-item-name">${file.name}</span>
                <span class="file-item-size">${formatBytes(file.size)}</span>
            `;
            elements.movementsList.appendChild(item);
        });

        const summary = document.createElement('div');
        summary.className = 'file-items-summary';
        summary.innerHTML = `✓ ${state.movementFiles.length} archivo(s) - ${formatBytes(totalSize)}`;
        elements.movementsList.appendChild(summary);
        elements.movementsList.classList.remove('hidden');
    }

    // --- Form Submission ---
    elements.uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData();
        formData.append('master_file', state.masterFile);
        state.movementFiles.forEach(f => formData.append('movement_files', f));

        showState('loading');
        elements.previewSection.classList.add('hidden');

        try {
            const response = await fetch('/api/process', { method: 'POST', body: formData });
            const result = await response.json();

            if (!response.ok) {
                const errorMsg = result.error || 'Error desconocido en el servidor';
                throw new Error(errorMsg);
            }

            // Update stats
            elements.statIngresos.textContent = result.statistics.total_ingresos || '0';
            elements.statRetiros.textContent = result.statistics.total_retiros || '0';
            elements.statMasterAfter.textContent = result.statistics.master_total_after || '0';

            // Setup downloads
            elements.dlMovements.href = `/api/download/${result.filenames.movements}`;
            elements.dlMaster.href = `/api/download/${result.filenames.master}`;

            // Store preview data
            state.previewData.movements = result.preview_movements || [];
            state.previewData.master = result.preview_master || [];

            showState('success');
            showPreview('movements');

        } catch (error) {
            console.error('Processing error:', error);
            alert('❌ Error en el procesamiento:\n\n' + error.message);
            showState('processing');
        }
    });

    // --- Preview Table ---
    let currentPreviewData = [];
    let currentPreviewColumns = [];

    function showPreview(type) {
        const data = type === 'movements' ? state.previewData.movements : state.previewData.master;
        if (data.length === 0) return;

        currentPreviewData = data;
        currentPreviewColumns = Object.keys(data[0]);
        state.currentPreviewTab = type;

        elements.tableHeaders.innerHTML = currentPreviewColumns.map(col =>
            `<th>${col}</th>`
        ).join('');

        renderPreviewTable(data);

        elements.btnShowMovements.classList.toggle('active', type === 'movements');
        elements.btnShowMaster.classList.toggle('active', type === 'master');

        elements.previewSection.classList.remove('hidden');
        elements.previewSearch.value = '';
    }

    function renderPreviewTable(data) {
        elements.tableBody.innerHTML = data.slice(0, 50).map(row =>
            `<tr>${currentPreviewColumns.map(col => `<td>${row[col] || '-'}</td>`).join('')}</tr>`
        ).join('');
        elements.previewCounter.textContent = `${data.length > 50 ? `Mostrando primeras 50 de ${data.length}` : `Mostrando ${data.length}`} registros`;
    }

    elements.previewSearch?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        if (!query) {
            renderPreviewTable(currentPreviewData);
            return;
        }
        const filtered = currentPreviewData.filter(row =>
            currentPreviewColumns.some(col => String(row[col] || '').toLowerCase().includes(query))
        );
        renderPreviewTable(filtered);
    });

    elements.btnShowMovements?.addEventListener('click', () => showPreview('movements'));
    elements.btnShowMaster?.addEventListener('click', () => showPreview('master'));

    // --- Search Tab ---
    async function searchCedula() {
        const query = elements.searchInput.value.trim();
        if (!query) {
            alert('Por favor ingrese un número de cédula para buscar');
            elements.searchInput.focus();
            return;
        }

        elements.searchLoader.classList.remove('hidden');
        elements.searchResultsWrapper.classList.add('hidden');
        elements.searchEmptyState.classList.add('hidden');

        try {
            const response = await fetch(`/api/search?cedula=${encodeURIComponent(query)}`);
            const results = await response.json();

            elements.searchLoader.classList.add('hidden');

            if (results.length === 0) {
                elements.searchEmptyState.classList.remove('hidden');
            } else {
                elements.resultsCount.textContent = results.length;
                elements.searchResultsList.innerHTML = results.map(result => `
                    <div class="result-row-card">
                        <div class="result-row-meta">
                            <span class="result-file-title">📄 ${result.file}</span>
                            <span class="result-sheet-badge">${result.sheet}</span>
                        </div>
                        <div class="result-row-details">
                            ${Object.entries(result.data).map(([key, val]) => `
                                <div class="detail-item">
                                    <span class="detail-label">${key}</span>
                                    <span class="detail-value">${val || '-'}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
                elements.searchResultsWrapper.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Search error:', error);
            alert('❌ Error en la búsqueda:\n\n' + error.message);
            elements.searchLoader.classList.add('hidden');
        }
    }

    elements.btnSearch?.addEventListener('click', searchCedula);
    elements.searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchCedula();
    });

    // --- History Tab ---
    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            const files = await response.json();

            if (files.length === 0) {
                elements.historyListBody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No hay archivos</td></tr>';
                return;
            }

            elements.historyListBody.innerHTML = files.map(file => `
                <tr>
                    <td>${file.name}</td>
                    <td><span class="file-type-badge ${file.type}">${file.type}</span></td>
                    <td>${formatBytes(file.size)}</td>
                    <td>${file.modified}</td>
                    <td><a href="/api/download/${file.name}" class="btn btn-secondary" style="font-size:0.8rem;padding:0.4rem 0.8rem;">Descargar</a></td>
                </tr>
            `).join('');
        } catch (error) {
            elements.historyListBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">Error cargando archivos</td></tr>';
        }
    }

    // Initial state
    validateInputs();
    showState('processing');
});
