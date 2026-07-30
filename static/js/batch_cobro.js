/**
 * Independent module: Batch cobro — one plantilla per month in a range.
 * Self-contained — does not touch app.js or other modules.
 *
 * Flow: analyze (/api/batch-cobro) -> confirm gender -> finalize (/api/batch-cobro/finalize)
 */
(function () {
    'use strict';

    const MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

    document.addEventListener('DOMContentLoaded', () => {
        const dropzone   = document.getElementById('batch-dropzone');
        const input      = document.getElementById('batch_files');
        const filesList  = document.getElementById('batch-files-list');
        const btnBatch   = document.getElementById('btn-batch');
        const spinner    = document.getElementById('batch-spinner');

        const masterZone = document.getElementById('batch-master-dropzone');
        const masterInp  = document.getElementById('batch_master');
        const masterSize = document.getElementById('batch-master-size');

        const startMes = document.getElementById('batch-start-mes');
        const startAnio = document.getElementById('batch-start-anio');
        const endMes = document.getElementById('batch-end-mes');
        const endAnio = document.getElementById('batch-end-anio');

        const idleBox    = document.getElementById('batch-idle');
        const loadingBox = document.getElementById('batch-loading');
        const successBox = document.getElementById('batch-success');

        const gModal   = document.getElementById('batch-genero-modal');
        const gTbody   = document.getElementById('batch-genero-tbody');
        const gConfirm = document.getElementById('batch-genero-confirm');
        const gError   = document.getElementById('batch-genero-error');

        if (!dropzone || !input || !btnBatch) return;

        let selectedFiles = [];
        let masterFile = null;

        // Populate month selects
        for (let m = 1; m <= 12; m++) {
            startMes.insertAdjacentHTML('beforeend', `<option value="${m}">${MESES[m]}</option>`);
            endMes.insertAdjacentHTML('beforeend', `<option value="${m}">${MESES[m]}</option>`);
        }
        const now = new Date();
        startMes.value = now.getMonth() + 1;
        startAnio.value = now.getFullYear();
        endMes.value = now.getMonth() + 1;
        endAnio.value = now.getFullYear();

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function renderFileList() {
            if (selectedFiles.length === 0) { filesList.classList.add('hidden'); filesList.innerHTML = ''; return; }
            const total = selectedFiles.reduce((s, f) => s + f.size, 0);
            filesList.innerHTML = selectedFiles.map((f, i) => `
                <div class="file-item">
                    <span class="file-item-index">${i + 1}</span>
                    <span class="file-item-name">${f.name}</span>
                    <span class="file-item-size">${formatBytes(f.size)}</span>
                </div>`).join('') +
                `<div class="file-items-summary">✓ ${selectedFiles.length} archivo(s) - ${formatBytes(total)}</div>`;
            filesList.classList.remove('hidden');
        }

        function addFiles(fileArr) {
            const valid = Array.from(fileArr).filter(f => f.name.toLowerCase().endsWith('.xlsx'));
            const existing = new Set(selectedFiles.map(f => f.name));
            selectedFiles = [...selectedFiles, ...valid.filter(f => !existing.has(f.name))];
            renderFileList();
            btnBatch.disabled = selectedFiles.length === 0;
        }

        function setupZone(zone, inp, onFiles) {
            zone.addEventListener('click', () => inp.click());
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
            zone.addEventListener('dragleave', (e) => { e.preventDefault(); zone.classList.remove('dragover'); });
            zone.addEventListener('drop', (e) => {
                e.preventDefault(); zone.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) onFiles(e.dataTransfer.files);
            });
            inp.addEventListener('change', () => { if (inp.files.length > 0) onFiles(inp.files); });
        }

        setupZone(dropzone, input, addFiles);
        setupZone(masterZone, masterInp, (files) => {
            const f = files[0];
            if (!f.name.toLowerCase().endsWith('.xlsx')) return;
            masterFile = f;
            masterSize.textContent = `✓ ${f.name} (${formatBytes(f.size)})`;
            masterSize.classList.remove('hidden');
        });

        function askGender(ingresos) {
            gTbody.innerHTML = ingresos.map((p, i) => `
                <tr style="border-bottom:1px solid #313244;">
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.id}</td>
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.apellidos}</td>
                    <td style="padding:0.55rem 0.75rem; color:#cdd6f4;">${p.nombres}</td>
                    <td style="padding:0.55rem 0.75rem; text-align:center;">
                        <label style="margin-right:1rem; color:#a6e3a1; cursor:pointer;">
                            <input type="radio" name="bgen_${i}" value="M" data-id="${p.id}" ${p.genero === 'M' ? 'checked' : ''}> M
                        </label>
                        <label style="color:#f5c2e7; cursor:pointer;">
                            <input type="radio" name="bgen_${i}" value="F" data-id="${p.id}" ${p.genero === 'F' ? 'checked' : ''}> F
                        </label>
                    </td>
                </tr>`).join('');
            gError.style.display = 'none';
            gModal.style.display = 'flex';
            return new Promise((resolve) => {
                function onConfirm() {
                    const rows = gTbody.querySelectorAll('tr');
                    const updates = [];
                    let allFilled = true;
                    rows.forEach((row, i) => {
                        const checked = row.querySelector(`input[name="bgen_${i}"]:checked`);
                        const id = row.querySelector('input[type="radio"]')?.dataset.id;
                        if (!checked) allFilled = false; else updates.push({ id, genero: checked.value });
                    });
                    if (!allFilled) { gError.textContent = '⚠️ Selecciona el género de todas las personas.'; gError.style.display = 'block'; return; }
                    gConfirm.removeEventListener('click', onConfirm);
                    gModal.style.display = 'none';
                    resolve(updates);
                }
                gConfirm.addEventListener('click', onConfirm);
            });
        }

        async function finalize(genderUpdates) {
            const resp = await fetch('/api/batch-cobro/finalize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gender_updates: genderUpdates,
                    start_mes: parseInt(startMes.value), start_anio: parseInt(startAnio.value),
                    end_mes: parseInt(endMes.value), end_anio: parseInt(endAnio.value)
                })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Error al generar las cuentas');
            return data;
        }

        function showSuccess(data) {
            document.getElementById('batch-download-zip').href =
                `/api/batch-cobro/download/${encodeURIComponent(data.zip_filename)}`;
            document.getElementById('batch-file-list').innerHTML = data.files.map(f => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.6rem; border-bottom:1px solid #313244;">
                    <span style="color:#cdd6f4;">📄 ${f.mes} ${f.anio} <span style="color:#6c7086; font-size:0.8rem;">(${f.total} personas · cobro ${f.fecha_cobro})</span></span>
                    <a href="/api/batch-cobro/download/${encodeURIComponent(f.filename)}" style="color:#89b4fa; text-decoration:none;">descargar</a>
                </div>`).join('');
            loadingBox.style.display = 'none';
            successBox.style.display = 'block';
        }

        btnBatch.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;
            // Validate range
            const s = parseInt(startAnio.value) * 100 + parseInt(startMes.value);
            const e = parseInt(endAnio.value) * 100 + parseInt(endMes.value);
            if (!startAnio.value || !endAnio.value || s > e) {
                alert('⚠️ Revisa el rango de meses: la fecha inicial debe ser anterior o igual a la final.');
                return;
            }

            btnBatch.disabled = true;
            spinner.classList.remove('hidden');
            idleBox.style.display = 'none';
            successBox.style.display = 'none';
            loadingBox.style.display = 'block';

            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('batch_files', f));
            if (masterFile) formData.append('batch_master', masterFile);

            try {
                const resp = await fetch('/api/batch-cobro', { method: 'POST', body: formData });
                const analysis = await resp.json();
                if (!resp.ok) throw new Error(analysis.error || 'Error al analizar archivos');

                let genderUpdates = [];
                const ingresos = analysis.ingresos_para_genero || [];
                if (ingresos.length > 0) {
                    loadingBox.style.display = 'none';
                    genderUpdates = await askGender(ingresos);
                    loadingBox.style.display = 'block';
                }

                const data = await finalize(genderUpdates);
                showSuccess(data);
            } catch (err) {
                loadingBox.style.display = 'none';
                idleBox.style.display = 'block';
                alert('❌ ' + err.message);
            } finally {
                spinner.classList.add('hidden');
                btnBatch.disabled = false;
            }
        });
    });
})();
