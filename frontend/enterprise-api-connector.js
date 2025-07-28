/**
 * GPUDex Enterprise API Connector
 * Frontend-Backend Integration Layer with Web3
 * BILL GATES ON ADDERALL: MAXIMUM CONNECTIVITY!
 */

class GPUDexEnterpriseConnector {
    constructor(config) {
        this.config = {
            apiBaseUrl: config.apiBaseUrl || 'http://localhost:8000/api/v2',
            networkConfig: config.networkConfig || {
                chainId: 137, // Polygon mainnet
                rpcUrl: 'https://polygon-rpc.com',
                explorerUrl: 'https://polygonscan.com'
            },
            contractAddresses: config.contractAddresses || {
                enterprise: '0x...',
                token: '0x...',
                advancedTokenomics: '0x...'
            }
        };
        
        this.web3 = null;
        this.userAccount = null;
        this.contracts = {};
        this.isAuthenticated = false;
        
        // Event emitter for real-time updates
        this.eventEmitter = new EventTarget();
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing GPUDex Enterprise Connector...');
        await this.initWeb3();
        this.setupEventListeners();
    }
    
    // =============================================================================
    // WEB3 INTEGRATION
    // =============================================================================
    
    async initWeb3() {
        try {
            if (typeof window.ethereum !== 'undefined') {
                this.web3 = new Web3(window.ethereum);
                
                // Check if already connected
                const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                if (accounts.length > 0) {
                    this.userAccount = accounts[0];
                    await this.loadContracts();
                    this.isAuthenticated = true;
                    this.emit('walletConnected', { account: this.userAccount });
                }
                
                return true;
            } else {
                console.warn('MetaMask not detected');
                return false;
            }
        } catch (error) {
            console.error('Web3 initialization error:', error);
            return false;
        }
    }
    
    async connectWallet() {
        try {
            if (!this.web3) {
                throw new Error('Web3 not initialized');
            }
            
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            this.userAccount = accounts[0];
            
            // Check network
            const chainId = await window.ethereum.request({ method: 'eth_chainId' });
            if (parseInt(chainId, 16) !== this.config.networkConfig.chainId) {
                await this.switchNetwork();
            }
            
            await this.loadContracts();
            this.isAuthenticated = true;
            
            this.emit('walletConnected', { account: this.userAccount });
            this.showNotification('Wallet connected successfully!', 'success');
            
            return this.userAccount;
            
        } catch (error) {
            console.error('Wallet connection error:', error);
            this.showNotification('Failed to connect wallet: ' + error.message, 'error');
            throw error;
        }
    }
    
    async switchNetwork() {
        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: `0x${this.config.networkConfig.chainId.toString(16)}` }],
            });
        } catch (switchError) {
            // Network doesn't exist, add it
            if (switchError.code === 4902) {
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [{
                        chainId: `0x${this.config.networkConfig.chainId.toString(16)}`,
                        chainName: 'Polygon Mainnet',
                        nativeCurrency: { name: 'MATIC', symbol: 'MATIC', decimals: 18 },
                        rpcUrls: [this.config.networkConfig.rpcUrl],
                        blockExplorerUrls: [this.config.networkConfig.explorerUrl]
                    }]
                });
            }
        }
    }
    
    async loadContracts() {
        // Load contract ABIs (simplified for demo)
        const enterpriseABI = []; // Load from artifacts
        const tokenABI = [];      // Load from artifacts
        
        this.contracts.enterprise = new this.web3.eth.Contract(
            enterpriseABI,
            this.config.contractAddresses.enterprise
        );
        
        this.contracts.token = new this.web3.eth.Contract(
            tokenABI,
            this.config.contractAddresses.token
        );
    }
    
    // =============================================================================
    // API COMMUNICATION
    // =============================================================================
    
    async apiCall(endpoint, method = 'GET', data = null, requireAuth = true) {
        try {
            const url = `${this.config.apiBaseUrl}${endpoint}`;
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };
            
            // Add authentication if required
            if (requireAuth && this.isAuthenticated) {
                // In production, this would be a signed message or JWT token
                options.headers.Authorization = `Bearer ${this.userAccount}`;
            }
            
            if (data && (method === 'POST' || method === 'PUT')) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status} ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error(`API call error (${endpoint}):`, error);
            throw error;
        }
    }
    
    // =============================================================================
    // ENTERPRISE CLIENT MANAGEMENT
    // =============================================================================
    
    async registerEnterpriseClient(companyData) {
        try {
            this.showLoading(true, 'Registering enterprise client...');
            
            const registrationData = {
                company_name: companyData.companyName,
                contact_email: companyData.contactEmail,
                tier: parseInt(companyData.tier),
                contract_type: parseInt(companyData.contractType),
                wallet_address: this.userAccount
            };
            
            // Call API to register
            const result = await this.apiCall('/enterprise/register', 'POST', registrationData);
            
            // Monitor transaction
            if (result.transaction_hash) {
                await this.monitorTransaction(result.transaction_hash, 'Enterprise Registration');
            }
            
            this.emit('enterpriseRegistered', registrationData);
            this.showNotification('Enterprise registration submitted successfully!', 'success');
            
            return result;
            
        } catch (error) {
            console.error('Enterprise registration error:', error);
            this.showNotification('Registration failed: ' + error.message, 'error');
            throw error;
        } finally {
            this.showLoading(false);
        }
    }
    
    async getClientProfile(walletAddress = null) {
        try {
            const address = walletAddress || this.userAccount;
            const profile = await this.apiCall(`/enterprise/profile/${address}`);
            
            this.emit('profileLoaded', profile);
            return profile;
            
        } catch (error) {
            console.error('Get client profile error:', error);
            return null;
        }
    }
    
    async getTierInfo(walletAddress = null) {
        try {
            const address = walletAddress || this.userAccount;
            const tierInfo = await this.apiCall(`/enterprise/tier-info/${address}`);
            
            this.emit('tierInfoLoaded', tierInfo);
            return tierInfo;
            
        } catch (error) {
            console.error('Get tier info error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // PRICING AND QUOTES
    // =============================================================================
    
    async getPricingQuote(gpuType, hoursNeeded) {
        try {
            const quoteData = {
                gpu_type: gpuType,
                hours_needed: parseInt(hoursNeeded),
                client_address: this.userAccount
            };
            
            const quote = await this.apiCall('/pricing/quote', 'POST', quoteData);
            
            this.emit('quoteGenerated', quote);
            return quote;
            
        } catch (error) {
            console.error('Get pricing quote error:', error);
            throw error;
        }
    }
    
    async getPricingTiers() {
        try {
            const tiers = await this.apiCall('/pricing/tiers', 'GET', null, false);
            return tiers;
        } catch (error) {
            console.error('Get pricing tiers error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // ANALYTICS AND REPORTING
    // =============================================================================
    
    async getRevenueAnalytics() {
        try {
            const analytics = await this.apiCall('/analytics/revenue');
            
            this.emit('analyticsLoaded', analytics);
            return analytics;
            
        } catch (error) {
            console.error('Get revenue analytics error:', error);
            return null;
        }
    }
    
    async getClientAnalytics(walletAddress = null) {
        try {
            const address = walletAddress || this.userAccount;
            const analytics = await this.apiCall(`/analytics/client/${address}`);
            
            this.emit('clientAnalyticsLoaded', analytics);
            return analytics;
            
        } catch (error) {
            console.error('Get client analytics error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // INSTITUTIONAL STAKING
    // =============================================================================
    
    async applyInstitutionalStaking(stakingData) {
        try {
            this.showLoading(true, 'Applying for institutional staking...');
            
            const applicationData = {
                institution_name: stakingData.institutionName,
                stake_amount: parseFloat(stakingData.stakeAmount),
                custom_apy: parseFloat(stakingData.customAPY) / 100,
                lock_period_days: parseInt(stakingData.lockPeriodDays),
                wallet_address: this.userAccount
            };
            
            const result = await this.apiCall('/institutional/apply', 'POST', applicationData);
            
            if (result.transaction_hash) {
                await this.monitorTransaction(result.transaction_hash, 'Institutional Staking Application');
            }
            
            this.emit('institutionalApplicationSubmitted', applicationData);
            this.showNotification('Institutional staking application submitted!', 'success');
            
            return result;
            
        } catch (error) {
            console.error('Institutional staking application error:', error);
            this.showNotification('Application failed: ' + error.message, 'error');
            throw error;
        } finally {
            this.showLoading(false);
        }
    }
    
    async getInstitutionalPrograms() {
        try {
            const programs = await this.apiCall('/institutional/programs', 'GET', null, false);
            return programs;
        } catch (error) {
            console.error('Get institutional programs error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // ADVANCED TOKENOMICS
    // =============================================================================
    
    async getCurrentAPY() {
        try {
            const apyData = await this.apiCall('/tokenomics/apy', 'GET', null, false);
            
            this.emit('apyUpdated', apyData);
            return apyData;
            
        } catch (error) {
            console.error('Get current APY error:', error);
            return null;
        }
    }
    
    async getBurnStatistics() {
        try {
            const burnStats = await this.apiCall('/tokenomics/burn-stats', 'GET', null, false);
            
            this.emit('burnStatsLoaded', burnStats);
            return burnStats;
            
        } catch (error) {
            console.error('Get burn statistics error:', error);
            return null;
        }
    }
    
    async getCrossChainInfo() {
        try {
            const crossChainInfo = await this.apiCall('/tokenomics/cross-chain', 'GET', null, false);
            return crossChainInfo;
        } catch (error) {
            console.error('Get cross-chain info error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // TRANSACTION MONITORING
    // =============================================================================
    
    async monitorTransaction(txHash, description) {
        try {
            console.log(`Monitoring transaction: ${txHash}`);
            
            const checkStatus = async () => {
                try {
                    const status = await this.apiCall(`/transactions/${txHash}`);
                    
                    this.emit('transactionUpdate', { 
                        hash: txHash, 
                        status: status.status, 
                        description 
                    });
                    
                    if (status.status === 'confirmed') {
                        this.showNotification(`${description} confirmed!`, 'success');
                        return true;
                    } else if (status.status === 'failed') {
                        this.showNotification(`${description} failed!`, 'error');
                        return true;
                    }
                    
                    return false;
                } catch (error) {
                    console.error('Transaction status check error:', error);
                    return false;
                }
            };
            
            // Poll transaction status
            const maxAttempts = 60; // 5 minutes max
            let attempts = 0;
            
            while (attempts < maxAttempts) {
                const isComplete = await checkStatus();
                if (isComplete) break;
                
                await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
                attempts++;
            }
            
        } catch (error) {
            console.error('Transaction monitoring error:', error);
        }
    }
    
    async getTransactionHistory(limit = 10) {
        try {
            const history = await this.apiCall(`/transactions/history/${this.userAccount}?limit=${limit}`);
            
            this.emit('transactionHistoryLoaded', history);
            return history;
            
        } catch (error) {
            console.error('Get transaction history error:', error);
            return null;
        }
    }
    
    // =============================================================================
    // REAL-TIME UPDATES
    // =============================================================================
    
    setupEventListeners() {
        // Listen for account changes
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length === 0) {
                    this.disconnect();
                } else if (accounts[0] !== this.userAccount) {
                    this.userAccount = accounts[0];
                    this.emit('accountChanged', { account: this.userAccount });
                    this.loadContracts();
                }
            });
            
            window.ethereum.on('chainChanged', (chainId) => {
                if (parseInt(chainId, 16) !== this.config.networkConfig.chainId) {
                    this.showNotification('Please switch to Polygon network', 'warning');
                }
                this.emit('networkChanged', { chainId: parseInt(chainId, 16) });
            });
        }
    }
    
    disconnect() {
        this.userAccount = null;
        this.isAuthenticated = false;
        this.contracts = {};
        
        this.emit('walletDisconnected');
        this.showNotification('Wallet disconnected', 'info');
    }
    
    // =============================================================================
    // UTILITY METHODS
    // =============================================================================
    
    emit(eventType, data) {
        const event = new CustomEvent(eventType, { detail: data });
        this.eventEmitter.dispatchEvent(event);
    }
    
    on(eventType, callback) {
        this.eventEmitter.addEventListener(eventType, callback);
    }
    
    off(eventType, callback) {
        this.eventEmitter.removeEventListener(eventType, callback);
    }
    
    showLoading(show, message = 'Processing...') {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.toggle('hidden', !show);
            const messageEl = overlay.querySelector('p');
            if (messageEl) {
                messageEl.textContent = message;
            }
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg text-white z-50 transition-all duration-300 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${
                    type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-circle' : 
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle'
                } mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    formatAddress(address) {
        if (!address) return '';
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }
    
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }
    
    formatDate(timestamp) {
        return new Date(timestamp * 1000).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // =============================================================================
    // DASHBOARD HELPERS
    // =============================================================================
    
    async loadDashboard() {
        try {
            console.log('🚀 Loading enterprise dashboard...');
            
            // Load all dashboard data in parallel
            const [profile, tierInfo, analytics, apyData] = await Promise.all([
                this.getClientProfile(),
                this.getTierInfo(),
                this.getClientAnalytics(),
                this.getCurrentAPY()
            ]);
            
            // Update UI elements
            this.updateDashboardUI(profile, tierInfo, analytics, apyData);
            
            this.emit('dashboardLoaded', {
                profile, tierInfo, analytics, apyData
            });
            
        } catch (error) {
            console.error('Dashboard loading error:', error);
        }
    }
    
    updateDashboardUI(profile, tierInfo, analytics, apyData) {
        // Update profile info
        if (profile) {
            this.updateElement('total-spent', this.formatCurrency(profile.total_spent));
            this.updateElement('gpu-hours', profile.gpu_hours.toLocaleString());
            this.updateElement('discount-rate', `${profile.discount_rate}%`);
            
            // Update tier badge
            const tierBadge = document.getElementById('current-tier');
            if (tierBadge) {
                tierBadge.innerHTML = `<span class="tier-badge tier-${profile.tier.toLowerCase()}">${profile.tier}</span>`;
            }
        }
        
        // Update tier progress
        if (tierInfo) {
            const progressBar = document.getElementById('tier-progress-bar');
            if (progressBar) {
                progressBar.style.width = `${tierInfo.tier_progress}%`;
            }
            
            this.updateElement('tier-progress-text', 
                `${this.formatCurrency(tierInfo.current_spending)} / ${this.formatCurrency(tierInfo.next_tier_requirement)}`
            );
            
            this.updateElement('tier-upgrade-message',
                `Spend ${this.formatCurrency(tierInfo.amount_to_next_tier)} more to reach ${tierInfo.next_tier} tier!`
            );
        }
        
        // Update APY display
        if (apyData) {
            this.updateElement('current-apy', `${(apyData.current_apy * 100).toFixed(1)}%`);
        }
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
}

// Global instance
let gpudexConnector = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing GPUDex Enterprise Portal...');
    
    // Configuration
    const config = {
        apiBaseUrl: 'http://localhost:8000/api/v2',
        networkConfig: {
            chainId: 137, // Polygon mainnet
            rpcUrl: 'https://polygon-rpc.com',
            explorerUrl: 'https://polygonscan.com'
        },
        contractAddresses: {
            enterprise: '0x...', // Will be set from deployment
            token: '0x...',      // Will be set from deployment
            advancedTokenomics: '0x...' // Will be set from deployment
        }
    };
    
    // Initialize connector
    gpudexConnector = new GPUDexEnterpriseConnector(config);
    
    // Set up global event handlers
    setupGlobalEventHandlers();
});

function setupGlobalEventHandlers() {
    // Connect wallet button
    const connectBtn = document.getElementById('connect-wallet');
    if (connectBtn) {
        connectBtn.addEventListener('click', async () => {
            try {
                await gpudexConnector.connectWallet();
            } catch (error) {
                console.error('Wallet connection failed:', error);
            }
        });
    }
    
    // Enterprise registration form
    const regForm = document.getElementById('enterprise-registration-form');
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(regForm);
            const registrationData = {
                companyName: formData.get('company-name'),
                contactEmail: formData.get('contact-email'),
                tier: formData.get('enterprise-tier'),
                contractType: formData.get('contract-type')
            };
            
            try {
                await gpudexConnector.registerEnterpriseClient(registrationData);
            } catch (error) {
                console.error('Registration failed:', error);
            }
        });
    }
    
    // Pricing calculator
    const gpuTypeSelect = document.getElementById('gpu-type');
    const hoursInput = document.getElementById('hours-needed');
    
    if (gpuTypeSelect && hoursInput) {
        const updatePricing = async () => {
            if (gpudexConnector && gpudexConnector.isAuthenticated) {
                try {
                    const quote = await gpudexConnector.getPricingQuote(
                        gpuTypeSelect.value,
                        hoursInput.value
                    );
                    
                    document.getElementById('base-cost').textContent = 
                        gpudexConnector.formatCurrency(quote.base_cost);
                    document.getElementById('discounted-cost').textContent = 
                        gpudexConnector.formatCurrency(quote.final_cost);
                        
                } catch (error) {
                    console.error('Pricing calculation error:', error);
                }
            }
        };
        
        gpuTypeSelect.addEventListener('change', updatePricing);
        hoursInput.addEventListener('input', updatePricing);
    }
    
    // Listen for connector events
    if (gpudexConnector) {
        gpudexConnector.on('walletConnected', (event) => {
            const { account } = event.detail;
            
            // Update UI
            document.getElementById('wallet-status').textContent = 
                gpudexConnector.formatAddress(account);
            document.getElementById('connect-wallet').textContent = 'Connected';
            
            // Load dashboard
            gpudexConnector.loadDashboard();
        });
        
        gpudexConnector.on('enterpriseRegistered', (event) => {
            // Hide registration form, show dashboard
            document.getElementById('registration-section').classList.add('hidden');
            document.getElementById('dashboard-section').classList.remove('hidden');
        });
        
        gpudexConnector.on('dashboardLoaded', (event) => {
            console.log('✅ Dashboard loaded successfully');
        });
    }
}

// Export for global access
window.GPUDexEnterpriseConnector = GPUDexEnterpriseConnector;
window.gpudexConnector = gpudexConnector; 