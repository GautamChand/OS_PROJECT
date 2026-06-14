// dragdrop.js — Handle drag-and-drop folder selection

function initDragAndDrop(dropzoneId, callback) {
    const dropzone = document.getElementById(dropzoneId);
    if (!dropzone) return;
    
    // Make the dropzone card clickable to open path prompt
    dropzone.addEventListener('click', () => {
        promptForPath();
    });
    
    // Drag/drop folders from the desktop has limitations in browser sandboxes,
    // so we support folder drops (we get the directory path or file names)
    // and we also provide a manual path input form.
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-active');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-active');
        }, false);
    });
    
    dropzone.addEventListener('drop', async (e) => {
        const dt = e.dataTransfer;
        
        // Check for folder/files
        if (dt.items && dt.items.length > 0) {
            // Note: browser sandboxes prevent us from reading the full path of a dropped folder
            // for security reasons, but in this local app context, we can ask for path input or
            // read what we can, and guide the user.
            const item = dt.items[0];
            if (item.kind === 'file') {
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
                if (entry && entry.isDirectory) {
                    UI.showToast(`Selected directory: "${entry.name}". Please enter its full path.`, 'info');
                    promptForPath(entry.name);
                } else {
                    const file = item.getAsFile();
                    // Just prompt with the directory of the file if possible
                    UI.showToast(`Dropped file: "${file.name}". Please specify the directory path.`, 'warning');
                }
            }
        }
    });
}

function promptForPath(suggestedName = '') {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    
    // Close modal if user clicks on the overlay backdrop itself
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });

    modal.innerHTML = `
        <div class="modal" style="max-width: 500px; width: 90%;">
            <div class="modal-header">
                <h3 class="modal-title">Set Monitored Folder</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body" style="padding-top: 15px;">
                <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 16px;">
                    Enter the absolute system path of the directory you want to monitor:
                </p>
                <div class="form-group" style="margin-bottom: 20px;">
                    <input type="text" id="manualFolderPath" class="form-control" 
                           placeholder="e.g. C:\\Users\\Name\\Documents\\MyFolder" 
                           style="width:100%; padding:12px; border-radius:var(--radius-md); border:1px solid var(--border-glass); background:var(--bg-input); color:var(--text-primary); font-family: 'JetBrains Mono', monospace; font-size: 13px;">
                </div>
                <div class="modal-footer" style="padding: 0; display:flex; justify-content:flex-end; gap:10px;">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="btn btn-primary" id="btnConfirmPath">Set Folder</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const input = document.getElementById('manualFolderPath');
    input.focus();
    
    document.getElementById('btnConfirmPath').addEventListener('click', async () => {
        const path = input.value.trim();
        if (!path) {
            UI.showToast('Path cannot be empty', 'warning');
            return;
        }
        
        try {
            const result = await API.post('/api/folders/set', { path });
            if (result.success) {
                UI.showToast(`Monitored folder updated to: ${result.path}`, 'success');
                modal.remove();
                if (window.onFolderUpdated) {
                    window.onFolderUpdated(result.path);
                }
            }
        } catch (error) {
            // Toast error already shown in API.request
        }
    });
}
