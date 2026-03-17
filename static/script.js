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
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'file-remove';
        removeBtn.innerHTML = '×';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            selectedFiles.splice(index, 1);
            updateFileList();
        };

        item.appendChild(nameSpan);
        item.appendChild(removeBtn);
        fileList.appendChild(item);
    });
}

function showStatus(element, message, type) {
    element.innerHTML = message;
    element.className = `status-msg show status-${type}`;
}

// Upload Form Submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    showStatus(uploadStatus, '<span class="spinner">↻</span> Uploading & processing...', 'info');
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
            showStatus(uploadStatus, 'Successfully uploaded: ' + data.message, 'success');
            selectedFiles = []; // Clear queue
            updateFileList();
        } else {
            showStatus(uploadStatus, 'Error: ' + (data.detail || data.error || 'Upload failed'), 'error');
            uploadBtn.disabled = false;
        }
    } catch (error) {
        showStatus(uploadStatus, 'Network error during upload.', 'error');
        uploadBtn.disabled = false;
    }
});

// --- Query Logic ---

queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const company = document.getElementById('company').value.trim();
    const queryText = document.getElementById('query_text').value.trim();
    const aiQueryText = document.getElementById('ai_query').value.trim();

    if (!company || !queryText) {
        showStatus(queryStatus, 'Please enter company and query text.', 'error');
        return;
    }

    showStatus(queryStatus, '<span class="spinner">↻</span> Searching Vector DB & generating insights...', 'info');
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

        const data = await response.json();

        if (response.ok) {
            showStatus(queryStatus, 'Generation complete!', 'success');
            
            // Render marked.js output if available, else standard text
            if (typeof marked !== 'undefined') {
                aiResponse.innerHTML = marked.parse(data.answer);
            } else {
                aiResponse.innerHTML = `<pre>${data.answer}</pre>`;
            }

            // Render raw matches
            renderRawMatches(data.raw_matches);
            
            resultsArea.classList.remove('hidden');
        } else {
            showStatus(queryStatus, 'Error: ' + (data.detail || data.error || 'Query failed'), 'error');
        }
    } catch (error) {
        showStatus(queryStatus, 'Failed to reach the server. Is it running?', 'error');
    } finally {
        queryBtn.disabled = false;
    }
});

function renderRawMatches(matches) {
    rawMatches.innerHTML = '';
    if (!matches || matches.length === 0) {
        rawMatches.innerHTML = '<p class="match-text">No direct context matches returned.</p>';
        return;
    }

    matches.forEach(match => {
        const item = document.createElement('div');
        item.className = 'match-item';
        
        const meta = document.createElement('div');
        meta.className = 'match-meta';
        meta.textContent = `Page ${match.page} | Score: ${match.score.toFixed(3)}`;
        
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
        toggleDebugBtn.innerHTML = 'View Raw Vector DB Matches';
    } else {
        toggleDebugBtn.innerHTML = 'Hide Raw Matches';
    }
});
