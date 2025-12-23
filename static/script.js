const API_URL = '/api';

// Helper para token
function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = '/login';
    }
}

// Fetch con auth
async function authFetch(url, options = {}) {
    options.headers = {
        ...options.headers,
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
    };
    const res = await fetch(url, options);
    if (res.status === 401) {
        logout();
    }
    return res;
}

// Para todas las páginas que necesitan login
if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
    requireAuth();
}