/**
 * Screenshot to Code Generator — Frontend
 * ============================================
 * Pipeline: Upload → Detection → Parsing → Skeleton → AI Refinement
 * With framework selection, code tabs, and localStorage history.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── DOM Elements ──
    const dropZone       = document.getElementById('drop-zone');
    const fileInput      = document.getElementById('file-input');
    const preview        = document.getElementById('preview');
    const previewImg     = document.getElementById('preview-img');
    const removeBtn      = document.getElementById('remove-btn');
    const genBtn         = document.getElementById('gen-btn');
    const output         = document.getElementById('output-section');
    const outputHint     = document.getElementById('output-hint');
    const loading        = document.getElementById('loading');
    const loaderTitle    = document.getElementById('loader-title');
    const loaderSub      = document.getElementById('loader-sub');
    const codeContent    = document.getElementById('code-content');
    const copyBtn        = document.getElementById('copy-btn');
    const copyText       = document.getElementById('copy-text');
    const historySection = document.getElementById('history-section');
    const historyList    = document.getElementById('history-list');
    const clearHistBtn   = document.getElementById('clear-history-btn');
    const codeFilename   = document.getElementById('code-filename');

    // Pipeline Elements
    const pipelineSection = document.getElementById('pipeline-section');
    const pipelineBadge   = document.getElementById('pipeline-badge');
    const detectionInfo   = document.getElementById('detection-info');
    const detectionStats  = document.getElementById('detection-stats');
    const detectionTiming = document.getElementById('detection-timing');
    const codeTabs        = document.getElementById('code-tabs');
    const tabSkeleton     = document.getElementById('tab-skeleton');
    const tabRefined      = document.getElementById('tab-refined');

    // Framework selector
    const fwOptions = document.querySelectorAll('.fw-option');

    let selectedFile = null;
    let currentThumbnail = null;
    let selectedFramework = 'html-css';
    let currentSkeletonCode = '';
    let currentRefinedCode = '';

    const STORAGE_KEY = 'screenshot-to-code-history';
    const MAX_HISTORY = 20;

    // =========================================================
    // Framework Selector
    // =========================================================
    fwOptions.forEach(option => {
        option.addEventListener('click', () => {
            fwOptions.forEach(o => o.classList.remove('active'));
            option.classList.add('active');
            const radio = option.querySelector('input[type="radio"]');
            radio.checked = true;
            selectedFramework = radio.value;
        });
    });

    // =========================================================
    // Toast
    // =========================================================
    function toast(msg, type = 'success') {
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    }

    // =========================================================
    // Escape HTML
    // =========================================================
    function esc(str) {
        const d = document.createElement('div');
        d.appendChild(document.createTextNode(str));
        return d.innerHTML;
    }

    // =========================================================
    // History — localStorage
    // =========================================================
    function getHistory() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch {
            return [];
        }
    }

    function saveHistory(items) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
        } catch (e) {
            if (e.name === 'QuotaExceededError') {
                items = items.slice(0, Math.floor(items.length / 2));
                localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
            }
        }
    }

    function addToHistory(thumbnail, code, framework) {
        const items = getHistory();
        items.unshift({
            id: Date.now().toString(),
            date: new Date().toLocaleString(),
            thumbnail: thumbnail,
            code: code,
            framework: framework,
            preview: code.substring(0, 120).replace(/\s+/g, ' ')
        });
        if (items.length > MAX_HISTORY) items.length = MAX_HISTORY;
        saveHistory(items);
        renderHistory();
    }

    function deleteFromHistory(id) {
        const items = getHistory().filter(item => item.id !== id);
        saveHistory(items);
        renderHistory();
        toast('Removed from history');
    }

    function clearHistory() {
        localStorage.removeItem(STORAGE_KEY);
        renderHistory();
        toast('History cleared');
    }

    function loadFromHistory(id) {
        const items = getHistory();
        const item = items.find(i => i.id === id);
        if (!item) return;

        codeContent.innerHTML = esc(item.code);
        output.style.display = 'block';
        codeTabs.style.display = 'none';

        // Update output hint + filename based on saved framework
        const fw = item.framework || 'html-css';
        updateOutputUI(fw);

        setTimeout(() => output.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);
        toast('Loaded from history');
    }

    function renderHistory() {
        const items = getHistory();

        if (items.length === 0) {
            historySection.style.display = 'none';
            return;
        }

        historySection.style.display = 'block';
        historyList.innerHTML = '';

        items.forEach(item => {
            const fwLabel = item.framework === 'react-tailwind' ? '⚛️ React' : '🌐 HTML';
            const el = document.createElement('div');
            el.className = 'history-item';
            el.innerHTML = `
                ${item.thumbnail
                    ? `<img class="history-thumb" src="${item.thumbnail}" alt="Thumbnail">`
                    : `<div class="history-thumb" style="background:var(--surface-hover);display:flex;align-items:center;justify-content:center;font-size:0.65rem;color:var(--text-dim);">📷</div>`
                }
                <div class="history-info">
                    <div class="history-date">${item.date} · ${fwLabel}</div>
                    <div class="history-preview">${esc(item.preview || '')}</div>
                </div>
                <div class="history-actions">
                    <button class="history-load-btn" data-id="${item.id}">Load</button>
                    <button class="history-del-btn" data-id="${item.id}">✕</button>
                </div>
            `;
            historyList.appendChild(el);
        });

        historyList.querySelectorAll('.history-load-btn').forEach(btn => {
            btn.addEventListener('click', () => loadFromHistory(btn.dataset.id));
        });
        historyList.querySelectorAll('.history-del-btn').forEach(btn => {
            btn.addEventListener('click', () => deleteFromHistory(btn.dataset.id));
        });
    }

    clearHistBtn.addEventListener('click', () => {
        if (confirm('Delete all history? This cannot be undone.')) {
            clearHistory();
        }
    });

    // =========================================================
    // Update output section based on framework
    // =========================================================
    function updateOutputUI(framework) {
        if (framework === 'react-tailwind') {
            outputHint.innerHTML = '👉 Add this code to your <code>App.jsx</code>';
            codeFilename.textContent = 'Component.jsx';
        } else {
            outputHint.innerHTML = '👉 Add this code in your <code>index.html</code>';
            codeFilename.textContent = 'generated-page.html';
        }
    }

    // =========================================================
    // Pipeline Stages UI
    // =========================================================
    const stageNames = ['Detect', 'Parse', 'Generate', 'Refine'];

    function resetPipelineUI() {
        for (let i = 1; i <= 4; i++) {
            const dot = document.getElementById(`stage-${i}`);
            const label = document.getElementById(`stage-${i}-label`);
            dot.className = 'stage-dot';
            label.className = 'stage-label';
            label.textContent = stageNames[i - 1];
        }
        pipelineBadge.textContent = 'Processing';
        pipelineBadge.className = 'panel-badge';
        detectionInfo.style.display = 'none';
    }

    function activateStage(stageNum) {
        const dot = document.getElementById(`stage-${stageNum}`);
        const label = document.getElementById(`stage-${stageNum}-label`);
        dot.classList.add('active');
        label.classList.add('active');
    }

    function completeStage(stageNum, timeMs) {
        const dot = document.getElementById(`stage-${stageNum}`);
        const label = document.getElementById(`stage-${stageNum}-label`);
        dot.classList.remove('active');
        dot.classList.add('done');
        dot.textContent = '✓';
        label.classList.remove('active');
        label.classList.add('done');
        if (timeMs !== undefined) {
            label.textContent = `${stageNames[stageNum - 1]} (${timeMs}ms)`;
        }
    }

    function showDetectionInfo(detection) {
        if (!detection) return;

        const components = detection.components || [];
        const stages = detection.stages || [];
        const totalTime = detection.total_time_ms || 0;

        // Count component types
        const counts = {};
        components.forEach(c => {
            counts[c.type] = (counts[c.type] || 0) + 1;
        });

        const typeIcons = {
            button: '🔘',
            input: '📝',
            text: '📄',
            image: '🖼️',
            container: '📦'
        };

        // Build stats HTML
        let statsHtml = `<div class="detection-stat"><span class="stat-icon">🔍</span> Total: <span class="stat-value">${components.length}</span></div>`;
        for (const [type, count] of Object.entries(counts)) {
            const icon = typeIcons[type] || '❓';
            statsHtml += `<div class="detection-stat"><span class="stat-icon">${icon}</span> ${type}: <span class="stat-value">${count}</span></div>`;
        }
        detectionStats.innerHTML = statsHtml;

        // Build timing HTML
        let timingHtml = '';
        stages.forEach(stage => {
            timingHtml += `<span>${stage.name}: ${stage.duration_ms}ms</span>`;
        });
        timingHtml += `<span style="color:var(--primary);font-weight:600;">Total: ${totalTime}ms</span>`;
        detectionTiming.innerHTML = timingHtml;

        detectionInfo.style.display = 'block';

        // Mark pipeline as complete
        pipelineBadge.textContent = 'Complete';
        pipelineBadge.className = 'panel-badge success';
    }

    // =========================================================
    // Code Tabs (Skeleton vs Refined)
    // =========================================================
    tabSkeleton.addEventListener('click', () => {
        tabSkeleton.classList.add('active');
        tabRefined.classList.remove('active');
        codeContent.innerHTML = esc(currentSkeletonCode);
        codeFilename.textContent = selectedFramework === 'react-tailwind' ? 'Skeleton.jsx' : 'skeleton.html';
    });

    tabRefined.addEventListener('click', () => {
        tabRefined.classList.add('active');
        tabSkeleton.classList.remove('active');
        codeContent.innerHTML = esc(currentRefinedCode);
        updateOutputUI(selectedFramework);
    });

    // =========================================================
    // Create thumbnail
    // =========================================================
    function createThumbnail(file) {
        return new Promise(resolve => {
            const reader = new FileReader();
            reader.onload = e => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const MAX = 120;
                    let w = img.width, h = img.height;
                    if (w > h) { h = Math.round(h * MAX / w); w = MAX; }
                    else { w = Math.round(w * MAX / h); h = MAX; }
                    canvas.width = w;
                    canvas.height = h;
                    canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                    resolve(canvas.toDataURL('image/jpeg', 0.6));
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    // =========================================================
    // File handling
    // =========================================================
    function handleFile(file) {
        if (!file || !file.type.startsWith('image/')) {
            toast('Please select an image file.', 'error');
            return;
        }
        if (file.size > 16 * 1024 * 1024) {
            toast('File too large. Max 16 MB.', 'error');
            return;
        }
        selectedFile = file;
        createThumbnail(file).then(thumb => { currentThumbnail = thumb; });

        const reader = new FileReader();
        reader.onload = e => {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
            dropZone.style.display = 'none';
            genBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function removeFile() {
        selectedFile = null;
        currentThumbnail = null;
        fileInput.value = '';
        previewImg.src = '';
        preview.style.display = 'none';
        dropZone.style.display = 'block';
        genBtn.disabled = true;
        output.style.display = 'none';
        pipelineSection.style.display = 'none';
    }

    // =========================================================
    // Events
    // =========================================================
    fileInput.addEventListener('change', e => {
        if (e.target.files.length) handleFile(e.target.files[0]);
    });

    removeBtn.addEventListener('click', removeFile);

    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    dropZone.addEventListener('click', e => {
        if (!e.target.closest('.browse-link')) fileInput.click();
    });

    // =========================================================
    // Generate Code
    // =========================================================
    function updateRateLimitUI(rateInfo) {
        if (!rateInfo) return;
        const remaining = rateInfo.remaining;
        const limit = rateInfo.limit;
        if (remaining <= 1) {
            genBtn.innerHTML = `
                <svg viewBox="0 0 20 20" fill="none" class="gen-icon">
                    <path d="M10 2L3 10h4v8l7-8h-4V2z" fill="currentColor"/>
                </svg>
                Generate Code · ${remaining}/${limit} left`;
        }
    }

    async function simulatePipelineStages() {
        // Simulate stage progression for visual feedback
        // The real timing comes from the API response
        for (let i = 1; i <= 4; i++) {
            activateStage(i);
            const delay = i === 4 ? 3000 : (i === 1 ? 800 : 200);
            await new Promise(resolve => setTimeout(resolve, delay));
            if (i < 4) completeStage(i);
        }
    }

    genBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // Show loading
        loading.style.display = 'flex';
        genBtn.disabled = true;

        loaderTitle.textContent = 'Running detection pipeline…';
        loaderSub.textContent = 'Detecting components → Building layout → Generating code';

        // Show pipeline stages panel
        pipelineSection.style.display = 'block';
        resetPipelineUI();

        // Start stage animation (non-blocking)
        simulatePipelineStages();

        try {
            const form = new FormData();
            form.append('image', selectedFile);
            form.append('framework', selectedFramework);

            const res = await fetch('/generate-code', { method: 'POST', body: form });
            const ct = res.headers.get('content-type') || '';
            if (!ct.includes('application/json')) throw new Error('Server error. Please try again.');

            const data = await res.json();

            // Handle rate limit
            if (res.status === 429) {
                const wait = data.rate_limit?.reset_in || 60;
                toast(`⏳ Rate limit reached! Wait ${wait}s before trying again.`, 'error');
                return;
            }

            if (!res.ok || data.error) throw new Error(data.error || 'Generation failed.');

            const generatedCode = data.generated_code || '';

            // Update UI for framework
            updateOutputUI(selectedFramework);

            if (data.detection) {
                // Complete all pipeline stages
                for (let i = 1; i <= 4; i++) {
                    completeStage(i, data.detection.stages?.[i - 1]?.duration_ms);
                }

                // Show detection info
                showDetectionInfo(data.detection);

                // Store both versions
                currentSkeletonCode = data.skeleton_code || '';
                currentRefinedCode = generatedCode;

                // Show code tabs
                codeTabs.style.display = 'flex';
                tabRefined.classList.add('active');
                tabSkeleton.classList.remove('active');
            } else {
                currentSkeletonCode = '';
                currentRefinedCode = generatedCode;
                codeTabs.style.display = 'none';
            }

            // Show code
            codeContent.innerHTML = esc(generatedCode);
            output.style.display = 'block';

            // Update rate limit info
            if (data.rate_limit) {
                updateRateLimitUI(data.rate_limit);
                const r = data.rate_limit.remaining;
                if (r === 0) {
                    toast(`Code generated! ⚠️ You've used all ${data.rate_limit.limit} generations. Wait 2 min.`, 'success');
                } else {
                    toast(`Code generated! 🎉 (${r} generation${r !== 1 ? 's' : ''} remaining)`, 'success');
                }
            } else {
                toast('Code generated successfully! 🎉');
            }

            // Save to history
            addToHistory(currentThumbnail, generatedCode, selectedFramework);

            setTimeout(() => output.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);

        } catch (err) {
            toast(err.message || 'Something went wrong.', 'error');
        } finally {
            loading.style.display = 'none';
            genBtn.disabled = false;
        }
    });

    // =========================================================
    // Copy
    // =========================================================
    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(codeContent.textContent);
            copyBtn.classList.add('copied');
            copyText.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyText.textContent = 'Copy';
            }, 2000);
        } catch {
            toast('Copy failed.', 'error');
        }
    });

    // =========================================================
    // Init
    // =========================================================
    renderHistory();
});
