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
            state.movementFiles = validFiles;
            updateMovementsList();
            validateInputs();
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

    elements.uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (state.isProcessing) return; // Prevent double submission
        state.isProcessing = true;

        const formData = new FormData();
        formData.append('master_file', state.masterFile);
        state.movementFiles.forEach(f => formData.append('movement_files', f));

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

            // Store preview data
            state.previewData.movements = result.preview_movements || [];
            state.previewData.master = result.preview_master || [];

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

    /**
     * Render preview table with pagination
     * Only shows first 50 rows for performance
     */
    function renderPreviewTable(data) {
        const maxRows = 50;
        const displayData = data.slice(0, maxRows);

        elements.tableBody.innerHTML = displayData
            .map(row => `
                <tr>
                    ${currentPreviewColumns
                        .map(col => `<td>${row[col] || '-'}</td>`)
                        .join('')}
                </tr>
            `)
            .join('');

        const countText = data.length > maxRows
            ? `Mostrando primeras ${maxRows} de ${data.length}`
            : `Mostrando ${data.length}`;
        elements.previewCounter.textContent = `${countText} registros`;
    }

    /**
     * Debounced search in preview table
     * Prevents excessive DOM updates
     */
    const debouncedPreviewSearch = debounce((query) => {
        if (!query) {
            renderPreviewTable(currentPreviewData);
            return;
        }

        const filtered = currentPreviewData.filter(row =>
            currentPreviewColumns.some(col =>
                String(row[col] || '').toLowerCase().includes(query.toLowerCase())
            )
        );
        renderPreviewTable(filtered);
    }, 300);

    elements.previewSearch?.addEventListener('input', (e) => {
        debouncedPreviewSearch(e.target.value);
    });

    elements.btnShowMovements?.addEventListener('click', () => showPreview('movements'));
    elements.btnShowMaster?.addEventListener('click', () => showPreview('master'));

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

    // Performance monitoring (optional)
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log(`✓ Page load time: ${pageLoadTime}ms`);
        });
    }
});
