#!/usr/bin/env node
/**
 * CRM Metryki - Lokalny Serwer
 *
 * URUCHOMIENIE:
 *   node crm-server.js
 *
 * Potem otwórz: http://localhost:3456
 *
 * Automatycznie zapisuje do: ../dane/metryki.md
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3456;
const METRYKI_PATH = path.join(__dirname, '..', 'dane', 'metryki.md');

// Kolory do konsoli
const log = {
    info: (msg) => console.log(`\x1b[36m[INFO]\x1b[0m ${msg}`),
    success: (msg) => console.log(`\x1b[32m[OK]\x1b[0m ${msg}`),
    error: (msg) => console.log(`\x1b[31m[ERROR]\x1b[0m ${msg}`),
    save: (msg) => console.log(`\x1b[33m[SAVE]\x1b[0m ${msg}`)
};

// HTML aplikacji (wbudowany)
const HTML = `<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRM Metryki - Beauty AI FIRST</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --bg-input: #334155;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #475569;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }

        .container { max-width: 1400px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }

        h1 { font-size: 1.8rem; display: flex; align-items: center; gap: 10px; }

        .header-actions { display: flex; gap: 10px; align-items: center; }

        .save-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 15px;
            background: rgba(16, 185, 129, 0.2);
            border-radius: 8px;
            font-size: 0.85rem;
            color: var(--success);
        }

        .save-status.saving { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
        .save-status.error { background: rgba(239, 68, 68, 0.2); color: var(--danger); }

        .pulse {
            width: 8px; height: 8px; border-radius: 50%;
            background: currentColor; animation: pulse 2s infinite;
        }

        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

        .btn {
            padding: 10px 20px; border: none; border-radius: 8px;
            font-size: 0.9rem; font-weight: 600; cursor: pointer;
            transition: all 0.2s; display: flex; align-items: center; gap: 8px;
        }

        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-success { background: var(--success); color: white; }
        .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .btn-outline:hover { background: var(--bg-input); }

        .dashboard {
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 20px; margin-bottom: 30px;
        }

        .stat-card {
            background: var(--bg-card); padding: 20px;
            border-radius: 12px; border: 1px solid var(--border);
        }

        .stat-label { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px; }
        .stat-value { font-size: 2rem; font-weight: 700; }
        .stat-target { font-size: 0.8rem; color: var(--text-muted); margin-top: 5px; }
        .stat-value.success { color: var(--success); }
        .stat-value.warning { color: var(--warning); }
        .stat-value.danger { color: var(--danger); }

        .quick-add {
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 15px; margin-bottom: 30px;
        }

        .quick-add-item {
            background: var(--bg-card); padding: 20px;
            border-radius: 12px; border: 1px solid var(--border); text-align: center;
        }

        .quick-add-item label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 10px; }

        .counter { display: flex; align-items: center; justify-content: center; gap: 15px; }

        .counter button {
            width: 40px; height: 40px; border-radius: 50%;
            border: 1px solid var(--border); background: var(--bg-input);
            color: var(--text); font-size: 1.2rem; cursor: pointer; transition: all 0.2s;
        }

        .counter button:hover { background: var(--primary); border-color: var(--primary); }
        .counter span { font-size: 1.5rem; font-weight: 700; min-width: 40px; }

        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }

        .card {
            background: var(--bg-card); border-radius: 12px;
            border: 1px solid var(--border); padding: 20px;
        }

        .card-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border);
        }

        .card-title { font-size: 1.1rem; font-weight: 600; }

        .pipeline-section { margin-bottom: 20px; }

        .pipeline-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
        }

        .pipeline-title { font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .pipeline-title.hot::before { content: "🔥"; }
        .pipeline-title.warm::before { content: "☀️"; }
        .pipeline-title.cold::before { content: "❄️"; }
        .pipeline-total { font-size: 0.85rem; color: var(--success); font-weight: 600; }

        .lead-item {
            background: var(--bg-input); padding: 12px 15px; border-radius: 8px;
            margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;
        }

        .lead-info { flex: 1; }
        .lead-name { font-weight: 600; margin-bottom: 3px; }
        .lead-details { font-size: 0.8rem; color: var(--text-muted); }
        .lead-value { font-weight: 600; color: var(--success); margin-right: 15px; }
        .lead-actions { display: flex; gap: 5px; }

        .lead-actions button {
            width: 30px; height: 30px; border-radius: 6px; border: none;
            background: var(--bg-card); color: var(--text-muted); cursor: pointer; font-size: 0.8rem;
        }

        .lead-actions button:hover { background: var(--primary); color: white; }

        .empty-state { text-align: center; padding: 20px; color: var(--text-muted); font-size: 0.9rem; }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; }

        .form-group input, .form-group select, .form-group textarea {
            width: 100%; padding: 10px 12px; border-radius: 8px;
            border: 1px solid var(--border); background: var(--bg-input);
            color: var(--text); font-size: 0.95rem;
        }

        .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--primary); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }

        .history-table { width: 100%; border-collapse: collapse; }
        .history-table th, .history-table td { padding: 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
        .history-table th { color: var(--text-muted); font-weight: 500; }

        .modal-overlay {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center;
        }

        .modal-overlay.active { display: flex; }

        .modal {
            background: var(--bg-card); border-radius: 16px; padding: 30px;
            max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto;
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-title { font-size: 1.2rem; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer; }

        .toast {
            position: fixed; bottom: 20px; right: 20px;
            background: var(--success); color: white; padding: 15px 25px;
            border-radius: 8px; font-weight: 500; transform: translateY(100px);
            opacity: 0; transition: all 0.3s; z-index: 200;
        }

        .toast.show { transform: translateY(0); opacity: 1; }

        @media (max-width: 1200px) {
            .dashboard { grid-template-columns: repeat(2, 1fr); }
            .main-grid { grid-template-columns: 1fr; }
            .quick-add { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 600px) {
            .dashboard { grid-template-columns: 1fr; }
            .quick-add { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 CRM Metryki - Beauty</h1>
            <div class="header-actions">
                <div class="save-status" id="save-status">
                    <span class="pulse"></span>
                    <span id="save-text">Auto-zapis aktywny</span>
                </div>
                <button class="btn btn-outline" onclick="resetWeek()">🔄 Nowy Tydzień</button>
            </div>
        </header>

        <div class="dashboard">
            <div class="stat-card">
                <div class="stat-label">DM wysłane (tydzień)</div>
                <div class="stat-value" id="stat-dm">0</div>
                <div class="stat-target">Cel: 20</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Odpowiedzi</div>
                <div class="stat-value" id="stat-responses">0</div>
                <div class="stat-target">Cel: 5 (25%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Konsultacje</div>
                <div class="stat-value" id="stat-consultations">0</div>
                <div class="stat-target">Cel: 2</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sprzedaże</div>
                <div class="stat-value" id="stat-sales">0</div>
                <div class="stat-target">Cel: 1 = 5,500 PLN</div>
            </div>
        </div>

        <div class="quick-add">
            <div class="quick-add-item">
                <label>DM wysłane dziś</label>
                <div class="counter">
                    <button onclick="updateDaily('dm', -1)">−</button>
                    <span id="today-dm">0</span>
                    <button onclick="updateDaily('dm', 1)">+</button>
                </div>
            </div>
            <div class="quick-add-item">
                <label>Odpowiedzi dziś</label>
                <div class="counter">
                    <button onclick="updateDaily('responses', -1)">−</button>
                    <span id="today-responses">0</span>
                    <button onclick="updateDaily('responses', 1)">+</button>
                </div>
            </div>
            <div class="quick-add-item">
                <label>Konsultacje dziś</label>
                <div class="counter">
                    <button onclick="updateDaily('consultations', -1)">−</button>
                    <span id="today-consultations">0</span>
                    <button onclick="updateDaily('consultations', 1)">+</button>
                </div>
            </div>
            <div class="quick-add-item">
                <label>Sprzedaże dziś</label>
                <div class="counter">
                    <button onclick="updateDaily('sales', -1)">−</button>
                    <span id="today-sales">0</span>
                    <button onclick="updateDaily('sales', 1)">+</button>
                </div>
            </div>
        </div>

        <div class="main-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🎯 Pipeline</span>
                    <button class="btn btn-primary" onclick="showLeadModal()">+ Dodaj Lead</button>
                </div>

                <div class="pipeline-section">
                    <div class="pipeline-header">
                        <span class="pipeline-title hot">Gorące (decyzja &lt;7 dni)</span>
                        <span class="pipeline-total" id="total-hot">0 PLN</span>
                    </div>
                    <div id="pipeline-hot"></div>
                </div>

                <div class="pipeline-section">
                    <div class="pipeline-header">
                        <span class="pipeline-title warm">Ciepłe (po rozmowie)</span>
                        <span class="pipeline-total" id="total-warm">0 PLN</span>
                    </div>
                    <div id="pipeline-warm"></div>
                </div>

                <div class="pipeline-section">
                    <div class="pipeline-header">
                        <span class="pipeline-title cold">Zimne (czekam na odpowiedź)</span>
                        <span class="pipeline-total" id="total-cold">0 PLN</span>
                    </div>
                    <div id="pipeline-cold"></div>
                </div>
            </div>

            <div>
                <div class="card" style="margin-bottom: 20px;">
                    <div class="card-header">
                        <span class="card-title">💰 Historia Sprzedaży</span>
                        <span id="total-revenue" style="color: var(--success); font-weight: 600;">0 PLN</span>
                    </div>
                    <div id="sales-history">
                        <div class="empty-state">Brak sprzedaży. Zamknij pierwszego klienta!</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">📝 Wnioski i Lekcje</span>
                    </div>
                    <div class="form-group">
                        <label>Co działa:</label>
                        <textarea id="notes-working" rows="2" placeholder="np. Baza Primroses daje najlepsze leady..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Co nie działa:</label>
                        <textarea id="notes-not-working" rows="2" placeholder="np. Cold DM do nieznanych osób..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Do poprawy:</label>
                        <textarea id="notes-improve" rows="2" placeholder="np. Szybciej follow-upować..."></textarea>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Lead Modal -->
    <div class="modal-overlay" id="lead-modal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">Dodaj Lead</span>
                <button class="modal-close" onclick="closeLeadModal()">&times;</button>
            </div>
            <form onsubmit="addLead(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>Imię</label>
                        <input type="text" id="lead-name" required placeholder="np. Kasia">
                    </div>
                    <div class="form-group">
                        <label>Gabinet/Miasto</label>
                        <input type="text" id="lead-business" required placeholder="np. Beauty Studio Kraków">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Status</label>
                        <select id="lead-status">
                            <option value="cold">❄️ Zimny</option>
                            <option value="warm">☀️ Ciepły</option>
                            <option value="hot">🔥 Gorący</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Potencjał (PLN)</label>
                        <input type="number" id="lead-value" value="5500">
                    </div>
                </div>
                <div class="form-group">
                    <label>Następny krok</label>
                    <input type="text" id="lead-next" placeholder="np. Telefon, Wysłać ofertę">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Deadline</label>
                        <input type="date" id="lead-deadline">
                    </div>
                    <div class="form-group">
                        <label>Źródło</label>
                        <select id="lead-source">
                            <option value="Baza Primroses">Baza Primroses</option>
                            <option value="Instagram">Instagram</option>
                            <option value="Polecenie">Polecenie</option>
                            <option value="Inne">Inne</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Notatki</label>
                    <input type="text" id="lead-notes" placeholder="np. Była klientka, zainteresowana">
                </div>
                <button type="submit" class="btn btn-success" style="width: 100%; margin-top: 10px;">Dodaj Lead</button>
            </form>
        </div>
    </div>

    <!-- Sale Modal -->
    <div class="modal-overlay" id="sale-modal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🎉 Zamknij Sprzedaż</span>
                <button class="modal-close" onclick="closeSaleModal()">&times;</button>
            </div>
            <form onsubmit="convertToSale(event)">
                <input type="hidden" id="sale-lead-id">
                <div class="form-row">
                    <div class="form-group">
                        <label>Klient</label>
                        <input type="text" id="sale-client" readonly>
                    </div>
                    <div class="form-group">
                        <label>Kwota (PLN)</label>
                        <input type="number" id="sale-amount" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Produkt</label>
                    <input type="text" id="sale-product" value="Gabinet na Autopilocie">
                </div>
                <div class="form-group">
                    <label>Notatki</label>
                    <input type="text" id="sale-notes" placeholder="np. Start od 01.03">
                </div>
                <button type="submit" class="btn btn-success" style="width: 100%; margin-top: 10px;">💰 Zapisz Sprzedaż</button>
            </form>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let data = {
            currentWeek: getCurrentWeek(),
            daily: { dm: 0, responses: 0, consultations: 0, sales: 0 },
            weeklyTotals: {},
            leads: [],
            salesHistory: [],
            notes: { working: '', notWorking: '', improve: '' }
        };

        let saveTimeout = null;

        function getCurrentWeek() {
            const now = new Date();
            const start = new Date(now.getFullYear(), 0, 1);
            const week = Math.ceil((((now - start) / 86400000) + start.getDay() + 1) / 7);
            return 'Tydzień ' + week + ' (' + now.toLocaleDateString('pl-PL') + ')';
        }

        // Save to server (auto-save)
        async function saveToServer() {
            const statusEl = document.getElementById('save-status');
            const textEl = document.getElementById('save-text');

            statusEl.className = 'save-status saving';
            textEl.textContent = 'Zapisuję...';

            try {
                const markdown = generateMarkdown();
                const response = await fetch('/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/plain' },
                    body: markdown
                });

                if (response.ok) {
                    statusEl.className = 'save-status';
                    textEl.textContent = 'Zapisano ' + new Date().toLocaleTimeString('pl-PL');
                } else {
                    throw new Error('Save failed');
                }
            } catch (err) {
                statusEl.className = 'save-status error';
                textEl.textContent = 'Błąd zapisu!';
                console.error('Save error:', err);
            }
        }

        function triggerSave() {
            if (saveTimeout) clearTimeout(saveTimeout);
            saveTimeout = setTimeout(saveToServer, 500);
        }

        function saveData() {
            localStorage.setItem('crm-beauty-data', JSON.stringify(data));
            triggerSave();
        }

        function loadData() {
            const saved = localStorage.getItem('crm-beauty-data');
            if (saved) {
                data = JSON.parse(saved);
                const today = new Date().toDateString();
                if (data.lastDay !== today) {
                    if (data.lastDay && data.weeklyTotals) {
                        if (!data.weeklyTotals[data.currentWeek]) {
                            data.weeklyTotals[data.currentWeek] = { dm: 0, responses: 0, consultations: 0, sales: 0 };
                        }
                        data.weeklyTotals[data.currentWeek].dm += data.daily.dm;
                        data.weeklyTotals[data.currentWeek].responses += data.daily.responses;
                        data.weeklyTotals[data.currentWeek].consultations += data.daily.consultations;
                        data.weeklyTotals[data.currentWeek].sales += data.daily.sales;
                    }
                    data.daily = { dm: 0, responses: 0, consultations: 0, sales: 0 };
                    data.lastDay = today;
                }
            } else {
                // First time - add Kasia
                data.leads.push({
                    id: '1', name: 'Kasia', business: 'Oświęcim (2 gabinety)',
                    status: 'warm', value: 5500, next: 'Telefon',
                    deadline: '2026-02-13', source: 'Baza Primroses',
                    notes: 'Była klientka Primroses', createdAt: new Date().toISOString()
                });
            }
            data.lastDay = new Date().toDateString();
            updateUI();
        }

        function updateDaily(type, delta) {
            data.daily[type] = Math.max(0, data.daily[type] + delta);
            saveData();
            updateUI();
            showToast((delta > 0 ? '+1 ' : '-1 ') + type);
        }

        function getWeeklyTotals() {
            const weekData = data.weeklyTotals[data.currentWeek] || { dm: 0, responses: 0, consultations: 0, sales: 0 };
            return {
                dm: weekData.dm + data.daily.dm,
                responses: weekData.responses + data.daily.responses,
                consultations: weekData.consultations + data.daily.consultations,
                sales: weekData.sales + data.daily.sales
            };
        }

        function updateUI() {
            document.getElementById('today-dm').textContent = data.daily.dm;
            document.getElementById('today-responses').textContent = data.daily.responses;
            document.getElementById('today-consultations').textContent = data.daily.consultations;
            document.getElementById('today-sales').textContent = data.daily.sales;

            const weekly = getWeeklyTotals();
            updateStat('stat-dm', weekly.dm, 20);
            updateStat('stat-responses', weekly.responses, 5);
            updateStat('stat-consultations', weekly.consultations, 2);
            updateStat('stat-sales', weekly.sales, 1);

            renderPipeline();
            renderSalesHistory();

            document.getElementById('notes-working').value = data.notes.working || '';
            document.getElementById('notes-not-working').value = data.notes.notWorking || '';
            document.getElementById('notes-improve').value = data.notes.improve || '';
        }

        function updateStat(id, value, target) {
            const el = document.getElementById(id);
            el.textContent = value;
            el.className = 'stat-value ' + (value >= target ? 'success' : value >= target * 0.5 ? 'warning' : 'danger');
        }

        function renderPipeline() {
            const hot = data.leads.filter(l => l.status === 'hot');
            const warm = data.leads.filter(l => l.status === 'warm');
            const cold = data.leads.filter(l => l.status === 'cold');

            document.getElementById('pipeline-hot').innerHTML = hot.length ? hot.map(renderLead).join('') : '<div class="empty-state">Brak</div>';
            document.getElementById('pipeline-warm').innerHTML = warm.length ? warm.map(renderLead).join('') : '<div class="empty-state">Brak</div>';
            document.getElementById('pipeline-cold').innerHTML = cold.length ? cold.map(renderLead).join('') : '<div class="empty-state">Brak</div>';

            document.getElementById('total-hot').textContent = formatMoney(hot.reduce((s, l) => s + l.value, 0));
            document.getElementById('total-warm').textContent = formatMoney(warm.reduce((s, l) => s + l.value, 0));
            document.getElementById('total-cold').textContent = formatMoney(cold.reduce((s, l) => s + l.value, 0));
        }

        function renderLead(lead) {
            const deadline = lead.deadline ? new Date(lead.deadline).toLocaleDateString('pl-PL') : '';
            return '<div class="lead-item">' +
                '<div class="lead-info"><div class="lead-name">' + lead.name + '</div>' +
                '<div class="lead-details">' + lead.business + (deadline ? ' • ' + deadline : '') + (lead.next ? ' • ' + lead.next : '') + '</div></div>' +
                '<span class="lead-value">' + formatMoney(lead.value) + '</span>' +
                '<div class="lead-actions">' +
                (lead.status !== 'hot' ? '<button onclick="moveLead(\\'' + lead.id + '\\', \\'up\\')" title="W górę">⬆️</button>' : '') +
                (lead.status !== 'cold' ? '<button onclick="moveLead(\\'' + lead.id + '\\', \\'down\\')" title="W dół">⬇️</button>' : '') +
                '<button onclick="showSaleModal(\\'' + lead.id + '\\')" title="Sprzedaż">💰</button>' +
                '<button onclick="deleteLead(\\'' + lead.id + '\\')" title="Usuń">🗑️</button>' +
                '</div></div>';
        }

        function formatMoney(amount) { return amount.toLocaleString('pl-PL') + ' PLN'; }

        function showLeadModal() {
            document.getElementById('lead-modal').classList.add('active');
            document.getElementById('lead-deadline').value = new Date(Date.now() + 7*24*60*60*1000).toISOString().split('T')[0];
        }

        function closeLeadModal() { document.getElementById('lead-modal').classList.remove('active'); }

        function addLead(e) {
            e.preventDefault();
            data.leads.push({
                id: Date.now().toString(),
                name: document.getElementById('lead-name').value,
                business: document.getElementById('lead-business').value,
                status: document.getElementById('lead-status').value,
                value: parseInt(document.getElementById('lead-value').value) || 5500,
                next: document.getElementById('lead-next').value,
                deadline: document.getElementById('lead-deadline').value,
                source: document.getElementById('lead-source').value,
                notes: document.getElementById('lead-notes').value,
                createdAt: new Date().toISOString()
            });
            saveData();
            updateUI();
            closeLeadModal();
            showToast('Lead dodany!');
            e.target.reset();
        }

        function moveLead(id, direction) {
            const lead = data.leads.find(l => l.id === id);
            if (!lead) return;
            const statuses = ['cold', 'warm', 'hot'];
            const idx = statuses.indexOf(lead.status);
            const newIdx = direction === 'up' ? idx + 1 : idx - 1;
            if (newIdx >= 0 && newIdx < statuses.length) {
                lead.status = statuses[newIdx];
                saveData();
                updateUI();
            }
        }

        function deleteLead(id) {
            if (confirm('Usunąć leada?')) {
                data.leads = data.leads.filter(l => l.id !== id);
                saveData();
                updateUI();
            }
        }

        function showSaleModal(leadId) {
            const lead = data.leads.find(l => l.id === leadId);
            if (!lead) return;
            document.getElementById('sale-lead-id').value = leadId;
            document.getElementById('sale-client').value = lead.name + ', ' + lead.business;
            document.getElementById('sale-amount').value = lead.value;
            document.getElementById('sale-modal').classList.add('active');
        }

        function closeSaleModal() { document.getElementById('sale-modal').classList.remove('active'); }

        function convertToSale(e) {
            e.preventDefault();
            const leadId = document.getElementById('sale-lead-id').value;
            const lead = data.leads.find(l => l.id === leadId);

            data.salesHistory.push({
                id: Date.now().toString(),
                date: new Date().toISOString(),
                client: document.getElementById('sale-client').value,
                product: document.getElementById('sale-product').value,
                amount: parseInt(document.getElementById('sale-amount').value),
                source: lead ? lead.source : 'Inne',
                notes: document.getElementById('sale-notes').value
            });

            data.leads = data.leads.filter(l => l.id !== leadId);
            data.daily.sales++;
            saveData();
            updateUI();
            closeSaleModal();
            showToast('🎉 Sprzedaż zapisana!');
        }

        function renderSalesHistory() {
            const container = document.getElementById('sales-history');
            const total = data.salesHistory.reduce((s, sale) => s + sale.amount, 0);
            document.getElementById('total-revenue').textContent = formatMoney(total);

            if (!data.salesHistory.length) {
                container.innerHTML = '<div class="empty-state">Brak sprzedaży</div>';
                return;
            }

            container.innerHTML = '<table class="history-table"><thead><tr><th>#</th><th>Data</th><th>Klient</th><th>Kwota</th></tr></thead><tbody>' +
                data.salesHistory.map((s, i) => '<tr><td>' + (i+1) + '</td><td>' + new Date(s.date).toLocaleDateString('pl-PL') + '</td><td>' + s.client + '</td><td style="color:var(--success);font-weight:600">' + formatMoney(s.amount) + '</td></tr>').join('') +
                '</tbody></table>';
        }

        function resetWeek() {
            if (confirm('Rozpocząć nowy tydzień?')) {
                const weekly = getWeeklyTotals();
                data.weeklyTotals[data.currentWeek] = weekly;
                data.currentWeek = getCurrentWeek();
                data.daily = { dm: 0, responses: 0, consultations: 0, sales: 0 };
                saveData();
                updateUI();
                showToast('Nowy tydzień!');
            }
        }

        // Notes auto-save
        ['notes-working', 'notes-not-working', 'notes-improve'].forEach(id => {
            document.getElementById(id).addEventListener('input', function() {
                data.notes.working = document.getElementById('notes-working').value;
                data.notes.notWorking = document.getElementById('notes-not-working').value;
                data.notes.improve = document.getElementById('notes-improve').value;
                saveData();
            });
        });

        function generateMarkdown() {
            const today = new Date().toLocaleDateString('pl-PL');
            const weekly = getWeeklyTotals();
            const hot = data.leads.filter(l => l.status === 'hot');
            const warm = data.leads.filter(l => l.status === 'warm');
            const cold = data.leads.filter(l => l.status === 'cold');

            return \`# METRYKI SPRZEDAŻY - BEAUTY (AI FIRST)

**Ostatnia aktualizacja:** \${today}
**Model:** Lejek Hunter (0 PLN budżetu)
**Cena wdrożenia:** 5,500 PLN

---

## LEJEK HUNTER - FLOW

\\\`\\\`\\\`
BAZA PRIMROSES → OUTREACH → ODPOWIEDŹ → KONSULTACJA → SPRZEDAŻ → CASE STUDY → REFERRAL
     ↓              ↓           ↓            ↓            ↓
   100%           20/tydz      25%          40%          50%
                              (5/20)       (2/5)        (1/2)
\\\`\\\`\\\`

**Cel tygodniowy:** 20 DM → 5 odpowiedzi → 2 konsultacje → 1 sprzedaż = 5,500 PLN

---

## AKTYWNOŚĆ TYGODNIOWA

### \${data.currentWeek}
| Metryka | Wartość | Cel | Status |
|---------|---------|-----|--------|
| DM wysłane | \${weekly.dm} | 20 | \${weekly.dm >= 20 ? '✅' : weekly.dm >= 10 ? '⚠️' : '❌'} |
| Odpowiedzi | \${weekly.responses} | 5 | \${weekly.responses >= 5 ? '✅' : weekly.responses >= 2 ? '⚠️' : '❌'} |
| Konsultacje | \${weekly.consultations} | 2 | \${weekly.consultations >= 2 ? '✅' : weekly.consultations >= 1 ? '⚠️' : '❌'} |
| Sprzedaże | \${weekly.sales} | 1 | \${weekly.sales >= 1 ? '✅' : '❌'} |

---

## PIPELINE

### Gorące (gotowe kupić - decyzja w 7 dni)
\${hot.length ? \`| Kto | Gabinet | Potencjał | Następny krok | Deadline | Notatki |
|-----|---------|-----------|---------------|----------|---------|
\${hot.map(l => \`| \${l.name} | \${l.business} | \${formatMoney(l.value)} | \${l.next || '-'} | \${l.deadline ? new Date(l.deadline).toLocaleDateString('pl-PL') : '-'} | \${l.notes || '-'} |\`).join('\\n')}\` : '| - | - | - | - | - | - |'}

**TOTAL GORĄCE:** \${formatMoney(hot.reduce((s, l) => s + l.value, 0))}

### Ciepłe (po rozmowie/zainteresowani)
\${warm.length ? \`| Kto | Gabinet | Potencjał | Następny krok | Deadline | Notatki |
|-----|---------|-----------|---------------|----------|---------|
\${warm.map(l => \`| \${l.name} | \${l.business} | \${formatMoney(l.value)} | \${l.next || '-'} | \${l.deadline ? new Date(l.deadline).toLocaleDateString('pl-PL') : '-'} | \${l.notes || '-'} |\`).join('\\n')}\` : '| - | - | - | - | - | - |'}

**TOTAL CIEPŁE:** \${formatMoney(warm.reduce((s, l) => s + l.value, 0))}

### Zimne (napisałeś, czekasz na odpowiedź)
\${cold.length ? \`| Kto | Gabinet | Potencjał | Data kontaktu | Follow-up |
|-----|---------|-----------|---------------|-----------|
\${cold.map(l => \`| \${l.name} | \${l.business} | \${formatMoney(l.value)} | \${l.createdAt ? new Date(l.createdAt).toLocaleDateString('pl-PL') : '-'} | \${l.deadline ? new Date(l.deadline).toLocaleDateString('pl-PL') : '-'} |\`).join('\\n')}\` : '| - | - | - | - | - |'}

**TOTAL ZIMNE:** \${formatMoney(cold.reduce((s, l) => s + l.value, 0))}

---

## HISTORIA SPRZEDAŻY

\${data.salesHistory.length ? \`| # | Data | Klient | Produkt | Kwota | Źródło | Notatki |
|---|------|--------|---------|-------|--------|---------|
\${data.salesHistory.map((s, i) => \`| \${i + 1} | \${new Date(s.date).toLocaleDateString('pl-PL')} | \${s.client} | \${s.product} | \${formatMoney(s.amount)} | \${s.source} | \${s.notes || '-'} |\`).join('\\n')}\` : '| - | - | - | - | - | - | Brak sprzedaży |'}

**TOTAL 2026:** \${formatMoney(data.salesHistory.reduce((s, sale) => s + sale.amount, 0))}

---

## WNIOSKI I LEKCJE

### Co działa:
\${data.notes.working || '- (uzupełnij po pierwszych sprzedażach)'}

### Co nie działa:
\${data.notes.notWorking || '- (uzupełnij po pierwszych próbach)'}

### Do poprawy:
\${data.notes.improve || '- Pipeline za wąski\\n- Zero outreachu'}

---

*CSO czyta ten plik przy każdym wywołaniu. Im lepsze dane, tym lepsze rekomendacje.*
\`;
        }

        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }

        loadData();
    </script>
</body>
</html>`;

// Serwer HTTP
const server = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // Strona główna
    if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(HTML);
        return;
    }

    // Zapis do pliku
    if (req.method === 'POST' && req.url === '/save') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', () => {
            try {
                fs.writeFileSync(METRYKI_PATH, body, 'utf8');
                log.save(`Zapisano metryki.md (${body.length} bajtów)`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (err) {
                log.error(`Błąd zapisu: ${err.message}`);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    // 404
    res.writeHead(404);
    res.end('Not found');
});

server.listen(PORT, () => {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║           CRM METRYKI - BEAUTY AI FIRST                ║');
    console.log('╠════════════════════════════════════════════════════════╣');
    console.log('║                                                        ║');
    log.success(`Serwer uruchomiony na http://localhost:${PORT}`);
    console.log('║                                                        ║');
    log.info(`Plik metryki: ${METRYKI_PATH}`);
    console.log('║                                                        ║');
    console.log('║  Otwórz przeglądarkę: http://localhost:3456            ║');
    console.log('║  Zatrzymaj serwer: Ctrl+C                              ║');
    console.log('║                                                        ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    console.log('');
});
