/**
 * AgriCare — Shared treatment-report PDF generator
 * Used by both the Detect page (fresh result) and the History page (stored result).
 * Relies on jsPDF (loaded via CDN as window.jspdf).
 */
(function () {
    'use strict';

    function normalizeList(v) {
        if (Array.isArray(v)) return v.filter(x => x != null && String(x).trim() !== '');
        if (v && String(v).trim() !== '') return [String(v)];
        return [];
    }

    // Pull a unified report object out of either a fresh /predict response or a
    // stored history record (which nests everything under `result`).
    function unify(data) {
        const r = (data && data.result) ? { ...data.result, ...data } : (data || {});
        return {
            source: r.source || 'AgriCare AI',
            crop: r.crop || 'Unknown',
            crop_hindi: r.crop_hindi || '',
            disease: r.disease || 'Unknown',
            confidence: (r.confidence != null) ? r.confidence : null,
            confidence_level: r.confidence_level || '',
            is_healthy: !!r.is_healthy,
            cause: r.cause || '',
            affected_parts: normalizeList(r.affected_parts),
            symptoms: normalizeList(r.symptoms),
            organic_remedy: normalizeList(r.organic_remedy),
            chemical_spray: normalizeList(r.chemical_spray),
            preventive_measures: normalizeList((r.preventive_measures && r.preventive_measures.length) ? r.preventive_measures : r.prevention),
            best_time_to_spray: r.best_time_to_spray || '',
            fertilizers: Array.isArray(r.fertilizers) ? r.fertilizers : [],
            safety_tips: normalizeList((r.safety_tips && r.safety_tips.length) ? r.safety_tips : r.farmer_tips),
            disclaimer: r.disclaimer || '',
            created_at: r.created_at || null
        };
    }

    function accuracyText(rep) {
        if (rep.confidence == null) return 'Confidence: N/A';
        const lvl = rep.confidence_level || (rep.confidence >= 90 ? 'High' : rep.confidence >= 70 ? 'Medium' : 'Low');
        return `Accuracy: ${rep.confidence.toFixed ? rep.confidence.toFixed(2) : rep.confidence}%  (${lvl})`;
    }

    function downloadPDF(data) {
        const rep = unify(data);
        if (!window.jspdf || !window.jspdf.jsPDF) {
            alert('PDF library not loaded. Please check your internet connection and try again.');
            return;
        }
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ unit: 'pt', format: 'a4' });

        const M = 48;                       // margin
        const W = doc.internal.pageSize.getWidth();
        const H = doc.internal.pageSize.getHeight();
        const CW = W - M * 2;               // content width
        let y = M;

        const green = [46, 125, 50];
        const dark = [33, 37, 41];
        const grey = [110, 116, 122];

        function ensure(space) {
            if (y + space > H - M) { doc.addPage(); y = M; }
        }
        function rule() {
            ensure(14);
            doc.setDrawColor(200); doc.setLineWidth(0.6);
            doc.line(M, y, W - M, y); y += 14;
        }
        function heading(txt) {
            ensure(26);
            doc.setFont('helvetica', 'bold'); doc.setFontSize(12);
            doc.setTextColor(green[0], green[1], green[2]);
            doc.text(txt, M, y); y += 16;
            doc.setTextColor(dark[0], dark[1], dark[2]);
        }
        function bullets(items) {
            doc.setFont('helvetica', 'normal'); doc.setFontSize(10.5);
            doc.setTextColor(dark[0], dark[1], dark[2]);
            items.forEach(function (it) {
                const lines = doc.splitTextToSize('•  ' + String(it), CW - 6);
                ensure(lines.length * 13 + 2);
                doc.text(lines, M + 4, y);
                y += lines.length * 13 + 2;
            });
            y += 6;
        }
        function kv(label, value) {
            doc.setFontSize(10.5);
            ensure(15);
            doc.setFont('helvetica', 'bold'); doc.setTextColor(grey[0], grey[1], grey[2]);
            doc.text(label, M, y);
            doc.setFont('helvetica', 'normal'); doc.setTextColor(dark[0], dark[1], dark[2]);
            const lines = doc.splitTextToSize(String(value || '—'), CW - 130);
            doc.text(lines, M + 130, y);
            y += Math.max(15, lines.length * 13);
        }

        // ── Header banner ──
        doc.setFillColor(green[0], green[1], green[2]);
        doc.rect(0, 0, W, 74, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFont('helvetica', 'bold'); doc.setFontSize(17);
        doc.text('AgriCare  —  Crop Health & Diagnosis Report', M, 34);
        doc.setFont('helvetica', 'normal'); doc.setFontSize(10);
        doc.text(accuracyText(rep), M, 54);
        y = 96;

        // ── Identity ──
        kv('Identified Crop', rep.crop);
        kv('Detected Disease', rep.disease);
        if (rep.cause) kv('Cause of Disease', rep.cause);
        if (rep.affected_parts.length) kv('Affected Parts', rep.affected_parts.join(', '));
        y += 4; rule();

        if (rep.symptoms.length) { heading('Visible Symptoms'); bullets(rep.symptoms); }
        if (rep.organic_remedy.length) { heading('Organic Remedy'); bullets(rep.organic_remedy); }
        if (rep.chemical_spray.length) { heading('Chemical Spray'); bullets(rep.chemical_spray); }
        if (rep.preventive_measures.length) { heading('Preventive Measures'); bullets(rep.preventive_measures); }

        if (rep.best_time_to_spray) {
            heading('Best Time to Spray');
            doc.setFont('helvetica', 'normal'); doc.setFontSize(10.5);
            const lines = doc.splitTextToSize(rep.best_time_to_spray, CW - 6);
            ensure(lines.length * 13 + 4);
            doc.text(lines, M + 4, y); y += lines.length * 13 + 8;
        }

        if (rep.fertilizers.length) {
            heading('Recommended Fertilizers');
            bullets(rep.fertilizers.map(function (f) {
                return f.purpose ? (f.name + ' — ' + f.purpose) : f.name;
            }));
        }

        if (rep.safety_tips.length) { heading('Safety Precautions & Farmer Tips'); bullets(rep.safety_tips); }

        // A printed plan travels away from the app, so the label caveat has to
        // travel with it whenever chemicals were recommended.
        if (rep.chemical_spray && rep.chemical_spray.length && !rep.is_healthy) {
            ensure(46);
            doc.setFont('helvetica', 'italic'); doc.setFontSize(9);
            doc.setTextColor(140, 110, 0);
            const cl = doc.splitTextToSize(
                'Important: doses above are general guidance for Indian conditions. '
                + 'Approved products and rates change and differ by state - always follow '
                + 'the label on the pack, observe the pre-harvest interval, and check with '
                + 'your Krishi Vigyan Kendra or agriculture officer before treating a large area.',
                CW);
            doc.text(cl, M, y); y += cl.length * 12 + 6;
            doc.setTextColor(0, 0, 0);
        }

        if (rep.disclaimer) {
            ensure(30);
            doc.setFont('helvetica', 'italic'); doc.setFontSize(9);
            doc.setTextColor(140, 110, 0);
            const dl = doc.splitTextToSize('Note: ' + rep.disclaimer, CW);
            doc.text(dl, M, y); y += dl.length * 12 + 6;
        }

        // ── Footer on every page ──
        const stamp = 'Generated ' + new Date().toLocaleString();
        const pages = doc.internal.getNumberOfPages();
        for (let p = 1; p <= pages; p++) {
            doc.setPage(p);
            doc.setFont('helvetica', 'normal'); doc.setFontSize(8.5);
            doc.setTextColor(grey[0], grey[1], grey[2]);
            doc.text(stamp, M, H - 22);
            doc.text('Powered by AgriCare AI', W - M, H - 22, { align: 'right' });
        }

        const dateStr = new Date().toISOString().slice(0, 10);
        const safeCrop = (rep.crop || 'Crop').replace(/[^a-z0-9]+/gi, '_');
        doc.save('AgriCare_' + safeCrop + '_' + dateStr + '.pdf');
    }

    window.AgriCareReport = { downloadPDF: downloadPDF, unify: unify };
})();
