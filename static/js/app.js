// Frontend JavaScript Controller for ROESAN-SALVAGUARDAR

document.addEventListener('DOMContentLoaded', () => {
    // State management
    let state = {
        masterFile: null,
        movementFiles: [],
        previewData: {
            movements: [],
            master: []
        },
        currentPreviewTab: 'movements', // or 'master'
        historyData: []
    };

    // DOM Elements
    const elements = {
        // Tabs
        tabBtns: document.querySelectorAll('.tab-btn'),
        tabContents: document.querySelectorAll('.tab-content'),
        
        // Upload form
        uploadForm: document.getElementById('upload-form'),
        masterDropzone: document.getElementById('master-dropzone'),
        masterInput: document.getElementById('master_file'),
        masterSize: document.getElementById('master-size'),
        movementsDropzone: document.getElementById('movements-dropzone'),
        movementsInput: document.getElementById('movement_files'),
        movementsList: document.getElementById('movements-list'),
        btnProcess: document.getElementById('btn-process'),
        
        // Console / Stats / Downloads
        logsContainer: document.getElementById('logs-container'),
        statusBadge: document.getElementById('status-badge'),
        statsContainer: document.getElementById('stats-container'),
        statIngresos: document.getElementById('stat-ingresos'),
        statRetiros: document.getElementById('stat-retiros'),
        statMasterAfter: document.getElementById('stat-master-after'),
        downloadsContainer: document.getElementById('downloads-container'),
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
        
        // History tab
        historyListBody: document.getElementById('history-list-body')
    };

    // --- Tab Navigation ---
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Toggle active buttons
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Toggle active contents
            elements.tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTab) {
                    content.classList.add('active');
                }
            });
            
            // Action on tab entry
            if (targetTab === 'history-tab') {
                loadHistory();
            }
        });
    });

    // --- Helper functions ---
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function addLogLine(message, type = 'system') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        line.innerText = `[${timestamp}] ${message}`;
        
        elements.logsContainer.appendChild(line);
        elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
    }

    function validateInputs() {
        const isValid = state.masterFile !== null && state.movementFiles.length > 0;
        elements.btnProcess.disabled = !isValid;
    }

    // --- File Uploader Interactive Features ---
    
    // Dropzone events helper
    function setupDropzone(zone, input, onFilesSelected) {
        zone.addEventListener('click', () => input.click());
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                onFilesSelected(e.dataTransfer.files);
            }
        });
        
        input.addEventListener('change', () => {
            if (input.files && input.files.length > 0) {
                onFilesSelected(input.files);
            }
        });
    }

    // Master File Select handler
    setupDropzone(elements.masterDropzone, elements.masterInput, (files) => {
        const file = files[0];
        if (!file.name.endsWith('.xlsx')) {
            addLogLine(`[!] Error: El archivo maestro debe ser formato Excel (.xlsx).`, 'error');
            return;
        }
        state.masterFile = file;
        
        // Update UI
        const label = elements.masterDropzone.querySelector('.file-name-label');
        label.innerText = file.name;
        label.style.color = '#ffffff';
        label.style.fontWeight = '500';
        
        elements.masterSize.innerText = formatBytes(file.size);
        elements.masterSize.classList.remove('hidden');
        
        addLogLine(`Archivo maestro cargado: ${file.name} (${formatBytes(file.size)})`);
        validateInputs();
    });

    // Movement Files Select handler
    setupDropzone(elements.movementsDropzone, elements.movementsInput, (files) => {
        const newFiles = Array.from(files).filter(file => {
            if (!file.name.endsWith('.xlsx')) {
                addLogLine(`[!] Ignorado archivo no Excel: ${file.name}`, 'warn');
                return false;
            }
            return true;
        });
        
        if (newFiles.length === 0) return;
        
        // Add to our list
        state.movementFiles = [...state.movementFiles, ...newFiles];
        
        // Update UI list
        elements.movementsList.innerHTML = '';
        state.movementFiles.forEach((file) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <span class="file-item-name">📄 ${file.name}</span>
                <span class="file-item-size">${formatBytes(file.size)}</span>
            `;
            elements.movementsList.appendChild(item);
        });
        
        elements.movementsList.classList.remove('hidden');
        const label = elements.movementsDropzone.querySelector('.file-name-label');
        label.innerText = `${state.movementFiles.length} archivo(s) de movimientos seleccionado(s)`;
        label.style.color = '#a5b4fc';
        
        addLogLine(`Cargados ${newFiles.length} archivos de movimientos.`);
        validateInputs();
    });

    // --- Form submit (Pipeline running) ---
    elements.uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!state.masterFile || state.movementFiles.length === 0) return;
        
        // UI states
        elements.btnProcess.disabled = true;
        elements.btnProcess.querySelector('.btn-text').innerText = 'Conciliando...';
        elements.btnProcess.querySelector('.spinner').classList.remove('hidden');
        elements.statusBadge.innerText = 'Procesando en servidor...';
        elements.statusBadge.style.color = '#fbbf24';
        
        elements.statsContainer.classList.add('hidden');
        elements.downloadsContainer.classList.add('hidden');
        elements.previewSection.classList.add('hidden');
        
        elements.logsContainer.innerHTML = '';
        addLogLine('Iniciando carga de archivos y procesamiento...', 'system');
        
        // Build payload
        const formData = new FormData();
        formData.append('master_file', state.masterFile);
        state.movementFiles.forEach(file => {
            formData.append('movement_files', file);
        });
        
        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                // Populate logs
                result.logs.forEach(logMsg => {
                    let logType = 'system';
                    if (logMsg.includes('[!] Error')) logType = 'error';
                    else if (logMsg.includes('[!]')) logType = 'warn';
                    addLogLine(logMsg, logType);
                });
                
                // Show Statistics
                elements.statIngresos.innerText = result.statistics.total_ingresos;
                elements.statRetiros.innerText = result.statistics.total_retiros;
                elements.statMasterAfter.innerText = result.statistics.master_total_after;
                elements.statsContainer.classList.remove('hidden');
                
                // Set download buttons
                elements.dlMovements.href = `/api/download/${result.filenames.movements}`;
                elements.dlMovements.setAttribute('download', result.filenames.movements);
                elements.dlMovements.querySelector('span').innerText = `Movimientos (${result.statistics.total_movements} filas)`;
                
                elements.dlMaster.href = `/api/download/${result.filenames.master}`;
                elements.dlMaster.setAttribute('download', result.filenames.master);
                elements.dlMaster.querySelector('span').innerText = `Nuevo Maestro (${result.statistics.master_total_after} filas)`;
                
                elements.downloadsContainer.classList.remove('hidden');
                
                // Save preview data
                state.previewData.movements = result.preview_movements;
                state.previewData.master = result.preview_master;
                
                // Render preview
                state.currentPreviewTab = 'movements';
                elements.btnShowMovements.classList.add('active');
                elements.btnShowMaster.classList.remove('active');
                renderPreviewTable();
                elements.previewSection.classList.remove('hidden');
                
                elements.statusBadge.innerText = 'Finalizado con éxito';
                elements.statusBadge.style.color = '#10b981';
                addLogLine('Proceso de conciliación finalizado correctamente.', 'system');
            } else {
                elements.statusBadge.innerText = 'Error en ejecución';
                elements.statusBadge.style.color = '#ef4444';
                addLogLine(`[!] Error: ${result.error || 'Ocurrió un error inesperado.'}`, 'error');
                if (result.details) {
                    console.error(result.details);
                    addLogLine(`Detalles:\n${result.details.substring(0, 300)}...`, 'error');
                }
            }
        } catch (error) {
            elements.statusBadge.innerText = 'Error de conexión';
            elements.statusBadge.style.color = '#ef4444';
            addLogLine(`[!] Error de red o comunicación con el servidor.`, 'error');
            console.error(error);
        } finally {
            elements.btnProcess.disabled = false;
            elements.btnProcess.querySelector('.btn-text').innerText = 'Iniciar Conciliación';
            elements.btnProcess.querySelector('.spinner').classList.add('hidden');
        }
    });

    // --- Dynamic Preview Rendering ---
    
    function renderPreviewTable() {
        const data = state.currentPreviewTab === 'movements' 
            ? state.previewData.movements 
            : state.previewData.master;
            
        elements.tableHeaders.innerHTML = '';
        elements.tableBody.innerHTML = '';
        
        if (data.length === 0) {
            elements.tableBody.innerHTML = `<tr><td colspan="11" style="text-align:center;">No hay datos para mostrar</td></tr>`;
            elements.previewCounter.innerText = 'Mostrando 0 de 0 registros';
            return;
        }

        // Get headers from first record keys
        const headers = Object.keys(data[0]);
        headers.forEach(h => {
            const th = document.createElement('th');
            th.innerText = h.replace(/_/g, ' ');
            elements.tableHeaders.appendChild(th);
        });

        // Filter search logic
        const query = elements.previewSearch.value.toLowerCase().trim();
        const filteredData = data.filter(row => {
            if (!query) return true;
            return Object.values(row).some(val => 
                String(val).toLowerCase().includes(query)
            );
        });

        // Append rows
        filteredData.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(h => {
                const td = document.createElement('td');
                const val = row[h];
                td.innerText = val !== null && val !== undefined ? val : '';
                tr.appendChild(td);
            });
            elements.tableBody.appendChild(tr);
        });

        elements.previewCounter.innerText = `Mostrando ${filteredData.length} de ${data.length} registros (Vista previa de las primeras 50 filas)`;
    }

    elements.btnShowMovements.addEventListener('click', () => {
        state.currentPreviewTab = 'movements';
        elements.btnShowMovements.classList.add('active');
        elements.btnShowMaster.classList.remove('active');
        elements.previewSearch.value = '';
        renderPreviewTable();
    });

    elements.btnShowMaster.addEventListener('click', () => {
        state.currentPreviewTab = 'master';
        elements.btnShowMaster.classList.add('active');
        elements.btnShowMovements.classList.remove('active');
        elements.previewSearch.value = '';
        renderPreviewTable();
    });

    elements.previewSearch.addEventListener('input', () => {
        renderPreviewTable();
    });

    // --- Search Cédulas Tab ---
    
    async function triggerSearch() {
        const query = elements.searchInput.value.trim();
        if (!query) return;
        
        elements.searchLoader.classList.remove('hidden');
        elements.searchResultsWrapper.classList.add('hidden');
        elements.searchEmptyState.classList.add('hidden');
        
        try {
            const response = await fetch(`/api/search?cedula=${encodeURIComponent(query)}`);
            const results = await response.json();
            
            elements.searchLoader.classList.add('hidden');
            
            if (results && results.length > 0) {
                elements.resultsCount.innerText = results.length;
                elements.searchResultsList.innerHTML = '';
                
                results.forEach(res => {
                    const card = document.createElement('div');
                    card.className = 'result-row-card';
                    
                    // Render details key values
                    let detailsHtml = '';
                    const fields = [
                        { label: 'Identificación', key: 'NUMERO_IDENTIFICACION_ASEGURADO' },
                        { label: 'Apellidos', key: 'APELLIDOS_ASEGURADO' },
                        { label: 'Nombres', key: 'NOMBRES_ASEGURADO' },
                        { label: 'Cargo', key: 'CARGO' },
                        { label: 'Género', key: 'GENERO' },
                        { label: 'Fecha Nacimiento', key: 'FECHA_NACIMIENTO_ASEGURADO' },
                        { label: 'Valor Asegurado', key: 'VALOR_ASEGURADO_MUERTE' },
                        { label: 'Tipo Novedad', key: 'TIPO_NOVEDAD' },
                        { label: 'Fecha Novedad', key: 'FECHA_NOVEDAD' }
                    ];
                    
                    fields.forEach(f => {
                        const val = res.data[f.key] || res.data[f.key.toLowerCase()] || res.data[f.label.toUpperCase().replace(/ /g, '_')];
                        if (val !== undefined && val !== null) {
                            detailsHtml += `
                                <div class="detail-item">
                                    <span class="detail-label">${f.label}</span>
                                    <span class="detail-value">${val}</span>
                                </div>
                            `;
                        }
                    });
                    
                    // In case columns are different, show other non-null entries
                    if (!detailsHtml) {
                        Object.keys(res.data).forEach(k => {
                            if (res.data[k] !== null && res.data[k] !== '') {
                                detailsHtml += `
                                    <div class="detail-item">
                                        <span class="detail-label">${k.replace(/_/g, ' ')}</span>
                                        <span class="detail-value">${res.data[k]}</span>
                                    </div>
                                `;
                            }
                        });
                    }
                    
                    card.innerHTML = `
                        <div class="result-row-meta">
                            <span class="result-file-title">📁 [${res.folder}] ${res.file}</span>
                            <span class="result-sheet-badge">Hoja: ${res.sheet} | Fila: ${res.row}</span>
                        </div>
                        <div class="result-row-details">
                            ${detailsHtml}
                        </div>
                    `;
                    elements.searchResultsList.appendChild(card);
                });
                
                elements.searchResultsWrapper.classList.remove('hidden');
            } else {
                elements.searchEmptyState.classList.remove('hidden');
            }
        } catch (error) {
            elements.searchLoader.classList.add('hidden');
            addLogLine(`[!] Error de red al buscar la cédula en el servidor.`, 'error');
            console.error(error);
        }
    }

    elements.btnSearch.addEventListener('click', triggerSearch);
    elements.searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            triggerSearch();
        }
    });

    // --- History Files Tab ---
    
    async function loadHistory() {
        elements.historyListBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Cargando archivos del servidor...</td></tr>`;
        
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            elements.historyListBody.innerHTML = '';
            
            if (data.length === 0) {
                elements.historyListBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No hay archivos Excel disponibles en el servidor</td></tr>`;
                return;
            }
            
            data.forEach(item => {
                const tr = document.createElement('tr');
                const dateStr = item.modified || '';
                const typeBadge = item.type === 'output' 
                    ? `<span class="file-type-badge output">Salida</span>`
                    : `<span class="file-type-badge workspace">Maestro/Raíz</span>`;
                    
                tr.innerHTML = `
                    <td style="color: #ffffff; font-weight: 500;">📊 ${item.name}</td>
                    <td>${typeBadge}</td>
                    <td>${formatBytes(item.size)}</td>
                    <td>${dateStr}</td>
                    <td>
                        <a href="/api/download/${encodeURIComponent(item.name)}" download="${item.name}" class="btn btn-secondary" style="width: auto; padding: 0.35rem 0.8rem; font-size: 0.8rem; border-radius: 4px; display: inline-flex;">
                            <span>Descargar</span>
                        </a>
                    </td>
                `;
                elements.historyListBody.appendChild(tr);
            });
        } catch (error) {
            elements.historyListBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--color-error);">Error al cargar archivos de historial</td></tr>`;
            console.error(error);
        }
    }
});
