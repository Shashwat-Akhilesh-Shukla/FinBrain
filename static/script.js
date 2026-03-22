// Configuration & State
let selectedFiles = [];

// DOM Elements
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const uploadBtn = document.getElementById('upload-btn');
const uploadForm = document.getElementById('upload-form');
const uploadStatus = document.getElementById('upload-status');

const queryForm = document.getElementById('query-form');
const queryBtn = document.getElementById('query-btn');
const queryStatus = document.getElementById('query-status');
const resultsArea = document.getElementById('results-area');
const aiResponse = document.getElementById('ai-response');
const toggleDebugBtn = document.getElementById('toggle-debug');
const rawMatches = document.getElementById('raw-matches');

// --- File Upload Logic ---

// Trigger file select window
dropArea.addEventListener('click', () => fileInput.click());

// Drag & Drop Handling
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
});

dropArea.addEventListener('drop', handleDrop, false);
fileInput.addEventListener('change', handleFiles, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFileArray(Array.from(files));
}

function handleFiles(e) {
    handleFileArray(Array.from(e.target.files));
}

function handleFileArray(files) {
    files.forEach(file => {
        if (file.type === 'application/pdf' && !selectedFiles.some(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    });
    updateFileList();
}

function updateFileList() {
    fileList.innerHTML = '';
    
    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
    } else {
        uploadBtn.disabled = true;
    }

    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'file-item-info';
        infoDiv.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            <span>${file.name}</span>
            <span style="color:#94a3b8; font-size:0.8rem; margin-left:8px;">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
        `;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'file-remove';
        removeBtn.title = 'Remove file';
        removeBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            selectedFiles.splice(index, 1);
            updateFileList();
        };

        item.appendChild(infoDiv);
        item.appendChild(removeBtn);
        fileList.appendChild(item);
    });
}

function showStatus(element, message, type) {
    element.innerHTML = message;
    element.className = `status-msg show status-${type}`;
}

const spinnerSvg = '<span class="spinner"></span>';
const successSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
const errorSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';

// Upload Form Submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    showStatus(uploadStatus, `${spinnerSvg} Uploading & processing documents...`, 'info');
    uploadBtn.disabled = true;

    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(uploadStatus, `${successSvg} Successfully uploaded: ${data.message}`, 'success');
            selectedFiles = []; // Clear queue
            updateFileList();
        } else {
            showStatus(uploadStatus, `${errorSvg} Error: ${data.detail || data.error || 'Upload failed'}`, 'error');
            uploadBtn.disabled = false;
        }
    } catch (error) {
        showStatus(uploadStatus, `${errorSvg} Network error during upload.`, 'error');
        uploadBtn.disabled = false;
    }
});

// --- Query Logic ---

// Configure marked.js ONCE at module level with GFM (tables) enabled
marked.use({ gfm: true, breaks: true });

queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const company = document.getElementById('company').value.trim();
    const queryText = document.getElementById('query_text').value.trim();
    const aiQueryText = document.getElementById('ai_query').value.trim();

    if (!company || !queryText) {
        showStatus(queryStatus, `${errorSvg} Please enter entity and query text.`, 'error');
        return;
    }

    console.group('[FinBrain] Query Request');
    console.log('Company:', company);
    console.log('Vector Search Target:', queryText);
    console.log('AI Instruction:', aiQueryText);
    console.groupEnd();

    showStatus(queryStatus, `${spinnerSvg} Searching Vector DB & generating insights...`, 'info');
    queryBtn.disabled = true;
    resultsArea.classList.add('hidden');

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company: company,
                query_text: queryText,
                ai_query: aiQueryText
            })
        });

        console.group('[FinBrain] API Response');
        console.log('HTTP Status:', response.status, response.statusText);

        const data = await response.json();
        console.log('Raw payload:', data);

        if (response.ok) {
            console.log('--- LLM Answer (raw text) ---');
            console.log(data.answer);
            console.log('--- Raw Matches ---', data.raw_matches);
            console.groupEnd();

            showStatus(queryStatus, `${successSvg} Generation complete!`, 'success');

            // Render markdown with GFM tables via marked.js
            const rendered = marked.parse(data.answer);
            console.debug('[FinBrain] Rendered HTML:', rendered);
            aiResponse.innerHTML = rendered;

            // Render raw matches
            renderRawMatches(data.raw_matches);
            
            resultsArea.classList.remove('hidden');
        } else {
            console.error('[FinBrain] API error payload:', data);
            console.groupEnd();
            showStatus(queryStatus, `${errorSvg} Error: ${data.detail || data.error || 'Query failed'}`, 'error');
        }
    } catch (error) {
        console.error('[FinBrain] Network/parse error:', error);
        showStatus(queryStatus, `${errorSvg} Failed to reach the server. Is it running?`, 'error');
    } finally {
        queryBtn.disabled = false;
    }
});

function renderRawMatches(matches) {
    rawMatches.innerHTML = '';
    if (!matches || matches.length === 0) {
        rawMatches.innerHTML = '<p class="match-text">No direct context matches returned from Vector Search.</p>';
        return;
    }

    matches.forEach(match => {
        const item = document.createElement('div');
        item.className = 'match-item';
        
        const meta = document.createElement('div');
        meta.className = 'match-meta';
        
        const pageSpan = document.createElement('span');
        pageSpan.textContent = `Page ${match.page}`;
        
        const scoreSpan = document.createElement('span');
        scoreSpan.className = 'match-score';
        scoreSpan.textContent = `Confidence: ${(match.score * 100).toFixed(1)}%`;
        
        meta.appendChild(pageSpan);
        meta.appendChild(scoreSpan);
        
        const text = document.createElement('div');
        text.className = 'match-text';
        text.textContent = match.text;

        item.appendChild(meta);
        item.appendChild(text);
        rawMatches.appendChild(item);
    });
}

// Toggle raw matches visibility
toggleDebugBtn.addEventListener('click', () => {
    rawMatches.classList.toggle('hidden');
    if (rawMatches.classList.contains('hidden')) {
        toggleDebugBtn.innerHTML = 'View Source Matches';
    } else {
        toggleDebugBtn.innerHTML = 'Hide Source Matches';
    }
});

// Theme Toggle Logic
const themeToggleBtn = document.getElementById('theme-toggle');
if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        if (document.body.classList.contains('dark-mode')) {
            themeToggleBtn.textContent = 'Light Mode';
        } else {
            themeToggleBtn.textContent = 'Dark Mode';
        }
    });
}
