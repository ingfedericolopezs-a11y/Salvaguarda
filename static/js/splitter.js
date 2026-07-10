/**
 * Independent module: Split ingresos/egresos into blocks of 20.
 * Self-contained — does not touch app.js or the monthly reconciliation flow.
 *
 * Flow: analyze (/api/split) -> confirm gender -> finalize (/api/split/finalize)
 * Output format is identical to the reconciliation output (PlantillaCargue).
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const dropzone   = document.getElementById('split-dropzone');
        const input      = document.getElementById('split_files');
        const filesList  = document.getElementById('split-files-list');
        const btnSplit   = document.getElementById('btn-split');
        const spinner    = document.getElementById('split-spinner');

        const masterZone = document.getElementById('split-master-dropzone');
        const masterInp  = document.getElementById('split_master');
        const masterSize = document.getElementById('split-master-size');

        const idleBox    = document.getElementById('split-idle');
        const loadingBox = document.getElementById('split-loading');
        const successBox = document.getElementById('split-success');

        const gModal   = document.getElementById('split-genero-modal');
        const gTbody   = document.getElementById('split-genero-tbody');
        const gConfirm = document.getElementById('split-genero-confirm');
        const gError   = document.getElementById('split-genero-error');

        if (!dropzone || !input || !btnSplit) return; // tab not present

        let selectedFiles = [];
        let masterFile = null;

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
            selectedFiles = [...selectedFiles, ...valid.filter(f => !existing.has(f.name))];
            renderFileList();
            btnSplit.disabled = selectedFiles.length === 0;
        }

        function setupZone(zone, inp, onFiles) {
            zone.addEventListener('click', () => inp.click());
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
            zone.addEventListener('dragleave', (e) => { e.preventDefault(); zone.classList.remove('dragover'); });
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) onFiles(e.dataTransfer.files);
            });
            inp.addEventListener('change', () => { if (inp.files.length > 0) onFiles(inp.files); });
        }

        setupZone(dropzone, input, addFiles);
        if (masterZone && masterInp) {
            setupZone(masterZone, masterInp, (files) => {
                const f = files[0];
                if (!f.name.toLowerCase().endsWith('.xlsx')) return;
                masterFile = f;
                masterSize.textContent = `✓ ${f.name} (${formatBytes(f.size)})`;
                masterSize.classList.remove('hidden');
            });
        }

        // ── Gender modal: resolves with gender_updates array, or null if cancelled ──
        function askGender(ingresos) {
            gTbody.innerHTML = ingresos.map((p, i) => `
                <tr style="border-bottom:1px solid #313244;">
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.id}</td>
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.apellidos}</td>
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.nombres}</td>
                    <td style="padding:0.55rem 0.75rem; text-align:center;">
                        <label style="margin-right:1rem; color:#a6e3a1; cursor:pointer;">
                            <input type="radio" name="sgen_${i}" value="M" data-id="${p.id}" ${p.genero === 'M' ? 'checked' : ''}> M
                        </label>
                        <label style="color:#f5c2e7; cursor:pointer;">
                            <input type="radio" name="sgen_${i}" value="F" data-id="${p.id}" ${p.genero === 'F' ? 'checked' : ''}> F
                        </label>
                    </td>
                </tr>
            `).join('');
            gError.style.display = 'none';
            gModal.style.display = 'flex';

            return new Promise((resolve) => {
                function onConfirm() {
                    const rows = gTbody.querySelectorAll('tr');
                    const updates = [];
                    let allFilled = true;
                    rows.forEach((row, i) => {
                        const checked = row.querySelector(`input[name="sgen_${i}"]:checked`);
                        const id = row.querySelector('input[type="radio"]')?.dataset.id;
                        if (!checked) allFilled = false;
                        else updates.push({ id, genero: checked.value });
                    });
                    if (!allFilled) {
                        gError.textContent = '⚠️ Selecciona el género de todas las personas.';
                        gError.style.display = 'block';
                        return;
                    }
                    gConfirm.removeEventListener('click', onConfirm);
                    gModal.style.display = 'none';
                    resolve(updates);
                }
                gConfirm.addEventListener('click', onConfirm);
            });
        }

        async function finalize(genderUpdates) {
            const resp = await fetch('/api/split/finalize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gender_updates: genderUpdates })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Error al generar archivos');
            return data;
        }

        function showSuccess(data) {
            document.getElementById('split-total-ingresos').textContent = data.total_ingresos;
            document.getElementById('split-total-egresos').textContent  = data.total_egresos;
            document.getElementById('split-files-ingresos').textContent = data.ingresos_files;
            document.getElementById('split-files-egresos').textContent  = data.egresos_files;

            document.getElementById('split-download-zip').href =
                `/api/split/download/${encodeURIComponent(data.zip_filename)}`;

            document.getElementById('split-file-list').innerHTML = data.files.map(f => {
                const color = f.category === 'Ingresos' ? '#a6e3a1' : '#f38ba8';
                return `<div style="display:flex; justify-content:space-between; padding:0.4rem 0.6rem; border-bottom:1px solid #313244;">
                    <span style="color:${color};">📄 ${f.filename}</span>
                    <a href="/api/split/download/${encodeURIComponent(f.filename)}" style="color:#89b4fa; text-decoration:none;">descargar</a>
                </div>`;
            }).join('');

            loadingBox.style.display = 'none';
            successBox.style.display = 'block';
        }

        btnSplit.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;

            btnSplit.disabled = true;
            spinner.classList.remove('hidden');
            idleBox.style.display = 'none';
            successBox.style.display = 'none';
            loadingBox.style.display = 'block';

            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('split_files', f));
            if (masterFile) formData.append('split_master', masterFile);

            try {
                // Step 1: analyze
                const resp = await fetch('/api/split', { method: 'POST', body: formData });
                const analysis = await resp.json();
                if (!resp.ok) throw new Error(analysis.error || 'Error al analizar archivos');

                // Step 2: gender confirmation for ingresos (if any)
                let genderUpdates = [];
                const ingresos = analysis.ingresos_para_genero || [];
                if (ingresos.length > 0) {
                    loadingBox.style.display = 'none';
                    genderUpdates = await askGender(ingresos);
                    loadingBox.style.display = 'block';
                }

                // Step 3: finalize
                const data = await finalize(genderUpdates);
                showSuccess(data);
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
