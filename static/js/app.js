// app.js — Main application JavaScript

// Global API Helper
const API = {
    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`API Error [${url}]:`, error);
            UI.showToast(error.message || 'An unexpected error occurred', 'danger');
            throw error;
        }
    },
    
    get(url) {
        return this.request(url);
    },
    
    post(url, body = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }
};

// Global UI Utilities
const UI = {
    showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'warning') icon = '⚠️';
        if (type === 'danger') icon = '🚨';
        
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(toast);
        
        // Trigger reflow for slide-in animation
        toast.offsetHeight;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    },
    
    formatPercent(ratio) {
        return (ratio * 100).toFixed(1) + '%';
    },
    
    formatDateTime(isoString) {
        if (!isoString) return 'Never';
        let parsedString = isoString;
        if (isoString.includes(' ') && !isoString.includes('T') && !isoString.endsWith('Z')) {
            parsedString = isoString.replace(' ', 'T') + 'Z';
        } else if (!isoString.includes('T') && !isoString.endsWith('Z') && !isoString.includes('+') && !isoString.includes('-')) {
            parsedString = isoString + 'Z';
        }
        const date = new Date(parsedString);
        return date.toLocaleString();
    },
    
    formatRelativeTime(isoString) {
        if (!isoString) return 'Never';
        let parsedString = isoString;
        if (isoString.includes(' ') && !isoString.includes('T') && !isoString.endsWith('Z')) {
            parsedString = isoString.replace(' ', 'T') + 'Z';
        } else if (!isoString.includes('T') && !isoString.endsWith('Z') && !isoString.includes('+') && !isoString.includes('-')) {
            parsedString = isoString + 'Z';
        }
        const date = new Date(parsedString);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSecs < 60) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
};

// Background services monitor
async function updateSystemStatus() {
    try {
        const status = await API.get('/api/status');
        
        const watcherActive = status.watcher && status.watcher.is_running;
        const schedulerActive = status.scheduler && status.scheduler.is_running;
        
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (statusDot && statusText) {
            if (watcherActive && schedulerActive) {
                statusDot.className = 'status-dot';
                statusText.innerText = 'Monitoring Active';
            } else if (watcherActive || schedulerActive) {
                statusDot.className = 'status-dot warning';
                statusText.innerText = 'Partial Monitoring';
            } else {
                statusDot.className = 'status-dot inactive';
                statusText.innerText = 'Services Stopped';
            }
        }
        return status;
    } catch (error) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        if (statusDot && statusText) {
            statusDot.className = 'status-dot inactive';
            statusText.innerText = 'Connection Lost';
        }
    }
}

// Initial status check and periodic updates
document.addEventListener('DOMContentLoaded', () => {
    updateSystemStatus();
    setInterval(updateSystemStatus, 10000); // update every 10 seconds
});
