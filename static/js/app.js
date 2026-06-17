/**
 * ROESAN-SALVAGUARDAR: Frontend Application Controller
 * Modern, efficient, and performant implementation with optimization techniques
 */

// ============================================================================
// PERFORMANCE OPTIMIZATION UTILITIES
// ============================================================================

/**
 * Debounce function to limit function execution frequency
 * Useful for search, resize events, etc.
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function to limit function execution rate
 * Useful for scroll events
 */
function throttle(func, limit = 100) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Cache system for API responses
 * Prevents redundant network requests
 */
class CacheManager {
    constructor(ttl = 5 * 60 * 1000) { // 5 minutes default
        this.cache = new Map();
        this.ttl = ttl;
    }

    set(key, value) {
        const expiresAt = Date.now() + this.ttl;
        this.cache.set(key, { value, expiresAt });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() > item.expiresAt) {
            this.cache.delete(key);
            return null;
        }
        return item.value;
    }

    clear() {
        this.cache.clear();
    }

    has(key) {
        return this.get(key) !== null;
    }
}

// ============================================================================
// MAIN APPLICATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize cache manager
    const cache = new CacheManager(5 * 60 * 1000); // 5 minutes

    // Application state with better organization
    const state = {
        masterFile: null,
        movementFiles: [],
        previewData: { movements: [], master: [] },
        currentPreviewTab: 'movements',
        historyData: [],
        isProcessing: false,
        lastSearchQuery: null,
        searchResults: []
    };

    // Global lastProcessedData for reports and comparison
    window.lastProcessedData = {
        movements_df: [],
        master_df: [],
        analytics: null
    };

    // Lazy load DOM elements (only when needed)
    const getElement = (() => {
        const cache = {};
        return (id) => {
            if (!cache[id]) {
                cache[id] = document.getElementById(id);
            }
            return cache[id];
        };
    })();

    // DOM Elements - accessed via lazy loader
    const elements = {
        get tabBtns() { return document.querySelectorAll('.tab-btn'); },
        get tabContents() { return document.querySelectorAll('.tab-content'); },

        get uploadForm() { return getElement('upload-form'); },
        get masterDropzone() { return getElement('master-dropzone'); },
        get masterInput() { return getElement('master_file'); },
        get masterSize() { return getElement('master-size'); },
        get movementsDropzone() { return getElement('movements-dropzone'); },
        get movementsInput() { return getElement('movement_files'); },
        get movementsList() { return getElement('movements-list'); },
        get btnProcess() { return getElement('btn-process'); },

        // Results States
        get processingState() { return getElement('processing-state'); },
        get loadingState() { return getElement('loading-state'); },
        get successState() { return getElement('success-state'); },

        get statIngresos() { return getElement('stat-ingresos'); },
        get statRetiros() { return getElement('stat-retiros'); },
        get statMasterAfter() { return getElement('stat-master-after'); },
        get dlMovements() { return getElement('dl-movements'); },
        get dlMaster() { return getElement('dl-master'); },

        // Preview section
        get previewSection() { return getElement('preview-section'); },
        get btnShowMovements() { return getElement('btn-show-movements'); },
        get btnShowMaster() { return getElement('btn-show-master'); },
        get previewSearch() { return getElement('preview-search'); },
        get previewFilterType() { return getElement('preview-filter-type'); },
        get tableHeaders() { return getElement('table-headers'); },
        get tableBody() { return getElement('table-body'); },
        get previewCounter() { return getElement('preview-counter'); },

        // Search tab
        get searchInput() { return getElement('search-input'); },
        get btnSearch() { return getElement('btn-search'); },
        get searchLoader() { return getElement('search-loader'); },
        get searchResultsWrapper() { return getElement('search-results-wrapper'); },
        get searchResultsList() { return getElement('search-results-list'); },
        get resultsCount() { return getElement('results-count'); },
        get searchEmptyState() { return getElement('search-empty-state'); },

        get historyListBody() { return getElement('history-list-body'); }
    };

    // ========================================================================
    // TAB NAVIGATION
    // ========================================================================

    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Update active states
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            elements.tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTab) {
                    content.classList.add('active');
                }
            });

            // Load history when history tab is clicked
            if (targetTab === 'history-tab') {
                loadHistory();
            }
        });
    });

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

    /**
     * Format bytes into human-readable size
     * Cached for performance
     */
    const formatBytesCache = new Map();
    function formatBytes(bytes) {
        if (formatBytesCache.has(bytes)) {
            return formatBytesCache.get(bytes);
        }

        if (bytes === 0) {
            const result = '0 B';
            formatBytesCache.set(bytes, result);
            return result;
        }

        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        const result = Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];

        formatBytesCache.set(bytes, result);
        return result;
    }

    /**
     * Validate form inputs
     */
    function validateInputs() {
        const hasFiles = state.masterFile && state.movementFiles.length > 0;
        elements.btnProcess.disabled = !hasFiles;
        elements.btnProcess.title = hasFiles
            ? 'Hacer clic para procesar los archivos'
            : 'Carga ambos tipos de archivos para procesar';
    }

    /**
     * Show/hide processing states with smooth transitions
     */
    function showState(stateName) {
        const states = [elements.processingState, elements.loadingState, elements.successState];
        states.forEach(state => state.classList.remove('active'));

        switch (stateName) {
            case 'processing':
                elements.processingState?.classList.add('active');
                break;
            case 'loading':
                elements.loadingState?.classList.add('active');
                break;
            case 'success':
                elements.successState?.classList.add('active');
                break;
        }
    }

    // ========================================================================
    // FILE UPLOAD HANDLERS
    // ========================================================================

    /**
     * Setup drag and drop for file zones
     * Uses event delegation for efficiency
     */
    function setupDropzone(zone, input, onFilesSelected) {
        zone.addEventListener('click', () => input.click());

        // Drag over
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('dragover');
        });

        // Drag leave
        zone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dragover');
        });

        // Drop
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                onFilesSelected(e.dataTransfer.files);
            }
        });

        // File input change
        input.addEventListener('change', () => {
            if (input.files.length > 0) {
                onFilesSelected(input.files);
            }
        });
    }

    // Master File Handler
    setupDropzone(elements.masterDropzone, elements.masterInput, (files) => {
        const file = files[0];
        if (!file.name.endsWith('.xlsx')) {
            showNotification('❌ Error: El archivo debe ser Excel (.xlsx)', 'error');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            showNotification('❌ Error: El archivo es demasiado grande (máx. 10MB)', 'error');
            return;
        }

        state.masterFile = file;
        elements.masterSize.textContent = `✓ ${formatBytes(file.size)}`;
        elements.masterSize.classList.remove('hidden');
        validateInputs();
    });

    // Movement Files Handler
    setupDropzone(elements.movementsDropzone, elements.movementsInput, (files) => {
        const allFiles = Array.from(files);
        const validFiles = allFiles.filter(f => f.name.endsWith('.xlsx'));
        const invalidFiles = allFiles.filter(f => !f.name.endsWith('.xlsx'));

        if (invalidFiles.length > 0) {
            showNotification(`⚠️ ${invalidFiles.length} archivo(s) no son válidos (deben ser .xlsx)`, 'warning');
        }

        if (validFiles.length > 0) {
            // Add new files to existing list, avoiding duplicates by filename
            const existingNames = new Set(state.movementFiles.map(f => f.name));
            const newFiles = validFiles.filter(f => !existingNames.has(f.name));

            if (newFiles.length > 0) {
                state.movementFiles = [...state.movementFiles, ...newFiles];
                updateMovementsList();
                validateInputs();
            } else {
                showNotification('⚠️ Los archivos seleccionados ya están en la lista', 'warning');
            }
        }
    });

    /**
     * Update movements list display
     * Optimized rendering
     */
    function updateMovementsList() {
        elements.movementsList.innerHTML = '';
        if (state.movementFiles.length === 0) {
            elements.movementsList.classList.add('hidden');
            return;
        }

        // Use document fragment for efficient DOM operations
        const fragment = document.createDocumentFragment();
        const totalSize = state.movementFiles.reduce((sum, f) => sum + f.size, 0);

        state.movementFiles.forEach((file, idx) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-item-index">${idx + 1}</span>
                <span class="file-item-name">${file.name}</span>
                <span class="file-item-size">${formatBytes(file.size)}</span>
            `;
            fragment.appendChild(item);
        });

        const summary = document.createElement('div');
        summary.className = 'file-items-summary';
        summary.innerHTML = `✓ ${state.movementFiles.length} archivo(s) - ${formatBytes(totalSize)}`;
        fragment.appendChild(summary);

        elements.movementsList.appendChild(fragment);
        elements.movementsList.classList.remove('hidden');
    }

    // ========================================================================
    // FORM SUBMISSION & PROCESSING
    // ========================================================================

    // ── Cobro modal logic ────────────────────────────────────────────────────
    const cobroModal   = document.getElementById('cobro-modal');
    const cobroMesEl   = document.getElementById('cobro-mes');
    const cobroAnioEl  = document.getElementById('cobro-anio');
    const cobroPreview = document.getElementById('cobro-preview');
    const cobroCancelBtn  = document.getElementById('cobro-cancel');
    const cobroConfirmBtn = document.getElementById('cobro-confirm');

    const _MESES = ['', 'Enero','Febrero','Marzo','Abril','Mayo','Junio',
                    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

    function _updateCobroPreview() {
        const mes  = parseInt(cobroMesEl.value);
        const anio = parseInt(cobroAnioEl.value);
        if (!mes || !anio) return;
        const prevMes  = mes === 1 ? 12 : mes - 1;
        const prevAnio = mes === 1 ? anio - 1 : anio;
        const mm = String(prevMes).padStart(2, '0');
        cobroPreview.textContent = `Fecha de cobro: 26/${mm}/${prevAnio}`;
    }

    // Set defaults: current month & year
    (function initCobroDefaults() {
        const now = new Date();
        cobroMesEl.value  = now.getMonth() + 1;
        cobroAnioEl.value = now.getFullYear();
        _updateCobroPreview();
    })();

    cobroMesEl.addEventListener('change',  _updateCobroPreview);
    cobroAnioEl.addEventListener('input',  _updateCobroPreview);
    cobroCancelBtn.addEventListener('click', () => {
        cobroModal.style.display = 'none';
        state.isProcessing = false;
    });

    function _showCobroModal() {
        cobroModal.style.display = 'flex';
        _updateCobroPreview();
    }

    // Resolves with {mes, anio} when confirmed, null when cancelled
    function _waitCobroConfirm() {
        return new Promise((resolve) => {
            function onConfirm() { cleanup(); resolve({ mes: cobroMesEl.value, anio: cobroAnioEl.value }); }
            function onCancel()  { cleanup(); resolve(null); }
            function cleanup()   { cobroConfirmBtn.removeEventListener('click', onConfirm); cobroCancelBtn.removeEventListener('click', onCancel); cobroModal.style.display = 'none'; }
            cobroConfirmBtn.addEventListener('click', onConfirm);
            cobroCancelBtn.addEventListener('click',  onCancel);
        });
    }
    // ── End cobro modal logic ─────────────────────────────────────────────────

    elements.uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (state.isProcessing) return;
        state.isProcessing = true;

        // Show cobro modal before processing
        _showCobroModal();
        const cobro = await _waitCobroConfirm();
        if (!cobro) { state.isProcessing = false; return; }

        const formData = new FormData();
        formData.append('master_file', state.masterFile);
        state.movementFiles.forEach(f => formData.append('movement_files', f));
        formData.append('cobro_mes',  cobro.mes);
        formData.append('cobro_anio', cobro.anio);

        showState('loading');
        elements.previewSection.classList.add('hidden');

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                const errorMsg = result.error || 'Error desconocido en el servidor';
                throw new Error(errorMsg);
            }

            // Update stats with animation
            updateStatWithAnimation(elements.statIngresos, result.statistics.total_ingresos || '0');
            updateStatWithAnimation(elements.statRetiros, result.statistics.total_retiros || '0');
            updateStatWithAnimation(elements.statMasterAfter, result.statistics.master_total_after || '0');

            // Setup downloads
            elements.dlMovements.href = `/api/download/${result.filenames.movements}`;
            elements.dlMaster.href = `/api/download/${result.filenames.master}`;

            // Persist download links to localStorage for recovery after page reload
            localStorage.setItem('lastProcessedFiles', JSON.stringify({
                timestamp: new Date().toISOString(),
                movements: result.filenames.movements,
                master: result.filenames.master
            }));

            // Store preview data
            state.previewData.movements = result.preview_movements || [];
            state.previewData.master = result.preview_master || [];

            // Update global lastProcessedData for reports and comparison
            window.lastProcessedData.movements_df = result.preview_movements || [];
            window.lastProcessedData.master_df = result.preview_master || [];

            // Update reports and history displays
            if (typeof updateReportsTab === 'function') {
                updateReportsTab();
            }
            if (typeof loadProcessingHistory === 'function') {
                loadProcessingHistory();
            }

            showState('success');
            showPreview('movements');
            showNotification('✅ ¡Conciliación completada exitosamente!', 'success');

        } catch (error) {
            console.error('Processing error:', error);
            showNotification('❌ Error en el procesamiento: ' + error.message, 'error');
            showState('processing');
        } finally {
            state.isProcessing = false;
        }
    });

    /**
     * Animate number updates
     * Better UX for stat changes
     */
    function updateStatWithAnimation(element, newValue) {
        if (element.textContent === newValue) return;

        element.style.opacity = '0.5';
        element.textContent = newValue;
        element.style.transition = 'opacity 0.3s ease';

        setTimeout(() => {
            element.style.opacity = '1';
        }, 10);
    }

    // ========================================================================
    // PREVIEW TABLE
    // ========================================================================

    let currentPreviewData = [];
    let currentPreviewColumns = [];

    /**
     * Show preview with optimized rendering
     */
    function showPreview(type) {
        const data = type === 'movements' ? state.previewData.movements : state.previewData.master;
        if (data.length === 0) return;

        currentPreviewData = data;
        currentPreviewColumns = Object.keys(data[0]);
        state.currentPreviewTab = type;

        // Use HTML instead of appendChild for better performance
        elements.tableHeaders.innerHTML = currentPreviewColumns
            .map(col => `<th>${col}</th>`)
            .join('');

        renderPreviewTable(data);

        // Update toggle buttons
        elements.btnShowMovements.classList.toggle('active', type === 'movements');
        elements.btnShowMaster.classList.toggle('active', type === 'master');

        elements.previewSection.classList.remove('hidden');
        elements.previewSearch.value = '';
    }

    const PAGE_SIZE = 100;
    let currentPage = 1;
    let currentFilteredData = [];

    function renderPreviewTable(data) {
        currentFilteredData = data;
        currentPage = 1;
        renderPage();
    }

    function renderPage() {
        const data = currentFilteredData;
        const totalPages = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
        if (currentPage > totalPages) currentPage = totalPages;

        if (data.length === 0) {
            elements.tableBody.innerHTML = '<tr><td colspan="100" style="text-align:center; padding:2rem; color:#999;">No se encontraron registros con los filtros aplicados</td></tr>';
            elements.previewCounter.textContent = '⚠️ Sin resultados';
            _renderPagination(0, 1, 1);
            return;
        }

        const start = (currentPage - 1) * PAGE_SIZE;
        const end = Math.min(start + PAGE_SIZE, data.length);
        const pageData = data.slice(start, end);

        elements.tableBody.innerHTML = pageData
            .map(row => `
                <tr>
                    ${currentPreviewColumns
                        .map(col => `<td>${row[col] || '-'}</td>`)
                        .join('')}
                </tr>
            `)
            .join('');

        const filterInfo = elements.previewSearch?.value || elements.previewFilterType?.value ? ' (filtrados)' : '';
        elements.previewCounter.textContent = `Mostrando ${start + 1}–${end} de ${data.length} registros${filterInfo}`;
        _renderPagination(data.length, currentPage, totalPages);
    }

    function _renderPagination(total, page, totalPages) {
        let pg = document.getElementById('preview-pagination');
        if (!pg) {
            pg = document.createElement('div');
            pg.id = 'preview-pagination';
            pg.style.cssText = 'display:flex;align-items:center;gap:0.75rem;justify-content:center;margin-top:1rem;flex-wrap:wrap;';
            const footer = elements.previewCounter?.parentElement;
            if (footer) footer.insertAdjacentElement('afterend', pg);
        }
        if (total === 0 || totalPages <= 1) { pg.innerHTML = ''; return; }

        const btnStyle = 'padding:0.4rem 0.9rem;border:1px solid #444;border-radius:6px;background:#1e1e2e;color:#cdd6f4;cursor:pointer;font-size:0.85rem;';
        const activeBtnStyle = 'padding:0.4rem 0.9rem;border:1px solid #89b4fa;border-radius:6px;background:#313244;color:#89b4fa;cursor:pointer;font-size:0.85rem;font-weight:600;';

        let pageButtons = '';
        // Show first, last, and pages around current
        const delta = 2;
        const range = [];
        for (let i = Math.max(1, page - delta); i <= Math.min(totalPages, page + delta); i++) range.push(i);
        if (range[0] > 1) { pageButtons += `<button style="${btnStyle}" onclick="window._previewGoTo(1)">1</button>`; if (range[0] > 2) pageButtons += `<span style="color:#6c7086">…</span>`; }
        range.forEach(p => { pageButtons += `<button style="${p === page ? activeBtnStyle : btnStyle}" onclick="window._previewGoTo(${p})">${p}</button>`; });
        if (range[range.length-1] < totalPages) { if (range[range.length-1] < totalPages - 1) pageButtons += `<span style="color:#6c7086">…</span>`; pageButtons += `<button style="${btnStyle}" onclick="window._previewGoTo(${totalPages})">${totalPages}</button>`; }

        pg.innerHTML = `
            <button style="${btnStyle}" onclick="window._previewGoTo(${page-1})" ${page<=1?'disabled':''}>◀ Anterior</button>
            ${pageButtons}
            <button style="${btnStyle}" onclick="window._previewGoTo(${page+1})" ${page>=totalPages?'disabled':''}>Siguiente ▶</button>
            <span style="color:#6c7086;font-size:0.8rem;">Página ${page} de ${totalPages}</span>
        `;
    }

    window._previewGoTo = function(page) {
        const totalPages = Math.ceil(currentFilteredData.length / PAGE_SIZE);
        if (page < 1 || page > totalPages) return;
        currentPage = page;
        renderPage();
        elements.previewSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    /**
     * Apply both search and filter to preview table
     * Filters by text search and movement type
     */
    function applyPreviewFilters() {
        const searchQuery = elements.previewSearch?.value || '';
        const filterType = elements.previewFilterType?.value || '';

        let filtered = currentPreviewData;

        // Apply type filter
        if (filterType) {
            filtered = filtered.filter(row => {
                const tipoNovedad = String(row['TIPO_NOVEDAD'] || '').toUpperCase();
                return tipoNovedad.includes(filterType);
            });
        }

        // Apply search filter
        if (searchQuery) {
            filtered = filtered.filter(row =>
                currentPreviewColumns.some(col =>
                    String(row[col] || '').toLowerCase().includes(searchQuery.toLowerCase())
                )
            );
        }

        renderPreviewTable(filtered);
    }

    const debouncedPreviewSearch = debounce(applyPreviewFilters, 300);

    elements.previewSearch?.addEventListener('input', debouncedPreviewSearch);
    elements.previewFilterType?.addEventListener('change', applyPreviewFilters);

    elements.btnShowMovements?.addEventListener('click', () => showPreview('movements'));
    elements.btnShowMaster?.addEventListener('click', () => showPreview('master'));

    /**
     * Download all preview data as Excel file
     */
    const downloadPreviewButton = getElement('btn-download-preview');
    if (downloadPreviewButton) {
        downloadPreviewButton.addEventListener('click', () => {
            if (!currentPreviewData || currentPreviewData.length === 0) {
                showNotification('No hay datos para descargar', 'info');
                return;
            }

            // Convert data to CSV format
            const headers = currentPreviewColumns;
            const csvContent = [
                headers.join(','),
                ...currentPreviewData.map(row =>
                    headers.map(col => {
                        const value = row[col];
                        if (value === null || value === undefined) return '';
                        // Escape commas and quotes in values
                        const str = String(value);
                        return str.includes(',') || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str;
                    }).join(',')
                )
            ].join('\n');

            // Create blob and download
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            const filename = state.currentPreviewTab === 'movements'
                ? 'Movimientos_Completos.csv'
                : 'Plantilla_Completa.csv';

            link.href = url;
            link.download = filename;
            link.click();
            URL.revokeObjectURL(url);

            showNotification(`✅ Descargando ${currentPreviewData.length} registros completos`, 'success');
        });
    }

    // ========================================================================
    // SEARCH FUNCTIONALITY
    // ========================================================================

    /**
     * Search cedula with caching
     * Reduces unnecessary API calls
     */
    async function searchCedula() {
        const query = elements.searchInput.value.trim();
        if (!query) {
            showNotification('Por favor ingrese un número de cédula para buscar', 'info');
            elements.searchInput.focus();
            return;
        }

        // Check cache first
        const cacheKey = `search_${query}`;
        if (cache.has(cacheKey)) {
            displaySearchResults(cache.get(cacheKey));
            return;
        }

        elements.searchLoader.classList.remove('hidden');
        elements.searchResultsWrapper.classList.add('hidden');
        elements.searchEmptyState.classList.add('hidden');

        try {
            const response = await fetch(`/api/search?cedula=${encodeURIComponent(query)}`);
            const results = await response.json();

            // Cache the results
            cache.set(cacheKey, results);

            displaySearchResults(results);

        } catch (error) {
            console.error('Search error:', error);
            showNotification('❌ Error en la búsqueda: ' + error.message, 'error');
            elements.searchLoader.classList.add('hidden');
        }
    }

    /**
     * Display search results
     */
    function displaySearchResults(results) {
        elements.searchLoader.classList.add('hidden');

        if (results.length === 0) {
            elements.searchEmptyState.classList.remove('hidden');
        } else {
            elements.resultsCount.textContent = results.length;
            elements.searchResultsList.innerHTML = results
                .map(result => `
                    <div class="result-row-card">
                        <div class="result-row-meta">
                            <span class="result-file-title">📄 ${result.file}</span>
                            <span class="result-sheet-badge">${result.sheet}</span>
                        </div>
                        <div class="result-row-details">
                            ${Object.entries(result.data)
                                .map(([key, val]) => `
                                    <div class="detail-item">
                                        <span class="detail-label">${key}</span>
                                        <span class="detail-value">${val || '-'}</span>
                                    </div>
                                `)
                                .join('')}
                        </div>
                    </div>
                `)
                .join('');
            elements.searchResultsWrapper.classList.remove('hidden');
        }
    }

    elements.btnSearch?.addEventListener('click', searchCedula);
    elements.searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchCedula();
        }
    });

    // Clear results when search input is cleared
    elements.searchInput?.addEventListener('input', (e) => {
        if (!e.target.value.trim()) {
            elements.searchEmptyState.classList.add('hidden');
            elements.searchResultsWrapper.classList.add('hidden');
        }
    });

    // ========================================================================
    // HISTORY TAB
    // ========================================================================

    /**
     * Load history with caching
     */
    async function loadHistory() {
        // Check cache first
        const cacheKey = 'history_list';
        if (cache.has(cacheKey)) {
            displayHistory(cache.get(cacheKey));
            return;
        }

        try {
            const response = await fetch('/api/history');
            const files = await response.json();

            // Cache the results for 1 minute
            cache.set(cacheKey, files);

            displayHistory(files);

        } catch (error) {
            console.error('History error:', error);
            elements.historyListBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">Error cargando archivos</td></tr>';
        }
    }

    /**
     * Display history list
     */
    function displayHistory(files) {
        if (files.length === 0) {
            elements.historyListBody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No hay archivos</td></tr>';
            return;
        }

        elements.historyListBody.innerHTML = files
            .map(file => `
                <tr>
                    <td>${file.name}</td>
                    <td><span class="file-type-badge ${file.type}">${file.type}</span></td>
                    <td>${formatBytes(file.size)}</td>
                    <td>${file.modified}</td>
                    <td><a href="/api/download/${file.name}" class="btn btn-secondary" style="font-size:0.8rem;padding:0.4rem 0.8rem;">Descargar</a></td>
                </tr>
            `)
            .join('');
    }

    // ========================================================================
    // NOTIFICATIONS SYSTEM
    // ========================================================================

    /**
     * Show notifications
     * Simple but effective user feedback
     */
    function showNotification(message, type = 'info') {
        // Prevent notification spam
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#0ea5e9'};
            color: white;
            border-radius: 10px;
            z-index: 9999;
            animation: slideInRight 0.3s ease-out;
            font-weight: 500;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
            max-width: 400px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Auto-remove
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    validateInputs();
    showState('processing');

    /**
     * Restore download links from localStorage if they exist
     * Allows users to download files even after page reload
     */
    function restoreDownloadLinks() {
        const savedData = localStorage.getItem('lastProcessedFiles');
        if (savedData) {
            try {
                const { timestamp, movements, master } = JSON.parse(savedData);
                const savedTime = new Date(timestamp);
                const now = new Date();
                const hoursAgo = (now - savedTime) / (1000 * 60 * 60);

                // Only restore if files were processed in the last 24 hours
                if (hoursAgo < 24) {
                    elements.dlMovements.href = `/api/download/${movements}`;
                    elements.dlMaster.href = `/api/download/${master}`;

                    // Show success state with restored downloads
                    showState('success');

                    // Show a notification that downloads are restored
                    const savedDate = savedTime.toLocaleString('es-ES');
                    showNotification(`📥 Archivos disponibles para descargar (procesados: ${savedDate})`, 'info');
                }
            } catch (error) {
                console.warn('Error restoring downloads from localStorage:', error);
            }
        }
    }

    // Restore previous downloads if they exist
    restoreDownloadLinks();

    // Performance monitoring (optional)
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log(`✓ Page load time: ${pageLoadTime}ms`);
        });
    }

    // ========================================================================
    // ADVANCED REPORTS
    // ========================================================================

    /**
     * Generate PDF Report
     */
    const btnGeneratePdf = document.getElementById('btn-generate-pdf');
    if (btnGeneratePdf) {
        btnGeneratePdf.addEventListener('click', generatePdfReport);
    }

    /**
     * Generate Excel Report
     */
    const btnGenerateExcel = document.getElementById('btn-generate-excel');
    if (btnGenerateExcel) {
        btnGenerateExcel.addEventListener('click', generateExcelReport);
    }

    async function generatePdfReport() {
        try {
            const btn = elements.btnGeneratePdf;
            const spinner = btn.querySelector('.spinner');
            const btnText = btn.querySelector('.btn-text');

            // Disable button and show spinner
            btn.disabled = true;
            spinner.classList.remove('hidden');
            btnText.textContent = 'Generando PDF...';

            const response = await fetch('/api/reports/pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Error al generar PDF');
            }

            // Success - download the file
            showNotification('✅ Reporte PDF generado exitosamente', 'success');

            // Create download link
            const downloadUrl = `/api/reports/download/${result.filename}`;
            window.open(downloadUrl, '_blank');

        } catch (error) {
            console.error('PDF generation error:', error);
            showNotification('❌ Error al generar PDF: ' + error.message, 'error');
        } finally {
            // Re-enable button
            const btn = elements.btnGeneratePdf;
            const spinner = btn.querySelector('.spinner');
            const btnText = btn.querySelector('.btn-text');

            btn.disabled = false;
            spinner.classList.add('hidden');
            btnText.textContent = '📄 Generar PDF';
        }
    }

    async function generateExcelReport() {
        try {
            const btn = elements.btnGenerateExcel;
            const spinner = btn.querySelector('.spinner');
            const btnText = btn.querySelector('.btn-text');

            // Disable button and show spinner
            btn.disabled = true;
            spinner.classList.remove('hidden');
            btnText.textContent = 'Generando Excel...';

            const response = await fetch('/api/reports/excel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Error al generar Excel');
            }

            // Success - download the file
            showNotification('✅ Reporte Excel generado exitosamente', 'success');

            // Create download link
            const downloadUrl = `/api/reports/download/${result.filename}`;
            window.open(downloadUrl, '_blank');

        } catch (error) {
            console.error('Excel generation error:', error);
            showNotification('❌ Error al generar Excel: ' + error.message, 'error');
        } finally {
            // Re-enable button
            const btn = elements.btnGenerateExcel;
            const spinner = btn.querySelector('.spinner');
            const btnText = btn.querySelector('.btn-text');

            btn.disabled = false;
            spinner.classList.add('hidden');
            btnText.textContent = '📊 Generar Excel';
        }
    }

    // Add report button references to elements
    elements.btnGeneratePdf = document.getElementById('btn-generate-pdf');
    elements.btnGenerateExcel = document.getElementById('btn-generate-excel');

    // Reports Tab Elements
    elements.btnReportPdf = document.getElementById('btn-report-pdf');
    elements.btnReportExcel = document.getElementById('btn-report-excel');
    elements.reportsEmptyState = document.getElementById('reports-empty-state');

    // Reports functionality
    let chartInstance = null;
    let lastReportData = null;

    function updateReportsTab() {
        if (!lastProcessedData.movements_df || lastProcessedData.movements_df.length === 0) {
            elements.reportsEmptyState.style.display = 'block';
            elements.btnReportPdf.disabled = true;
            elements.btnReportExcel.disabled = true;
            return;
        }

        elements.reportsEmptyState.style.display = 'none';
        elements.btnReportPdf.disabled = false;
        elements.btnReportExcel.disabled = false;

        // Calculate statistics
        const movements = lastProcessedData.movements_df;
        const ingresos = movements.filter(m => m.Tipo === 'INGRESO');
        const retiros = movements.filter(m => m.Tipo === 'RETIRO');

        const totalIngresos = ingresos.reduce((sum, m) => sum + (parseFloat(m.Valor) || 0), 0);
        const totalRetiros = retiros.reduce((sum, m) => sum + (parseFloat(m.Valor) || 0), 0);
        const neto = totalIngresos - totalRetiros;

        // Update stat cards
        document.getElementById('report-total-ingresos').textContent = `$${totalIngresos.toFixed(2)}`;
        document.getElementById('report-count-ingresos').textContent = `${ingresos.length} registros`;

        document.getElementById('report-total-retiros').textContent = `$${totalRetiros.toFixed(2)}`;
        document.getElementById('report-count-retiros').textContent = `${retiros.length} registros`;

        document.getElementById('report-balance-neto').textContent = `$${neto.toFixed(2)}`;
        const netoStatus = neto > 0 ? '✓ Positivo' : neto < 0 ? '✗ Negativo' : 'Neutral';
        document.getElementById('report-balance-status').textContent = netoStatus;

        const total = totalIngresos + totalRetiros;
        const porcentajeIngresos = total > 0 ? ((totalIngresos / total) * 100).toFixed(1) : 0;
        document.getElementById('report-porcentaje').textContent = `${porcentajeIngresos}%`;
        document.getElementById('report-proporcion').textContent = 'Ingresos vs Retiros';

        // Create chart
        createReportChart(totalIngresos, totalRetiros);

        lastReportData = { totalIngresos, totalRetiros, neto, movements };
    }

    function createReportChart(ingresos, retiros) {
        const ctx = document.getElementById('chartIngresoRetiro');
        if (!ctx) return;

        // Destroy previous chart if exists
        if (chartInstance) {
            chartInstance.destroy();
        }

        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Ingresos', 'Retiros'],
                datasets: [{
                    label: 'Montos ($)',
                    data: [ingresos, retiros],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderColor: [
                        'rgba(16, 185, 129, 1)',
                        'rgba(239, 68, 68, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8,
                    hoverBackgroundColor: [
                        'rgba(16, 185, 129, 1)',
                        'rgba(239, 68, 68, 1)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#f8fafc',
                            font: { size: 14, weight: 'bold' }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#cbd5e1',
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        },
                        grid: {
                            color: 'rgba(124, 58, 237, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#cbd5e1'
                        },
                        grid: {
                            color: 'rgba(124, 58, 237, 0.1)'
                        }
                    }
                }
            }
        });
    }

    // Report download handlers
    if (elements.btnReportPdf) {
        elements.btnReportPdf.addEventListener('click', generatePdfReport);
    }
    if (elements.btnReportExcel) {
        elements.btnReportExcel.addEventListener('click', generateExcelReport);
    }

    // History/Comparison functionality
    async function loadProcessingHistory() {
        try {
            const response = await fetch('/api/history/list');
            const history = await response.json();

            const tbody = document.getElementById('processing-history-body');
            tbody.innerHTML = '';

            if (!history || history.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Sin histórico de procesaminetos</td></tr>';
                return;
            }

            history.reverse(); // Show newest first

            history.forEach(record => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${record.date_formatted}</td>
                    <td>${record.movements_count}</td>
                    <td>${record.master_count}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="compareWithHistory('${record.id}')">
                            Cruzar
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } catch (error) {
            console.error('Error loading history:', error);
            document.getElementById('processing-history-body').innerHTML =
                '<tr><td colspan="4" style="text-align: center; color: red;">Error cargando histórico</td></tr>';
        }
    }

    window.compareWithHistory = async function(recordId) {
        if (!lastProcessedData.movements_df || lastProcessedData.movements_df.length === 0) {
            showNotification('⚠️ Procesa archivos primero para hacer un cruce', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/history/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_id: recordId })
            });

            const comparison = await response.json();

            if (!response.ok) {
                showNotification('❌ Error en el cruce: ' + (comparison.error || 'Unknown error'), 'error');
                return;
            }

            displayComparisonResults(comparison);
            showNotification('✅ Cruce completado', 'success');

        } catch (error) {
            console.error('Comparison error:', error);
            showNotification('❌ Error al hacer el cruce', 'error');
        }
    };

    function displayComparisonResults(comparison) {
        const resultsDiv = document.getElementById('comparison-results');

        // Update summary stats
        document.getElementById('comp-added').textContent = comparison.summary.added_count;
        document.getElementById('comp-removed').textContent = comparison.summary.removed_count;
        document.getElementById('comp-modified').textContent = comparison.summary.modified_count;
        document.getElementById('comp-unchanged').textContent = comparison.summary.unchanged_count;

        // Update added list
        const addedDiv = document.getElementById('added-list');
        if (comparison.added.length === 0) {
            addedDiv.innerHTML = '<p>Ninguna cédula agregada</p>';
        } else {
            addedDiv.innerHTML = comparison.added
                .map(id => `<div class="detail-item">${id}</div>`)
                .join('');
        }

        // Update removed list
        const removedDiv = document.getElementById('removed-list');
        if (comparison.removed.length === 0) {
            removedDiv.innerHTML = '<p>Ninguna cédula removida</p>';
        } else {
            removedDiv.innerHTML = comparison.removed
                .map(id => `<div class="detail-item">${id}</div>`)
                .join('');
        }

        // Update modified list
        const modifiedDiv = document.getElementById('modified-list');
        if (comparison.modified.length === 0) {
            modifiedDiv.innerHTML = '<p>Ninguna cédula modificada</p>';
        } else {
            modifiedDiv.innerHTML = comparison.modified
                .map(m => `<div class="detail-item">${m.id}</div>`)
                .join('');
        }

        // Show results
        resultsDiv.classList.remove('hidden');

        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // Load history when page loads
    loadProcessingHistory();
});
