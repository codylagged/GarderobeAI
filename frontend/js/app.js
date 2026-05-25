const API_URL = 'http://127.0.0.1:8000/api';

// Auth State Management
function setToken(token) { localStorage.setItem('access_token', token); }
function getToken() { return localStorage.getItem('access_token'); }
function logout() { localStorage.removeItem('access_token'); window.location.href = 'index.html'; }
function checkAuth() {
    const path = window.location.pathname;
    const isHome = path.endsWith('index.html') || path === '/';
    const isAuthPage = path.endsWith('login.html');

    if (!getToken() && !isHome && !isAuthPage) {
        window.location.href = 'login.html';
    } else if (getToken() && (isHome || isAuthPage)) {
        window.location.href = 'welcome.html';
    }
}

async function apiCall(endpoint, options = {}) {
    const headers = options.headers || {};
    if (!options.isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };
    
    if (options.isFormData) {
        // Browser sets multipart/form-data with boundary automatically
        delete config.headers['Content-Type']; 
    } else if (config.body && typeof config.body !== 'string') {
        config.body = JSON.stringify(config.body);
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, config);
        
        if (response.status === 204) {
            return null;
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 401) logout();
            throw new Error(data.error || data.detail || 'A server-side error occurred. Please try again.');
        }
        return data;
    } catch (error) {
        console.error('API Error:', error);
        if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            throw new Error("Unable to establish a connection with the server. Please verify your network status and try again.");
        }
        throw error;
    }
}

// Ensure Auth State is Correct on Page Load
document.addEventListener('DOMContentLoaded', checkAuth);
