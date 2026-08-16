/**
 * AgriCare — single-page detect experience
 * crop → leaf photo → diagnosis + treatment plan
 */
document.addEventListener('DOMContentLoaded', () => {

    // ─── ELEMENTS ───
    const cropSelect    = document.getElementById('cropSelect');
    const cropHint      = document.getElementById('cropHint');
    const uploadZone    = document.getElementById('uploadZone');
    const fileInput     = document.getElementById('fileInput');
    const previewArea   = document.getElementById('previewArea');
    const previewImage  = document.getElementById('previewImage');
    const removeImage   = document.getElementById('removeImage');
    const fileName      = document.getElementById('fileName');
    const fileSize      = document.getElementById('fileSize');
    const detectBtn     = document.getElementById('detectBtn');
    const btnRequirement= document.getElementById('btnRequirement');
    const guestNote     = document.getElementById('guestNote');
    const scanLine      = document.getElementById('scanLine');
    const step1         = document.getElementById('step1');
    const step2         = document.getElementById('step2');

    const quotaScans    = document.getElementById('quotaScans');
    const quotaAi       = document.getElementById('quotaAi');

    const loadingOverlay= document.getElementById('loadingOverlay');
    const loadingTitle  = document.getElementById('loadingTitle');
    const loadingSub    = document.getElementById('loadingSub');

    const reportEmpty   = document.getElementById('reportEmpty');
    const report        = document.getElementById('report');
    const scanAgainBtn  = document.getElementById('scanAgainBtn');
    const downloadPdfBtn= document.getElementById('downloadPdfBtn');

    const limitModal    = document.getElementById('trialLimitModal');
    const limitClose    = document.getElementById('limitClose');
    const limitTitle    = document.getElementById('limitTitle');
    const limitBody     = document.getElementById('limitBody');
    const toastHost     = document.getElementById('toastHost');

    const GEMINI_ON = window.GEMINI_ENABLED === true;

    let selectedFile = null;
    let currentUser  = null;
    let lastResult   = null;

    // ─── AMBIENT LEAVES ───
    (function drift() {
        const host = document.getElementById('leafDrift');
        if (!host || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const glyphs = ['🌿', '🍃', '🌱'];
        for (let i = 0; i < 7; i++) {
            const el = document.createElement('span');
            el.className = 'floating-leaf';
            el.textContent = glyphs[i % glyphs.length];
            el.style.left = `${6 + Math.random() * 88}vw`;
            el.style.animationDuration = `${20 + Math.random() * 18}s`;
            el.style.animationDelay = `${-Math.random() * 30}s`;
            el.style.fontSize = `${0.9 + Math.random() * 1.1}rem`;
            host.appendChild(el);
        }
    })();

    // ─── USER MENU ───
    const userChip = document.getElementById('userChip');
    const userChipBtn = document.getElementById('userChipBtn');
    if (userChip && userChipBtn) {
        userChipBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userChip.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (!userChip.contains(e.target)) userChip.classList.remove('open');
        });
    }

    // ─── QUOTA ───
    function renderUsage(u) {
        if (!u) return;
        quotaScans.querySelector('span').textContent = `${u.scans_left} of ${u.scans_limit} scans left today`;
        quotaScans.classList.toggle('low', u.scans_left <= 3);

        quotaAi.querySelector('span').textContent = `${u.gemini_left} of ${u.gemini_limit} unlisted-crop checks left`;
        quotaAi.classList.toggle('low', u.gemini_left <= 1);

        guestNote.innerHTML = u.signed_in
            ? 'Signed in · scans saved to your history'
            : '<a href="/auth?next=/">Sign in</a> for 100 scans a day + saved history';
    }

    async function loadMe() {
        try {
            const res = await fetch('/api/me');
            const data = await res.json();
            currentUser = data.user;
            if (data.just_logged_in && currentUser) {
                showToast(`Welcome, ${currentUser.full_name.split(' ')[0]}! You're signed in.`, 'success');
            }
            renderUsage(data.usage);
        } catch (e) {
            console.error('Could not load account info:', e);
        }
    }
    loadMe();

    // ─── CROP PICKER ───
    // A searchable dropdown that writes through to the hidden <select>, so the
    // rest of the page keeps reading cropSelect.value / listening for 'change'.
    (function cropPicker() {
        const box     = document.getElementById('cropBox');
        const trigger = document.getElementById('cropTrigger');
        const panel   = document.getElementById('cropPanel');
        const search  = document.getElementById('cropSearch');
        const current = document.getElementById('cropCurrent');
        const empty   = document.getElementById('cropEmpty');
        if (!box || !trigger || !panel) return;

        const items = Array.from(panel.querySelectorAll('.cropbox-item'));
        let cursor = -1;

        const visible = () => items.filter(i => !i.hidden);

        function open() {
            box.classList.add('open');
            trigger.setAttribute('aria-expanded', 'true');
            search.value = '';
            filter('');
            cursor = items.findIndex(i => i.classList.contains('selected'));
            setCursor(cursor);
            setTimeout(() => search.focus(), 40);
        }
        function close() {
            box.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
            items.forEach(i => i.classList.remove('cursor'));
            cursor = -1;
        }
        function toggle() { box.classList.contains('open') ? close() : open(); }

        function filter(q) {
            const term = q.trim().toLowerCase();
            let shown = 0;
            items.forEach(i => {
                if (i.classList.contains('other')) return;   // always visible
                const match = i.dataset.name.toLowerCase().includes(term);
                i.hidden = !match;
                if (match) shown++;
            });
            empty.classList.toggle('show', shown === 0);
        }

        function setCursor(idx) {
            const vis = visible();
            items.forEach(i => i.classList.remove('cursor'));
            if (!vis.length) return;
            const clamped = Math.max(0, Math.min(idx, vis.length - 1));
            vis[clamped].classList.add('cursor');
            vis[clamped].scrollIntoView({ block: 'nearest' });
            cursor = items.indexOf(vis[clamped]);
        }

        function choose(item) {
            cropSelect.value = item.dataset.value;
            items.forEach(i => i.classList.toggle('selected', i === item));
            current.innerHTML = '';
            const ci = document.createElement('span');
            ci.className = 'ci';
            ci.textContent = item.dataset.icon;
            const cn = document.createElement('span');
            cn.className = 'cn';
            cn.textContent = item.dataset.name;
            current.append(ci, cn);
            // Let the existing change handler run exactly as before.
            cropSelect.dispatchEvent(new Event('change', { bubbles: true }));
            close();
            trigger.focus();
        }

        trigger.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });
        items.forEach(i => i.addEventListener('click', () => choose(i)));
        search.addEventListener('input', () => { filter(search.value); setCursor(0); });

        search.addEventListener('keydown', (e) => {
            const vis = visible();
            const at = vis.indexOf(items[cursor]);
            if (e.key === 'ArrowDown')      { e.preventDefault(); setCursor(at + 1); }
            else if (e.key === 'ArrowUp')   { e.preventDefault(); setCursor(at - 1); }
            else if (e.key === 'Enter')     { e.preventDefault(); if (items[cursor]) choose(items[cursor]); }
            else if (e.key === 'Escape')    { e.preventDefault(); close(); trigger.focus(); }
        });

        trigger.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
                e.preventDefault(); open();
            }
        });

        document.addEventListener('click', (e) => { if (!box.contains(e.target)) close(); });
    })();

    cropSelect.addEventListener('change', () => {
        const v = cropSelect.value;
        cropHint.style.display = 'flex';
        if (v === 'other') {
            if (GEMINI_ON) {
                cropHint.className = 'field-hint';
                cropHint.innerHTML = '<i class="bi bi-search"></i> We’ll identify the crop and disease from your photo automatically.';
            } else {
                cropHint.className = 'field-hint warn';
                cropHint.innerHTML = '<i class="bi bi-exclamation-circle"></i> Unlisted-crop identification isn’t configured right now — please pick a listed crop.';
            }
        } else if (v) {
            cropHint.className = 'field-hint';
            cropHint.innerHTML = '<i class="bi bi-check-circle"></i> Great — now add a clear photo of the affected leaf.';
        }
        step1.classList.toggle('done', !!v);
        updateDetectBtn();
    });

    // ─── BUTTON STATE ───
    function updateDetectBtn() {
        const hasCrop = !!cropSelect.value;
        const hasFile = !!selectedFile;
        detectBtn.disabled = !(hasCrop && hasFile);

        if (hasCrop && hasFile) {
            btnRequirement.style.display = 'none';
        } else {
            let msg;
            if (!hasCrop && !hasFile) msg = 'Choose a crop and add a leaf photo to continue.';
            else if (!hasCrop)        msg = '↑ Choose your crop above to continue.';
            else                      msg = '↑ Add a leaf photo above to continue.';
            btnRequirement.textContent = msg;
            btnRequirement.style.display = 'block';
        }
    }
    updateDetectBtn();

    // ─── FILE HANDLING ───
    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
    });
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFile(e.target.files[0]);
    });

    ['dragenter', 'dragover'].forEach(evt =>
        uploadZone.addEventListener(evt, (e) => {
            e.preventDefault(); uploadZone.classList.add('dragging');
        }));
    ['dragleave', 'drop'].forEach(evt =>
        uploadZone.addEventListener(evt, (e) => {
            e.preventDefault(); uploadZone.classList.remove('dragging');
        }));
    uploadZone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    function handleFile(file) {
        const ok = ['image/jpeg', 'image/jpg', 'image/png'];
        if (!ok.includes(file.type)) {
            showToast('Please choose a JPG, JPEG or PNG image.', 'error');
            return;
        }
        if (file.size > 16 * 1024 * 1024) {
            showToast('That photo is larger than 16 MB. Please pick a smaller one.', 'error');
            return;
        }
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadZone.style.display = 'none';
            previewArea.style.display = 'block';
            fileName.textContent = file.name;
            fileSize.textContent = formatSize(file.size);
            step2.classList.add('done');
            updateDetectBtn();
        };
        reader.readAsDataURL(file);
    }

    removeImage.addEventListener('click', resetUpload);

    function resetUpload() {
        selectedFile = null;
        fileInput.value = '';
        previewImage.src = '';
        uploadZone.style.display = 'block';
        previewArea.style.display = 'none';
        step2.classList.remove('done');
        updateDetectBtn();
    }

    // ─── DETECT ───
    detectBtn.addEventListener('click', async () => {
        if (!selectedFile || !cropSelect.value) return;

        const isUnknown = cropSelect.value === 'other';
        if (isUnknown && !GEMINI_ON) {
            showToast('Unlisted-crop identification isn’t configured. Please choose a listed crop.', 'error');
            return;
        }

        if (scanLine) scanLine.style.display = 'block';
        loadingTitle.textContent = isUnknown ? 'Identifying your crop…' : 'Reading your leaf…';
        loadingSub.textContent   = isUnknown ? 'Matching the photo against known crops' : 'Looking for signs of disease';
        loadingOverlay.style.display = 'flex';
        detectBtn.disabled = true;

        try {
            const form = new FormData();
            form.append('file', selectedFile);
            form.append('crop_selected', cropSelect.value);

            const res  = await fetch('/api/detect-with-crop', { method: 'POST', body: form });
            const data = await res.json();

            if (data.usage) renderUsage(data.usage);

            if (data.success) {
                lastResult = data;
                renderReport(data);
            } else if (res.status === 429 || data.limit_reached) {
                showLimitModal(data.error);
            } else {
                showToast(data.error || 'We couldn’t read that photo. Please try a clearer one.', 'error');
            }
        } catch (err) {
            console.error('Detection error:', err);
            showToast('Network problem — please check your connection and try again.', 'error');
        } finally {
            if (scanLine) scanLine.style.display = 'none';
            loadingOverlay.style.display = 'none';
            detectBtn.disabled = false;
        }
    });

    // ─── RENDER ───
    function setList(listId, items, sectionId) {
        const el = document.getElementById(listId);
        const arr = Array.isArray(items)
            ? items.filter(x => x != null && String(x).trim() !== '') : [];
        const section = sectionId ? document.getElementById(sectionId) : null;
        if (!arr.length) {
            if (section) section.style.display = 'none';
            el.innerHTML = '';
            return;
        }
        if (section) section.style.display = 'block';
        el.innerHTML = arr.map(x => `<li>${escapeHtml(String(x))}</li>`).join('');
    }

    function toggleRow(rowId, valId, value) {
        const row = document.getElementById(rowId);
        if (value && String(value).trim() !== '') {
            row.style.display = 'flex';
            document.getElementById(valId).textContent = value;
        } else {
            row.style.display = 'none';
        }
    }

    function renderReport(data) {
        const isAi = data.source_short === 'gemini';
        const conf = (data.confidence != null) ? Number(data.confidence) : null;
        const lvl  = data.confidence_level || 'High';
        const tier = data.confidence_tier ||
            (conf == null ? 'high' : conf >= 85 ? 'high' : conf >= 70 ? 'moderate' : 'low');

        reportEmpty.style.display = 'none';
        report.style.display = 'block';

        const badge = document.getElementById('badgeAcc');
        badge.className = 'r-badge ' +
            (lvl === 'High' ? 'acc-high' : lvl === 'Medium' ? 'acc-medium' : 'acc-low');
        badge.querySelector('span').textContent =
            (conf != null) ? `${conf.toFixed(1)}% ${lvl.toLowerCase()} confidence` : 'N/A';

        const banner = document.getElementById('lowConfBanner');
        if (tier === 'moderate' || tier === 'low') {
            document.getElementById('lowConfBannerMsg').textContent =
                data.advisory_message || 'Please verify this result before treating a large area.';
            banner.className = 'lowconf-banner ' + tier;
            banner.style.display = 'flex';
        } else {
            banner.style.display = 'none';
        }

        document.getElementById('aiDisclaimer').style.display =
            (isAi && !data.is_healthy) ? 'flex' : 'none';

        // Which model produced the answer is an internal detail — the report
        // shows the diagnosis and the plan, not the machinery behind it.
        renderTop3(tier === 'high' ? null : data.top3);

        document.getElementById('rCrop').textContent = data.crop || '—';
        document.getElementById('rDisease').textContent = data.disease || '—';

        toggleRow('rCauseRow', 'rCause', data.cause);
        toggleRow('rPartsRow', 'rParts',
            Array.isArray(data.affected_parts) ? data.affected_parts.join(', ') : '');

        document.getElementById('rConf').textContent =
            (conf != null) ? `${conf.toFixed(1)}% · ${lvl}` : 'N/A';
        const fill = document.getElementById('rConfFill');
        fill.className = 'conf-fill' +
            (lvl === 'Medium' ? ' medium' : lvl === 'Low' ? ' low' : '');
        fill.style.width = '0%';
        setTimeout(() => { fill.style.width = `${conf != null ? conf : 0}%`; }, 220);

        const healthy = document.getElementById('healthyHero');
        if (data.is_healthy) {
            healthy.style.display = 'flex';
            document.getElementById('healthyText').textContent = data.description ||
                'No disease found. Keep up the care routine below to protect your crop.';
        } else {
            healthy.style.display = 'none';
        }

        setList('rSymptoms', data.symptoms, 'secSymptoms');
        setList('rOrganic', data.organic_remedy, 'secOrganic');
        if (data.is_healthy) {
            document.getElementById('secChemical').style.display = 'none';
        } else {
            setList('rChemical', data.chemical_spray, 'secChemical');
        }
        setList('rPrevent',
            (data.preventive_measures && data.preventive_measures.length)
                ? data.preventive_measures : data.prevention, 'secPrevent');
        setList('rSafety',
            (data.safety_tips && data.safety_tips.length)
                ? data.safety_tips : data.farmer_tips, 'secSafety');

        const bt = document.getElementById('secBestTime');
        if (data.best_time_to_spray) {
            bt.style.display = 'block';
            document.getElementById('rBestTime').textContent = data.best_time_to_spray;
        } else { bt.style.display = 'none'; }

        const secFert = document.getElementById('secFert');
        const fertBox = document.getElementById('rFert');
        const ferts = Array.isArray(data.fertilizers) ? data.fertilizers : [];
        if (ferts.length) {
            secFert.style.display = 'block';
            const icons = ['🌱', '🧪', '💧', '🍂', '🌿', '⚗️'];
            fertBox.innerHTML = ferts.map((f, i) => `
                <div class="fert-item" style="animation-delay:${i * 0.05}s">
                    <span class="fico">${icons[i % icons.length]}</span>
                    <div><b>${escapeHtml(f.name || '')}</b><span>${escapeHtml(f.purpose || '')}</span></div>
                </div>`).join('');
        } else { secFert.style.display = 'none'; }

        document.getElementById('savedPill').style.display =
            currentUser ? 'inline-flex' : 'none';

        setTimeout(() => report.scrollIntoView({ behavior: 'smooth', block: 'start' }), 140);
    }


    function renderTop3(top3) {
        const sec = document.getElementById('secTop3');
        const box = document.getElementById('rTop3');
        const items = Array.isArray(top3) ? top3.filter(Boolean) : [];
        if (items.length < 2) {
            sec.style.display = 'none';
            box.innerHTML = '';
            return;
        }
        sec.style.display = 'block';
        box.innerHTML = items.map((t, i) => {
            const c = Number(t.confidence) || 0;
            const best = t.is_best || i === 0;
            const cls = c >= 70 ? '' : c >= 40 ? ' medium' : ' low';
            const label = [t.crop, t.disease].filter(Boolean).map(escapeHtml).join(' — ');
            return `
                <div class="top3-item${best ? ' best' : ''}" style="animation-delay:${i * 0.06}s">
                    <div class="top3-rank">${best ? '<i class="bi bi-star-fill"></i>' : (i + 1)}</div>
                    <div class="top3-body">
                        <div class="top3-name">${label}${best ? ' <span class="top3-tag">Best match</span>' : ''}</div>
                        <div class="top3-bar-track"><div class="top3-bar${cls}" style="width:${Math.max(2, c)}%"></div></div>
                    </div>
                    <div class="top3-pct">${c.toFixed(1)}%</div>
                </div>`;
        }).join('');
    }

    // ─── ACTIONS ───
    downloadPdfBtn.addEventListener('click', () => {
        if (!lastResult) return;
        if (window.AgriCareReport) window.AgriCareReport.downloadPDF(lastResult);
        else showToast('Report generator still loading — please try again.', 'error');
    });

    scanAgainBtn.addEventListener('click', () => {
        resetUpload();
        report.style.display = 'none';
        reportEmpty.style.display = 'block';
        lastResult = null;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // ─── LIMIT MODAL ───
    function showLimitModal(message) {
        if (!limitModal) { showToast(message, 'error'); return; }
        limitTitle.textContent = 'Daily limit reached';
        limitBody.textContent = message ||
            'You’ve used all of today’s scans. Sign in with Google for a higher daily limit.';
        limitModal.classList.add('show');
    }
    if (limitClose) limitClose.addEventListener('click', () => limitModal.classList.remove('show'));
    if (limitModal) limitModal.addEventListener('click', (e) => {
        if (e.target === limitModal) limitModal.classList.remove('show');
    });

    // ─── TOASTS ───
    function showToast(message, type = 'error') {
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        const icon = type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-circle-fill';
        t.innerHTML = `<i class="bi ${icon}"></i><span>${escapeHtml(message)}</span>`;
        toastHost.appendChild(t);
        setTimeout(() => {
            t.classList.add('leaving');
            setTimeout(() => t.remove(), 320);
        }, 4600);
    }

    // ─── UTIL ───
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, s => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[s]));
    }
});
