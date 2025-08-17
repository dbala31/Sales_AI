// Sales AI Frontend JavaScript
class SalesAI {
    constructor() {
        this.baseURL = window.location.origin;
        this.token = localStorage.getItem('sales_ai_token');
        this.user = JSON.parse(localStorage.getItem('sales_ai_user') || 'null');
        this.init();
    }

    init() {
        // Setup event listeners first
        this.setupEventListeners();
        
        // Only check auth on dashboard pages, not on public pages
        const currentPath = window.location.pathname;
        const publicPages = ['/', '/login', '/register'];
        
        if (!publicPages.includes(currentPath)) {
            // Check authentication on protected pages
            this.checkAuth();
        }
        
        // Load initial data if authenticated and on appropriate page
        if (this.isAuthenticated() && currentPath === '/dashboard') {
            this.loadDashboardData();
        }
    }

    // Authentication Methods
    isAuthenticated() {
        return !!this.token && !!this.user;
    }

    async checkAuth() {
        if (!this.token) {
            return false;
        }

        try {
            const response = await this.apiCall('/api/auth/verify-token', 'GET');
            if (response.valid) {
                this.user = response.user;
                localStorage.setItem('sales_ai_user', JSON.stringify(this.user));
                this.updateUI();
                return true;
            } else {
                this.clearAuth();
                return false;
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.clearAuth();
            return false;
        }
    }

    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('sales_ai_token');
        localStorage.removeItem('sales_ai_user');
    }

    async login(email, password) {
        try {
            const response = await this.apiCall('/api/auth/login', 'POST', {
                email: email,
                password: password
            });

            this.token = response.access_token;
            this.user = response.user;
            
            localStorage.setItem('sales_ai_token', this.token);
            localStorage.setItem('sales_ai_user', JSON.stringify(this.user));
            
            this.showAlert('Login successful!', 'success');
            this.redirectToDashboard();
            
            return response;
        } catch (error) {
            this.showAlert(error.message || 'Login failed', 'danger');
            throw error;
        }
    }

    async register(userData) {
        try {
            const response = await this.apiCall('/api/auth/register', 'POST', userData);

            this.token = response.access_token;
            this.user = response.user;
            
            localStorage.setItem('sales_ai_token', this.token);
            localStorage.setItem('sales_ai_user', JSON.stringify(this.user));
            
            this.showAlert('Registration successful!', 'success');
            this.redirectToDashboard();
            
            return response;
        } catch (error) {
            this.showAlert(error.message || 'Registration failed', 'danger');
            throw error;
        }
    }

    logout() {
        this.clearAuth();
        this.redirectToLogin();
    }

    // Navigation Methods
    redirectToLogin() {
        if (window.location.pathname !== '/login' && window.location.pathname !== '/register' && window.location.pathname !== '/') {
            window.location.href = '/login';
        }
    }

    redirectToDashboard() {
        window.location.href = '/dashboard';
    }

    // API Methods
    async apiCall(endpoint, method = 'GET', data = null) {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = {
            method: method,
            headers: headers
        };

        if (data && method !== 'GET') {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(this.baseURL + endpoint, config);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }

    async uploadFile(file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(this.baseURL + '/api/upload/csv', {
                method: 'POST',
                headers: headers,
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('File upload failed:', error);
            throw error;
        }
    }

    // Dashboard Methods
    async loadDashboardData() {
        try {
            const stats = await this.apiCall('/api/verification/statistics');
            this.updateStats(stats);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    updateStats(stats) {
        const elements = {
            totalContacts: document.getElementById('totalContacts'),
            verifiedContacts: document.getElementById('verifiedContacts'),
            verificationRate: document.getElementById('verificationRate'),
            avgQuality: document.getElementById('avgQuality')
        };

        if (elements.totalContacts) {
            elements.totalContacts.textContent = stats.contacts.total.toLocaleString();
        }
        if (elements.verifiedContacts) {
            elements.verifiedContacts.textContent = stats.contacts.verified.toLocaleString();
        }
        if (elements.verificationRate) {
            elements.verificationRate.textContent = stats.contacts.verification_rate + '%';
        }
        if (elements.avgQuality) {
            elements.avgQuality.textContent = stats.quality_scores.average;
        }
    }

    // File Processing Methods
    async processCSVFile(file) {
        try {
            this.showAlert('Uploading and processing file...', 'info');
            this.showLoading(true);

            const result = await this.uploadFile(file);
            
            this.showAlert(
                `Upload successful! Processing ${result.total_contacts} contacts. Batch ID: ${result.batch_id}`,
                'success'
            );

            // Monitor progress
            this.monitorBatchProgress(result.batch_id);

            return result;
        } catch (error) {
            this.showAlert(error.message || 'File upload failed', 'danger');
            throw error;
        } finally {
            this.showLoading(false);
        }
    }

    async monitorBatchProgress(batchId) {
        const checkProgress = async () => {
            try {
                const batch = await this.apiCall(`/api/upload/batch/${batchId}/status`);
                
                if (batch.status === 'completed') {
                    this.showAlert(
                        `Processing completed! ${batch.verified_contacts} contacts verified out of ${batch.total_contacts}`,
                        'success'
                    );
                    this.loadDashboardData();
                    this.showExportButton(batchId);
                } else if (batch.status === 'failed') {
                    this.showAlert('Processing failed: ' + (batch.processing_errors || 'Unknown error'), 'danger');
                } else {
                    // Still processing, check again in 2 seconds
                    setTimeout(checkProgress, 2000);
                }
            } catch (error) {
                console.error('Failed to check batch progress:', error);
            }
        };

        checkProgress();
    }

    async exportVerifiedContacts(batchId) {
        try {
            const response = await fetch(this.baseURL + `/api/upload/batch/${batchId}/download`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `verified_contacts_batch_${batchId}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showAlert('Export completed successfully!', 'success');
        } catch (error) {
            this.showAlert(error.message || 'Export failed', 'danger');
        }
    }

    // UI Helper Methods
    updateUI() {
        // Update navbar with user info
        const userInfo = document.getElementById('userInfo');
        if (userInfo && this.user) {
            userInfo.innerHTML = `
                <span>Welcome, ${this.user.first_name || this.user.username}!</span>
                <button class="btn btn-sm btn-secondary" onclick="salesAI.logout()">Logout</button>
            `;
        }

        // Show/hide elements based on auth state
        const authElements = document.querySelectorAll('.auth-required');
        const noAuthElements = document.querySelectorAll('.no-auth-required');

        if (this.isAuthenticated()) {
            authElements.forEach(el => el.style.display = 'block');
            noAuthElements.forEach(el => el.style.display = 'none');
        } else {
            authElements.forEach(el => el.style.display = 'none');
            noAuthElements.forEach(el => el.style.display = 'block');
        }
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alertContainer') || this.createAlertContainer();
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()">×</button>
        `;

        alertContainer.appendChild(alert);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, 5000);
    }

    createAlertContainer() {
        const container = document.createElement('div');
        container.id = 'alertContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        document.body.appendChild(container);
        return container;
    }

    showLoading(show = true) {
        const loader = document.getElementById('globalLoader') || this.createLoader();
        loader.style.display = show ? 'flex' : 'none';
    }

    createLoader() {
        const loader = document.createElement('div');
        loader.id = 'globalLoader';
        loader.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(255, 255, 255, 0.8); display: none; 
            justify-content: center; align-items: center; z-index: 9998;
        `;
        loader.innerHTML = '<div class="loading"></div>';
        document.body.appendChild(loader);
        return loader;
    }

    showExportButton(batchId) {
        const exportContainer = document.getElementById('exportContainer');
        if (exportContainer) {
            exportContainer.innerHTML = `
                <button class="export-btn" onclick="salesAI.exportVerifiedContacts(${batchId})">
                    <i class="fas fa-download"></i> Download Verified Contacts CSV
                </button>
            `;
            exportContainer.style.display = 'block';
        }
    }

    // Event Listeners
    setupEventListeners() {
        // File upload handlers
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', this.handleFileSelect.bind(this));
        });

        // Drag and drop handlers
        const uploadAreas = document.querySelectorAll('.upload-area');
        uploadAreas.forEach(area => {
            area.addEventListener('dragover', this.handleDragOver.bind(this));
            area.addEventListener('drop', this.handleDrop.bind(this));
            area.addEventListener('dragleave', this.handleDragLeave.bind(this));
        });

        // Form handlers
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', this.handleLogin.bind(this));
        }

        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', this.handleRegister.bind(this));
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file && file.type === 'text/csv') {
            this.processCSVFile(file);
        } else {
            this.showAlert('Please select a valid CSV file', 'warning');
        }
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.currentTarget.classList.remove('dragover');
    }

    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'text/csv') {
                this.processCSVFile(file);
            } else {
                this.showAlert('Please drop a valid CSV file', 'warning');
            }
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        try {
            await this.login(
                formData.get('email'),
                formData.get('password')
            );
        } catch (error) {
            // Error already shown in login method
        }
    }

    async handleRegister(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        const password = formData.get('password');
        const confirmPassword = formData.get('confirmPassword');
        
        if (password !== confirmPassword) {
            this.showAlert('Passwords do not match', 'danger');
            return;
        }

        try {
            await this.register({
                email: formData.get('email'),
                username: formData.get('username'),
                password: password,
                first_name: formData.get('firstName'),
                last_name: formData.get('lastName')
            });
        } catch (error) {
            // Error already shown in register method
        }
    }
}

// Initialize Sales AI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.salesAI = new SalesAI();
});