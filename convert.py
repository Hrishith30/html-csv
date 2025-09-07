from flask import Flask, request, render_template_string, send_file, jsonify
import pandas as pd
import json
from io import BytesIO, StringIO
import uuid
import os
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Universal Data Converter | JSON <> CSV</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" type="image/svg+xml" href="https://cdn.jsdelivr.net/npm/bootstrap-icons/icons/file-earmark.svg">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body { background-color: #f8f9fa; display: flex; flex-direction: column; min-height: 100vh; }
        .main-container { flex: 1; }
        .card { border: none; border-radius: 0.75rem; }
        .drop-zone { border: 2px dashed #ced4da; border-radius: 0.5rem; padding: 40px; text-align: center; cursor: pointer; background: #fff; transition: background-color 0.2s ease, border-color 0.2s ease; }
        .drop-zone.hover { background-color: #e9ecef; border-color: #0d6efd; }
        .drop-zone .icon { font-size: 3rem; color: #6c757d; }
        .results-area { display: none; }
        #spinner-j2c, #spinner-c2j { display: none; }
        .table th { cursor: pointer; user-select: none; }
        .table th:hover { background-color: #f1f1f1; }
        .table td.null { background-color: #fff0f1; }
        .toast-container { z-index: 1090; }
        .file-info { background-color: #e9ecef; padding: 8px 12px; border-radius: 6px; display: none; }
        .card-header h5 { margin-bottom: 0; }
        .text-input { font-family: monospace; font-size: 0.9rem; min-height: 200px; }
        #json-output { min-height: 300px; }
        .nav-link { cursor: pointer; }
        .footer { padding: 1rem 0; text-align: center; font-size: 0.9em; color: #6c757d; }
        .footer a { cursor: pointer; }
    </style>
</head>
<body>

<div class="container-xl my-5 main-container">
    <div class="text-center mb-5">
        <h1 class="display-5">Universal Data Converter</h1>
        <p class="lead text-muted">Seamlessly convert between JSON and CSV formats.</p>
    </div>

    <div class="card shadow-sm">
        <div class="card-header bg-white border-0 p-3">
             <ul class="nav nav-pills nav-fill" id="main-tabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#json-to-csv-pane" type="button" role="tab">
                        <i class="bi bi-filetype-json"></i> JSON <i class="bi bi-arrow-right-short"></i> CSV <i class="bi bi-file-earmark-spreadsheet"></i>
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#csv-to-json-pane" type="button" role="tab">
                        <i class="bi bi-file-earmark-spreadsheet"></i> CSV <i class="bi bi-arrow-right-short"></i> JSON <i class="bi bi-filetype-json"></i>
                    </button>
                </li>
            </ul>
        </div>

        <div class="tab-content" id="main-tab-content">
            <div class="tab-pane fade show active" id="json-to-csv-pane" role="tabpanel">
                <div class="card-body p-4">
                    <ul class="nav nav-tabs nav-fill mb-3">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#j2c-upload-tab" type="button">Upload File</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#j2c-paste-tab" type="button">Paste Text</button></li>
                    </ul>
                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="j2c-upload-tab">
                            <div class="drop-zone" id="j2c-drop-zone">
                                <div class="icon"><i class="bi bi-cloud-arrow-up-fill"></i></div>
                                <p class="mb-0 mt-2"><strong>Drag & Drop</strong> a JSON file here or <strong>click to select</strong></p>
                            </div>
                            <input type="file" id="j2c-file-input" accept=".json,application/json" class="d-none">
                            <div class="file-info mt-3" id="j2c-file-info">
                                <span><i class="bi bi-file-earmark-text"></i> <strong id="j2c-file-name"></strong></span>
                                <span class="mx-2 badge bg-secondary" id="j2c-file-size"></span>
                                <button type="button" class="btn-close float-end" id="j2c-clear-btn"></button>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="j2c-paste-tab">
                            <textarea id="j2c-text-input" class="form-control text-input" placeholder='[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'></textarea>
                        </div>
                    </div>
                    <div class="d-grid mt-4">
                        <button id="j2c-convert-btn" class="btn btn-primary btn-lg">
                            <span id="spinner-j2c" class="spinner-border spinner-border-sm me-2"></span>
                            <span id="j2c-btn-text">Convert to CSV</span>
                        </button>
                    </div>
                </div>
                <div class="results-area p-4 pt-0" id="j2c-results-area">
                    <div class="card shadow-sm mb-4">
                        <div class="card-header bg-light"><h5><i class="bi bi-bar-chart-line-fill me-2 text-info"></i>JSON Stats & Schema</h5></div>
                        <div class="card-body" id="j2c-stats-body"></div>
                    </div>
                    <div class="card shadow-sm">
                        <div class="card-header bg-light d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-table me-2 text-primary"></i>CSV Preview (First 10 Rows)</h5>
                            <a id="j2c-download-btn" class="btn btn-success btn-sm" href="#"><i class="bi bi-download"></i> Download Full CSV</a>
                        </div>
                        <div class="card-body">
                            <p class="text-muted small mb-2">Click table headers to sort preview data.</p>
                            <div class="table-responsive"><table class="table table-bordered table-striped table-hover" id="j2c-preview-table"></table></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tab-pane fade" id="csv-to-json-pane" role="tabpanel">
                 <div class="card-body p-4">
                    <ul class="nav nav-tabs nav-fill mb-3">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#c2j-upload-tab" type="button">Upload File</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#c2j-paste-tab" type="button">Paste Text</button></li>
                    </ul>
                     <div class="tab-content">
                        <div class="tab-pane fade show active" id="c2j-upload-tab">
                            <div class="drop-zone" id="c2j-drop-zone">
                                <div class="icon"><i class="bi bi-cloud-arrow-up-fill"></i></div>
                                <p class="mb-0 mt-2"><strong>Drag & Drop</strong> a CSV file here or <strong>click to select</strong></p>
                            </div>
                            <input type="file" id="c2j-file-input" accept=".csv,text/csv" class="d-none">
                            <div class="file-info mt-3" id="c2j-file-info">
                                <span><i class="bi bi-file-earmark-spreadsheet"></i> <strong id="c2j-file-name"></strong></span>
                                <span class="mx-2 badge bg-secondary" id="c2j-file-size"></span>
                                <button type="button" class="btn-close float-end" id="c2j-clear-btn"></button>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="c2j-paste-tab">
                            <textarea id="c2j-text-input" class="form-control text-input" placeholder="id,name&#10;1,John&#10;2,Jane"></textarea>
                        </div>
                    </div>
                    <div class="d-grid mt-4">
                        <button id="c2j-convert-btn" class="btn btn-primary btn-lg">
                            <span id="spinner-c2j" class="spinner-border spinner-border-sm me-2"></span>
                            <span id="c2j-btn-text">Convert to JSON</span>
                        </button>
                    </div>
                </div>
                <div class="results-area p-4 pt-0" id="c2j-results-area">
                    <div class="card shadow-sm mb-4">
                        <div class="card-header bg-light"><h5><i class="bi bi-bar-chart-line-fill me-2 text-info"></i>CSV Stats & Schema</h5></div>
                        <div class="card-body" id="c2j-stats-body"></div>
                    </div>
                    <div class="card shadow-sm">
                         <div class="card-header bg-light d-flex justify-content-between align-items-center">
                            <h5><i class="bi bi-filetype-json me-2 text-warning"></i>JSON Output</h5>
                            <div>
                                <button id="c2j-copy-btn" class="btn btn-secondary btn-sm"><i class="bi bi-clipboard"></i> Copy</button>
                                <a id="c2j-download-btn" class="btn btn-success btn-sm" href="#" download="data.json"><i class="bi bi-download"></i> Download .json</a>
                            </div>
                        </div>
                        <div class="card-body">
                            <textarea id="json-output" class="form-control text-input" readonly></textarea>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<footer class="footer">
    <div class="container-xl">
        <a data-bs-toggle="modal" data-bs-target="#bugReportModal" class="text-decoration-none">
            <i class="bi bi-bug-fill me-1"></i> Found a bug? Report it here
        </a>
    </div>
</footer>

<div class="modal fade" id="bugReportModal" tabindex="-1" aria-labelledby="bugReportModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="bugReportModalLabel">Report a Bug</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <form id="bug-report-form">
            <div class="mb-3">
                <label for="bug-name" class="form-label">Your Name</label>
                <input type="text" class="form-control" id="bug-name" required>
            </div>
            <div class="mb-3">
                <label for="bug-email" class="form-label">Your Email</label>
                <input type="email" class="form-control" id="bug-email" required>
            </div>
            <div class="mb-3">
                <label for="bug-message" class="form-label">Message</label>
                <textarea class="form-control" id="bug-message" rows="4" required></textarea>
                <div class="form-text">Please describe the bug and the steps to reproduce it.</div>
            </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        <button type="submit" form="bug-report-form" class="btn btn-primary" id="submit-bug-btn">
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
            Submit Report
        </button>
      </div>
    </div>
  </div>
</div>

<div class="toast-container position-fixed bottom-0 end-0 p-3"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', () => {
    // --- Utility Functions (Defined ONCE) ---
    const showToast = (message, type = 'danger') => {
        const toastId = `toast-${Date.now()}`;
        const toastHTML = `<div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true"><div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div></div>`;
        document.querySelector('.toast-container').insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    };

    const formatBytes = (bytes, decimals = 2) => {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    };

    const setupFileHandler = (type) => {
        const dropZone = document.getElementById(`${type}-drop-zone`);
        const fileInput = document.getElementById(`${type}-file-input`);
        const fileInfo = document.getElementById(`${type}-file-info`);
        const fileNameEl = document.getElementById(`${type}-file-name`);
        const fileSizeEl = document.getElementById(`${type}-file-size`);
        const clearBtn = document.getElementById(`${type}-clear-btn`);

        const resetFileUI = () => {
            fileInput.value = '';
            fileInfo.style.display = 'none';
            dropZone.innerHTML = `<div class="icon"><i class="bi bi-cloud-arrow-up-fill"></i></div><p class="mb-0 mt-2"><strong>Drag & Drop</strong> a ${type.toUpperCase()} file here or <strong>click to select</strong></p>`;
        };
        const handleFileSelection = (file) => {
            if (!file) return;
            fileNameEl.textContent = file.name;
            fileSizeEl.textContent = formatBytes(file.size);
            fileInfo.style.display = 'block';
            dropZone.innerHTML = `<div class="icon"><i class="bi bi-check-circle-fill text-success"></i></div><p class="mb-0">File <strong>${file.name}</strong> is ready!</p>`;
        };

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('hover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('hover'));
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.classList.remove('hover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelection(fileInput.files[0]);
            }
        });
        fileInput.addEventListener('change', () => handleFileSelection(fileInput.files[0]));
        clearBtn.addEventListener('click', resetFileUI);
    };

    const displayStats = (result, containerId) => {
        const statsBody = document.getElementById(containerId);
        let statsHtml = `<p><strong>Memory Usage:</strong> ${formatBytes(result.stats.memory_usage)}</p>`;
        statsHtml += '<div class="table-responsive"><table class="table table-sm table-bordered"><thead><tr><th>Column</th><th>Data Type</th><th>Non-Null Count</th><th>Filled (%)</th></tr></thead><tbody>';
        for (const col in result.stats.dtypes) {
            const count = result.stats.non_null_counts[col];
            const filled = (count / result.total_rows * 100).toFixed(2);
            statsHtml += `<tr><td>${col}</td><td>${result.stats.dtypes[col]}</td><td>${count}</td><td>${filled}%</td></tr>`;
        }
        statsHtml += '</tbody></table></div>';
        statsBody.innerHTML = statsHtml;
    };

    const renderJ2CTable = (columns, data) => {
        const previewTable = document.getElementById('j2c-preview-table');
        previewTable.innerHTML = '';
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        previewTable.appendChild(thead);
        const tbody = document.createElement('tbody');
        data.forEach(row => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row[col];
                td.textContent = (value === 'null' || value === null || value === undefined) ? 'null' : value;
                if (value === 'null' || value === null) td.classList.add('null');
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        previewTable.appendChild(tbody);
    };

    // --- JSON to CSV Logic ---
    setupFileHandler('j2c');
    document.getElementById('j2c-convert-btn').addEventListener('click', async () => {
        const fileInput = document.getElementById('j2c-file-input');
        const textInput = document.getElementById('j2c-text-input');
        const activeTab = document.querySelector('#json-to-csv-pane .nav-tabs .nav-link.active').getAttribute('data-bs-target');
        let sourceData;
        let fileName = 'pasted_data.json';
        if (activeTab === '#j2c-upload-tab') {
            if (!fileInput.files.length) { showToast("Please select a JSON file."); return; }
            sourceData = fileInput.files[0];
            fileName = sourceData.name;
        } else {
            if (textInput.value.trim() === '') { showToast("Please paste JSON text."); return; }
            sourceData = new Blob([textInput.value], { type: 'application/json' });
        }
        const convertBtn = document.getElementById('j2c-convert-btn');
        const spinner = document.getElementById('spinner-j2c');
        const btnText = document.getElementById('j2c-btn-text');
        const resultsArea = document.getElementById('j2c-results-area');
        convertBtn.disabled = true;
        spinner.style.display = 'inline-block';
        btnText.textContent = 'Processing...';
        resultsArea.style.display = 'none';
        const formData = new FormData();
        formData.append('file', sourceData, fileName);
        try {
            const response = await fetch('/convert_to_csv', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            displayStats(result, 'j2c-stats-body');
            document.getElementById('j2c-download-btn').href = result.csv_url;
            renderJ2CTable(result.preview_columns, result.preview_data);
            resultsArea.style.display = 'block';
        } catch (error) {
            showToast(`Conversion failed: ${error.message}`);
        } finally {
            convertBtn.disabled = false;
            spinner.style.display = 'none';
            btnText.textContent = 'Convert to CSV';
        }
    });
    
    // --- CSV to JSON Logic ---
    setupFileHandler('c2j');
    document.getElementById('c2j-convert-btn').addEventListener('click', async () => {
        const fileInput = document.getElementById('c2j-file-input');
        const textInput = document.getElementById('c2j-text-input');
        const activeTab = document.querySelector('#csv-to-json-pane .nav-tabs .nav-link.active').getAttribute('data-bs-target');
        let sourceData;
        let fileName = 'pasted_data.csv';
        if (activeTab === '#c2j-upload-tab') {
            if (!fileInput.files.length) { showToast("Please select a CSV file."); return; }
            sourceData = fileInput.files[0];
            fileName = sourceData.name;
        } else {
            if (textInput.value.trim() === '') { showToast("Please paste CSV text."); return; }
            sourceData = new Blob([textInput.value], { type: 'text/csv' });
        }
        const convertBtn = document.getElementById('c2j-convert-btn');
        const spinner = document.getElementById('spinner-c2j');
        const btnText = document.getElementById('c2j-btn-text');
        const resultsArea = document.getElementById('c2j-results-area');
        convertBtn.disabled = true;
        spinner.style.display = 'inline-block';
        btnText.textContent = 'Processing...';
        resultsArea.style.display = 'none';
        const formData = new FormData();
        formData.append('file', sourceData, fileName);
        try {
            const response = await fetch('/convert_to_json', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            displayStats(result, 'c2j-stats-body');
            document.getElementById('json-output').value = JSON.stringify(result.json_data, null, 2);
            const downloadBtn = document.getElementById('c2j-download-btn');
            downloadBtn.href = result.json_url;
            downloadBtn.download = result.json_name;
            resultsArea.style.display = 'block';
        } catch (error) {
            showToast(`Conversion failed: ${error.message}`);
        } finally {
            convertBtn.disabled = false;
            spinner.style.display = 'none';
            btnText.textContent = 'Convert to JSON';
        }
    });
    document.getElementById('c2j-copy-btn').addEventListener('click', () => {
        navigator.clipboard.writeText(document.getElementById('json-output').value)
            .then(() => showToast("JSON copied to clipboard!", 'success'));
    });

    // --- Bug Report Logic ---
    const bugReportForm = document.getElementById('bug-report-form');
    const submitBugBtn = document.getElementById('submit-bug-btn');
    const bugModal = new bootstrap.Modal(document.getElementById('bugReportModal'));

    bugReportForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('bug-name').value;
        const email = document.getElementById('bug-email').value;
        const message = document.getElementById('bug-message').value;
        if (!name || !email || !message) {
            showToast("Please fill out all fields in the bug report.");
            return;
        }
        const spinner = submitBugBtn.querySelector('.spinner-border');
        submitBugBtn.disabled = true;
        spinner.style.display = 'inline-block';
        try {
            const response = await fetch('/submit_bug_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, message })
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to send report.');
            }
            showToast("Thank you! Your bug report has been submitted.", 'success');
            bugModal.hide();
            bugReportForm.reset();
        } catch (error) {
            showToast(`Error: ${error.message}`);
        } finally {
            submitBugBtn.disabled = false;
            spinner.style.display = 'none';
        }
    });
});
</script>
</body>
</html>
'''

# In-memory store for generated files.
FILE_STORE = {}

# --- Email Configuration ---
# IMPORTANT: These are loaded from environment variables for security.
SENDER_EMAIL = os.environ.get('GMAIL_EMAIL')
SENDER_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
# This is the email address that will receive the bug reports.
# By default, it sends to itself. You can change this to a different address.
RECIPIENT_EMAIL = SENDER_EMAIL

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/submit_bug_report', methods=['POST'])
def submit_bug_report():
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        return jsonify({"error": "Mail server is not configured. Please contact the administrator."}), 500
    if not RECIPIENT_EMAIL:
         return jsonify({"error": "Recipient email is not configured."}), 500

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    if not all([name, email, message]):
        return jsonify({"error": "All fields are required."}), 400

    msg = EmailMessage()
    msg['Subject'] = f"Bug Report from {name} - Universal Data Converter"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(
        f"A new bug report has been submitted.\n\n"
        f"From: {name}\n"
        f"Reply-to Email: {email}\n\n"
        f"Message:\n{message}"
    )

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp_server.send_message(msg)
        return jsonify({"message": "Bug report submitted successfully."}), 200
    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "Mail server authentication failed. Check credentials."}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/convert_to_csv', methods=['POST'])
def convert_to_csv():
    file = request.files.get('file')
    if not file: return jsonify({"error": "No file or text provided."}), 400
    try:
        content = file.read().decode('utf-8')
        if not content.strip(): return jsonify({"error": "Input is empty."}), 400
        data = json.loads(content)
        if isinstance(data, dict): data = [data]
        df = pd.json_normalize(data, max_level=1)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error processing data: {e}"}), 400
    if df.empty: return jsonify({"error": "JSON resulted in empty data (must be an array of objects)."}), 400

    stats = {
        "memory_usage": int(df.memory_usage(deep=True).sum()),
        "dtypes": df.dtypes.apply(lambda x: str(x)).to_dict(),
        "non_null_counts": df.count().to_dict()
    }
    csv_buf = BytesIO()
    df.to_csv(csv_buf, index=False)
    file_id = str(uuid.uuid4())
    file_name = (file.filename.rsplit('.', 1)[0] + '.csv') if file.filename else 'data.csv'
    FILE_STORE[file_id] = (csv_buf.getvalue(), file_name, 'text/csv')
    return jsonify({
        "preview_data": df.head(10).fillna('null').to_dict(orient='records'),
        "preview_columns": list(df.columns),
        "csv_url": f"/download/{file_id}",
        "total_rows": len(df),
        "stats": stats
    })

@app.route('/convert_to_json', methods=['POST'])
def convert_to_json():
    file = request.files.get('file')
    if not file: return jsonify({"error": "No file or text provided."}), 400
    try:
        content = file.read().decode('utf-8')
        if not content.strip(): return jsonify({"error": "Input is empty."}), 400
        df = pd.read_csv(StringIO(content))
    except pd.errors.ParserError as e:
        return jsonify({"error": f"Malformed CSV: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error processing CSV: {e}"}), 400
    if df.empty: return jsonify({"error": "CSV resulted in empty data."}), 400
    
    stats = {
        "memory_usage": int(df.memory_usage(deep=True).sum()),
        "dtypes": df.dtypes.apply(lambda x: str(x)).to_dict(),
        "non_null_counts": df.count().to_dict()
    }
    df_clean = df.replace({pd.NA: None, pd.NaT: None}).where(pd.notna(df), None)
    json_data = json.loads(df_clean.to_json(orient='records', date_format='iso'))
    json_string = json.dumps(json_data, indent=2)
    file_id = str(uuid.uuid4())
    file_name = (file.filename.rsplit('.', 1)[0] + '.json') if file.filename else 'data.json'
    FILE_STORE[file_id] = (json_string.encode('utf-8'), file_name, 'application/json')
    return jsonify({
        "json_data": json_data,
        "json_url": f"/download/{file_id}",
        "json_name": file_name,
        "total_rows": len(df),
        "stats": stats
    })

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in FILE_STORE:
        return "File not found or has expired.", 404
    file_data, file_name, mimetype = FILE_STORE.pop(file_id)
    return send_file(
        BytesIO(file_data),
        as_attachment=True,
        download_name=file_name,
        mimetype=mimetype
    )

if __name__ == '__main__':
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        print("="*60)
        print("WARNING: GMAIL_EMAIL or GMAIL_APP_PASSWORD environment")
        print("         variables not set. The bug report feature will not work.")
        print("="*60)
    app.run(debug=True)