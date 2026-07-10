/**
 * Independent module: Split ingresos/egresos into blocks of 20.
 * Self-contained — does not touch app.js or the monthly reconciliation flow.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const dropzone   = document.getElementById('split-dropzone');
        const input      = document.getElementById('split_files');
        const filesList  = document.getElementById('split-files-list');
        const btnSplit   = document.getElementById('btn-split');
        const spinner    = document.getElementById('split-spinner');

        const idleBox    = document.getElementById('split-idle');
        const loadingBox = document.getElementById('split-loading');
        const successBox = document.getElementById('split-success');

        if (!dropzone || !input || !btnSplit) return; // tab not present

        let selectedFiles = [];

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function renderFileList() {
            if (selectedFiles.length === 0) {
                filesList.classList.add('hidden');
                filesList.innerHTML = '';
                return;
            }
            const total = selectedFiles.reduce((s, f) => s + f.size, 0);
            filesList.innerHTML = selectedFiles.map((f, i) => `
                <div class="file-item">
                    <span class="file-item-index">${i + 1}</span>
                    <span class="file-item-name">${f.name}</span>
                    <span class="file-item-size">${formatBytes(f.size)}</span>
                </div>
            `).join('') + `<div class="file-items-summary">✓ ${selectedFiles.length} archivo(s) - ${formatBytes(total)}</div>`;
            filesList.classList.remove('hidden');
        }

        function addFiles(fileArr) {
            const valid = Array.from(fileArr).filter(f => f.name.toLowerCase().endsWith('.xlsx'));
            const existing = new Set(selectedFiles.map(f => f.name));
            const added = valid.filter(f => !existing.has(f.name));
            selectedFiles = [...selectedFiles, ...added];
            renderFileList();
            btnSplit.disabled = selectedFiles.length === 0;
        }

        // Dropzone wiring
        dropzone.addEventListener('click', () => input.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
        });
        input.addEventListener('change', () => { if (input.files.length > 0) addFiles(input.files); });

        // Process
        btnSplit.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;

            btnSplit.disabled = true;
            spinner.classList.remove('hidden');
            idleBox.style.display = 'none';
            successBox.style.display = 'none';
            loadingBox.style.display = 'block';

            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('split_files', f));

            try {
                const resp = await fetch('/api/split', { method: 'POST', body: formData });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Error al dividir archivos');

                document.getElementById('split-total-ingresos').textContent = data.total_ingresos;
                document.getElementById('split-total-egresos').textContent  = data.total_egresos;
                document.getElementById('split-files-ingresos').textContent = data.ingresos_files;
                document.getElementById('split-files-egresos').textContent  = data.egresos_files;

                const zipLink = document.getElementById('split-download-zip');
                zipLink.href = `/api/split/download/${encodeURIComponent(data.zip_filename)}`;

                const listBox = document.getElementById('split-file-list');
                listBox.innerHTML = data.files.map(f => {
                    const color = f.category === 'Ingresos' ? '#a6e3a1' : '#f38ba8';
                    return `<div style="display:flex; justify-content:space-between; padding:0.4rem 0.6rem; border-bottom:1px solid #313244;">
                        <span style="color:${color};">📄 ${f.filename}</span>
                        <a href="/api/split/download/${encodeURIComponent(f.filename)}" style="color:#89b4fa; text-decoration:none;">descargar</a>
                    </div>`;
                }).join('');

                loadingBox.style.display = 'none';
                successBox.style.display = 'block';
            } catch (err) {
                loadingBox.style.display = 'none';
                idleBox.style.display = 'block';
                alert('❌ ' + err.message);
            } finally {
                spinner.classList.add('hidden');
                btnSplit.disabled = false;
            }
        });
    });
})();
