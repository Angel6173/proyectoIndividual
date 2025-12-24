// script.js - Sistema Completo de TaskFlow

/**********************************************
 * 1. SISTEMA DE AUTENTICACIÓN Y TOKENS
 **********************************************/
class AuthSystem {
    constructor() {
        this.token = localStorage.getItem('token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
        this.apiUrl = '/api';
    }

    // Verificar si hay token
    isAuthenticated() {
        return !!this.token;
    }

    // Guardar autenticación
    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
    }

    // Limpiar autenticación
    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }

    // Fetch con autorización
    async authFetch(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                this.clearAuth();
                window.location.href = '/login';
                throw new Error('Sesión expirada');
            }

            return response;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }

    // Cerrar sesión
    logout() {
        this.clearAuth();
        window.location.href = '/login';
    }

    // Proteger rutas
    requireAuth() {
        const publicRoutes = ['/login', '/register'];
        const currentPath = window.location.pathname;
        
        if (!this.isAuthenticated() && !publicRoutes.includes(currentPath)) {
            window.location.href = '/login';
        }
    }
}

// Instancia global de autenticación
const Auth = new AuthSystem();

/**********************************************
 * 2. SISTEMA DE NOTIFICACIONES
 **********************************************/
class NotificationSystem {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        this.container = document.createElement('div');
        this.container.className = 'notifications-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <div class="alert-icon">
                ${this.getIcon(type)}
            </div>
            <div class="alert-content">${message}</div>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(notification);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, duration);
        }
    }

    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }
}

const Notify = new NotificationSystem();

/**********************************************
 * 3. SISTEMA DE CARGA (LOADING)
 **********************************************/
class LoadingSystem {
    show(container = document.body) {
        const loader = document.createElement('div');
        loader.className = 'loading';
        loader.innerHTML = `
            <div class="loading-spinner"></div>
            <p>Cargando...</p>
        `;
        container.appendChild(loader);
        return loader;
    }

    hide(loader) {
        if (loader && loader.parentElement) {
            loader.remove();
        }
    }
}

const Loader = new LoadingSystem();

/**********************************************
 * 4. MANEJO DE TAREAS
 **********************************************/
class TaskManager {
    constructor() {
        this.tasks = [];
        this.categories = [];
    }

    // Cargar todas las tareas
    async loadTasks() {
        try {
            const response = await Auth.authFetch('/api/tasks');
            if (response.ok) {
                this.tasks = await response.json();
                return this.tasks;
            }
            return [];
        } catch (error) {
            Notify.show('Error al cargar tareas', 'error');
            return [];
        }
    }

    // Cargar categorías
    async loadCategories() {
        try {
            const response = await Auth.authFetch('/api/categories');
            if (response.ok) {
                this.categories = await response.json();
                return this.categories;
            }
            return [];
        } catch (error) {
            Notify.show('Error al cargar categorías', 'error');
            return [];
        }
    }

    // Crear nueva tarea
    async createTask(taskData) {
        try {
            const response = await Auth.authFetch('/api/tasks', {
                method: 'POST',
                body: JSON.stringify(taskData)
            });

            if (response.ok) {
                Notify.show('Tarea creada exitosamente', 'success');
                return true;
            }
            return false;
        } catch (error) {
            Notify.show('Error al crear tarea', 'error');
            return false;
        }
    }

    // Actualizar tarea
    async updateTask(id, updates) {
        try {
            const response = await Auth.authFetch(`/api/tasks/${id}`, {
                method: 'PUT',
                body: JSON.stringify(updates)
            });

            if (response.ok) {
                Notify.show('Tarea actualizada', 'success');
                return true;
            }
            return false;
        } catch (error) {
            Notify.show('Error al actualizar tarea', 'error');
            return false;
        }
    }

    // Eliminar tarea
    async deleteTask(id) {
        if (!confirm('¿Estás seguro de eliminar esta tarea?')) return false;

        try {
            const response = await Auth.authFetch(`/api/tasks/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                Notify.show('Tarea eliminada', 'success');
                return true;
            }
            return false;
        } catch (error) {
            Notify.show('Error al eliminar tarea', 'error');
            return false;
        }
    }

    // Obtener estadísticas
    getStats() {
        const total = this.tasks.length;
        const completed = this.tasks.filter(t => t.completada).length;
        const pending = total - completed;
        const productivity = total > 0 ? Math.round((completed / total) * 100) : 0;

        return {
            total,
            completed,
            pending,
            productivity
        };
    }

    // Filtrar tareas
    filterTasks(filter = {}) {
        let filtered = [...this.tasks];

        if (filter.status === 'completed') {
            filtered = filtered.filter(t => t.completada);
        } else if (filter.status === 'pending') {
            filtered = filtered.filter(t => !t.completada);
        }

        if (filter.priority) {
            filtered = filtered.filter(t => t.prioridad === filter.priority);
        }

        if (filter.category) {
            filtered = filtered.filter(t => t.categoria === filter.category);
        }

        return filtered;
    }
}

/**********************************************
 * 5. SISTEMA DE ADMINISTRACIÓN
 **********************************************/
class AdminSystem {
    constructor() {
        this.isAdmin = false;
    }

    async login(password) {
        try {
            const response = await fetch('/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            if (response.ok) {
                this.isAdmin = true;
                Notify.show('Acceso admin concedido', 'success');
                return true;
            }
            
            const data = await response.json();
            Notify.show(data.error || 'Contraseña incorrecta', 'error');
            return false;
        } catch (error) {
            Notify.show('Error de conexión', 'error');
            return false;
        }
    }

    async logout() {
        await fetch('/admin/logout');
        this.isAdmin = false;
        window.location.reload();
    }

    async getUsers() {
        try {
            const response = await fetch('/api/admin/users');
            if (response.ok) return await response.json();
            return [];
        } catch (error) {
            Notify.show('Error al cargar usuarios', 'error');
            return [];
        }
    }

    async getStats() {
        try {
            const response = await fetch('/api/admin/stats');
            if (response.ok) return await response.json();
            return null;
        } catch (error) {
            Notify.show('Error al cargar estadísticas', 'error');
            return null;
        }
    }
}

/**********************************************
 * 6. UTILIDADES Y HELPERS
 **********************************************/
const Utils = {
    // Formatear fecha
    formatDate(dateString) {
        if (!dateString) return 'Sin fecha';
        
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    // Formatear fecha corta
    formatDateShort(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('es-ES');
    },

    // Obtener color de prioridad
    getPriorityColor(priority) {
        const colors = {
            alta: '#e53e3e',
            media: '#d69e2e',
            baja: '#48bb78'
        };
        return colors[priority] || '#a0aec0';
    },

    // Validar email
    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    // Generar ID único
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
};

/**********************************************
 * 7. COMPONENTES VUE REUTILIZABLES
 **********************************************/
const VueComponents = {
    // Componente de Tarea
    TaskComponent: {
        props: ['task'],
        template: `
            <div :class="['task-item', { completed: task.completada }]">
                <div class="task-content">
                    <div class="task-title">
                        <span v-if="task.completada">✅</span>
                        {{ task.titulo }}
                        <span :class="['priority-badge', 'priority-' + task.prioridad]">
                            {{ task.prioridad }}
                        </span>
                    </div>
                    <p v-if="task.descripcion" class="task-desc">
                        {{ task.descripcion }}
                    </p>
                    <div class="task-meta">
                        <span v-if="task.fecha_limite" class="meta-item">
                            📅 {{ formatDate(task.fecha_limite) }}
                        </span>
                        <span v-if="task.categoria" class="meta-item">
                            🏷️ {{ task.categoria }}
                        </span>
                        <span class="meta-item">
                            📌 {{ task.completada ? 'Completada' : 'Pendiente' }}
                        </span>
                    </div>
                </div>
                <div class="task-actions">
                    <button @click="$emit('toggle', task.id)" class="action-btn" 
                            :title="task.completada ? 'Marcar como pendiente' : 'Marcar como completada'">
                        {{ task.completada ? '↩️' : '✅' }}
                    </button>
                    <button @click="$emit('delete', task.id)" class="action-btn" title="Eliminar tarea">
                        🗑️
                    </button>
                </div>
            </div>
        `,
        methods: {
            formatDate(date) {
                return Utils.formatDateShort(date);
            }
        }
    },

    // Componente de Estadísticas
    StatsComponent: {
        props: ['stats'],
        template: `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-number">{{ stats.total }}</div>
                    <div class="stat-label">Total Tareas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">✅</div>
                    <div class="stat-number">{{ stats.completed }}</div>
                    <div class="stat-label">Completadas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">⏳</div>
                    <div class="stat-number">{{ stats.pending }}</div>
                    <div class="stat-label">Pendientes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📈</div>
                    <div class="stat-number">{{ stats.productivity }}%</div>
                    <div class="stat-label">Productividad</div>
                    <div class="stat-progress">
                        <div class="progress-bar" :style="{ width: stats.productivity + '%' }"></div>
                    </div>
                </div>
            </div>
        `
    }
};

/**********************************************
 * 8. APLICACIÓN PRINCIPAL VUE
 **********************************************/
function createTaskApp() {
    if (!document.getElementById('app')) return;

    const TaskApp = {
        data() {
            return {
                tasks: [],
                categories: [],
                loading: false,
                newTask: {
                    titulo: '',
                    descripcion: '',
                    categoria: '',
                    prioridad: 'media',
                    fecha_limite: ''
                },
                filter: {
                    status: 'all',
                    priority: '',
                    category: ''
                },
                stats: {
                    total: 0,
                    completed: 0,
                    pending: 0,
                    productivity: 0
                }
            };
        },

        computed: {
            filteredTasks() {
                return this.tasks.filter(task => {
                    let matches = true;
                    
                    if (this.filter.status === 'completed') {
                        matches = matches && task.completada;
                    } else if (this.filter.status === 'pending') {
                        matches = matches && !task.completada;
                    }
                    
                    if (this.filter.priority) {
                        matches = matches && task.prioridad === this.filter.priority;
                    }
                    
                    if (this.filter.category) {
                        matches = matches && task.categoria === this.filter.category;
                    }
                    
                    return matches;
                });
            }
        },

        methods: {
            async loadData() {
                this.loading = true;
                try {
                    const taskManager = new TaskManager();
                    [this.tasks, this.categories] = await Promise.all([
                        taskManager.loadTasks(),
                        taskManager.loadCategories()
                    ]);
                    this.updateStats();
                } catch (error) {
                    Notify.show('Error al cargar datos', 'error');
                } finally {
                    this.loading = false;
                }
            },

            async createTask() {
                if (!this.newTask.titulo.trim()) {
                    Notify.show('El título es requerido', 'error');
                    return;
                }

                const taskManager = new TaskManager();
                const success = await taskManager.createTask(this.newTask);
                
                if (success) {
                    this.newTask = {
                        titulo: '',
                        descripcion: '',
                        categoria: '',
                        prioridad: 'media',
                        fecha_limite: ''
                    };
                    await this.loadData();
                }
            },

            async toggleTask(taskId) {
                const task = this.tasks.find(t => t.id === taskId);
                if (!task) return;

                const taskManager = new TaskManager();
                await taskManager.updateTask(taskId, {
                    completada: !task.completada
                });
                
                task.completada = !task.completada;
                this.updateStats();
            },

            async deleteTask(taskId) {
                const taskManager = new TaskManager();
                const success = await taskManager.deleteTask(taskId);
                
                if (success) {
                    await this.loadData();
                }
            },

            updateStats() {
                const taskManager = new TaskManager();
                taskManager.tasks = this.tasks;
                this.stats = taskManager.getStats();
            },

            clearFilters() {
                this.filter = {
                    status: 'all',
                    priority: '',
                    category: ''
                };
            },

            logout() {
                Auth.logout();
            }
        },

        mounted() {
            this.loadData();
            Auth.requireAuth();
        }
    };

    // Registrar componentes globales
    if (Vue.createApp) {
        const app = Vue.createApp(TaskApp);
        
        // Registrar componentes
        app.component('task-item', VueComponents.TaskComponent);
        app.component('stats-display', VueComponents.StatsComponent);
        
        app.mount('#app');
    }
}

/**********************************************
 * 9. APLICACIÓN DE ADMINISTRACIÓN
 **********************************************/
function createAdminApp() {
    if (!document.getElementById('adminApp')) return;

    const AdminApp = {
        data() {
            return {
                logged: false,
                password: '',
                users: [],
                tasks: [],
                stats: {},
                loading: false
            };
        },

        methods: {
            async login() {
                const adminSystem = new AdminSystem();
                this.logged = await adminSystem.login(this.password);
                if (this.logged) {
                    await this.loadAdminData();
                }
            },

            async logout() {
                const adminSystem = new AdminSystem();
                await adminSystem.logout();
            },

            async loadAdminData() {
                this.loading = true;
                try {
                    const adminSystem = new AdminSystem();
                    const [users, tasksRes, statsRes] = await Promise.all([
                        adminSystem.getUsers(),
                        fetch('/api/admin/all-tasks').then(r => r.json()),
                        adminSystem.getStats()
                    ]);

                    this.users = users;
                    this.tasks = tasksRes;
                    this.stats = statsRes || {};
                } catch (error) {
                    Notify.show('Error al cargar datos admin', 'error');
                } finally {
                    this.loading = false;
                }
            }
        }
    };

    if (Vue.createApp) {
        Vue.createApp(AdminApp).mount('#adminApp');
    }
}

/**********************************************
 * 10. INICIALIZACIÓN DE LA APLICACIÓN
 **********************************************/
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar autenticación
    Auth.requireAuth();
    
    // Crear aplicaciones según la página
    if (document.getElementById('app')) {
        createTaskApp();
    }
    
    if (document.getElementById('adminApp')) {
        createAdminApp();
    }
    
    // Manejar formulario de login
    const loginForm = document.querySelector('form[action^="/api/login"]');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.token) {
                    Auth.setAuth(result.token, result.user);
                    Notify.show('¡Bienvenido!', 'success');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                } else {
                    Notify.show(result.error || 'Error al iniciar sesión', 'error');
                }
            } catch (error) {
                Notify.show('Error de conexión', 'error');
            }
        });
    }
    
    // Manejar formulario de registro
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const nombre = document.getElementById('nombre').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            if (!Utils.validateEmail(email)) {
                Notify.show('Email inválido', 'error');
                return;
            }
            
            if (password.length < 6) {
                Notify.show('La contraseña debe tener al menos 6 caracteres', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre, email, password })
                });
                
                if (response.status === 201) {
                    Notify.show('¡Cuenta creada exitosamente!', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    const data = await response.json();
                    Notify.show(data.error || 'Error al registrar', 'error');
                }
            } catch (error) {
                Notify.show('Error de conexión', 'error');
            }
        });
    }
    
    // Añadir botón de logout global
    if (Auth.isAuthenticated()) {
        const logoutBtn = document.querySelector('[onclick="logout()"]');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => Auth.logout());
        }
    }
});

/**********************************************
 * 11. FUNCIONES GLOBALES
 **********************************************/
window.Auth = Auth;
window.Notify = Notify;
window.Loader = Loader;
window.TaskManager = TaskManager;
window.Utils = Utils;

// Función global de logout
window.logout = function() {
    Auth.logout();
};

// Función global para mostrar alertas rápidas
window.showAlert = function(message, type = 'info') {
    Notify.show(message, type);
};