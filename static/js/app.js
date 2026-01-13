/**
 * MyPanel Common JavaScript Utilities
 */

// API Helper
const API = {
    async get(url) {
        try {
            const res = await fetch(url);
            return res.json();
        } catch (e) {
            console.error('API GET error:', e);
            return { error: e.message };
        }
    },

    async post(url, data) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return res.json();
        } catch (e) {
            console.error('API POST error:', e);
            return { error: e.message };
        }
    },

    async put(url, data) {
        try {
            const res = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return res.json();
        } catch (e) {
            console.error('API PUT error:', e);
            return { error: e.message };
        }
    },

    async delete(url) {
        try {
            const res = await fetch(url, { method: 'DELETE' });
            return res.json();
        } catch (e) {
            console.error('API DELETE error:', e);
            return { error: e.message };
        }
    }
};

// Toast Notification
function showToast(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-indigo-500',
        warning: 'bg-yellow-500'
    };

    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 ${colors[type] || colors.info} text-white px-6 py-3 rounded-xl shadow-lg fade-in z-50`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Format bytes to human-readable
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

// Format date
function formatDate(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Скопировано!', 'success');
    } catch (e) {
        showToast('Не удалось скопировать', 'error');
    }
}

// Confirm dialog
function confirmAction(message) {
    return new Promise((resolve) => {
        resolve(confirm(message));
    });
}

// Loading indicator
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="flex items-center justify-center py-12">
                <div class="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        `;
    }
}

// Empty state
function showEmpty(containerId, message = 'Нет данных', icon = null) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-400">
                ${icon ? `<div class="mb-4">${icon}</div>` : ''}
                <p>${message}</p>
            </div>
        `;
    }
}
