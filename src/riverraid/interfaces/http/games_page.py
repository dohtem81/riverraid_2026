GAMES_HTML = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>RiverRaid Recorded Games</title>
    <style>
        body {
            margin: 0;
            padding: 24px;
            font-family: Arial, sans-serif;
            background: #0f1117;
            color: #e6e6e6;
        }
        h1 {
            margin: 0 0 16px 0;
            font-size: 24px;
        }
        #status {
            margin: 0 0 16px 0;
            color: #a9b1c6;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border: 1px solid #2a3240;
        }
        th, td {
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #2a3240;
            vertical-align: top;
            font-size: 13px;
        }
        th {
            background: #1f2633;
            color: #c9d4ec;
            position: sticky;
            top: 0;
        }
        code {
            font-family: Menlo, Monaco, monospace;
            color: #f3b57a;
        }
        .empty {
            padding: 16px;
            color: #9aa7bd;
            border: 1px dashed #2a3240;
            background: #161b22;
        }
    </style>
</head>
<body>
    <h1>Recorded Games</h1>
    <div id=\"status\">Loading...</div>
    <div id=\"content\"></div>

    <script>
        const statusEl = document.getElementById('status');
        const contentEl = document.getElementById('content');

        function renderTable(rows) {
            if (!rows.length) {
                contentEl.innerHTML = '<div class=\"empty\">No recorded games yet.</div>';
                return;
            }

            const header = `
                <tr>
                    <th>id</th>
                    <th>pilot_name</th>
                    <th>score</th>
                    <th>level</th>
                    <th>started_at</th>
                    <th>finished_at</th>
                </tr>
            `;

            const body = rows.map((row) => `
                <tr>
                    <td><code>${row.id}</code></td>
                    <td>${row.pilot_name}</td>
                    <td>${row.score}</td>
                    <td>${row.level}</td>
                    <td>${row.started_at}</td>
                    <td>${row.finished_at}</td>
                </tr>
            `).join('');

            contentEl.innerHTML = `<table><thead>${header}</thead><tbody>${body}</tbody></table>`;
        }

        async function load() {
            try {
                const response = await fetch('/api/v1/games');
                if (!response.ok) {
                    throw new Error(`Failed to load games: HTTP ${response.status}`);
                }
                const rows = await response.json();
                statusEl.textContent = `Loaded ${rows.length} recorded game(s).`;
                renderTable(rows);
            } catch (err) {
                statusEl.textContent = err.message || 'Failed to load recorded games.';
                contentEl.innerHTML = '';
            }
        }

        load();
    </script>
</body>
</html>
"""
