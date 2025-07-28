/**
 * GPUDx Wallet Connector - Web3 Integration
 * Supports MetaMask, WalletConnect, Coinbase Wallet, and more
 */

class WalletConnector {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.chainId = null;
        this.isConnected = false;
        this.supportedChains = {
            1: { name: 'Ethereum', rpc: 'https://mainnet.infura.io/v3/' },
            137: { name: 'Polygon', rpc: 'https://polygon-rpc.com' },
            31337: { name: 'Localhost', rpc: 'http://localhost:8545' }
        };
        this.targetChainId = 137; // Polygon by default
        
        this.init();
    }

    async init() {
        // Check if already connected
        if (this.hasWalletConnection()) {
            await this.autoConnect();
        }
        
        // Listen for account changes
        this.setupEventListeners();
        
        // Update UI
        this.updateWalletUI();
    }

    hasWalletConnection() {
        return localStorage.getItem('walletConnected') === 'true';
    }

    setupEventListeners() {
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length === 0) {
                    this.disconnect();
                } else {
                    this.account = accounts[0];
                    this.updateWalletUI();
                }
            });

            window.ethereum.on('chainChanged', (chainId) => {
                this.chainId = parseInt(chainId, 16);
                this.updateWalletUI();
                if (this.chainId !== this.targetChainId) {
                    this.promptChainSwitch();
                }
            });
        }
    }

    async connectWallet(walletType = 'metamask') {
        try {
            switch (walletType) {
                case 'metamask':
                    return await this.connectMetaMask();
                case 'walletconnect':
                    return await this.connectWalletConnect();
                case 'coinbase':
                    return await this.connectCoinbaseWallet();
                default:
                    return await this.connectMetaMask();
            }
        } catch (error) {
            console.error('Wallet connection error:', error);
            this.showNotification('Failed to connect wallet: ' + error.message, 'error');
            return false;
        }
    }

    async connectMetaMask() {
        if (!window.ethereum) {
            this.showInstallMetaMaskModal();
            return false;
        }

        try {
            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            this.account = accounts[0];
            this.web3 = new Web3(window.ethereum);
            
            // Get chain ID
            this.chainId = await window.ethereum.request({
                method: 'eth_chainId'
            });
            this.chainId = parseInt(this.chainId, 16);

            // Switch to target chain if needed
            if (this.chainId !== this.targetChainId) {
                await this.switchChain(this.targetChainId);
            }

            this.isConnected = true;
            localStorage.setItem('walletConnected', 'true');
            localStorage.setItem('walletType', 'metamask');
            
            this.updateWalletUI();
            this.showNotification('Wallet connected successfully!', 'success');
            
            return true;
        } catch (error) {
            throw new Error(`MetaMask connection failed: ${error.message}`);
        }
    }

    async connectWalletConnect() {
        // WalletConnect integration would go here
        this.showNotification('WalletConnect integration coming soon!', 'info');
        return false;
    }

    async connectCoinbaseWallet() {
        // Coinbase Wallet integration would go here
        this.showNotification('Coinbase Wallet integration coming soon!', 'info');
        return false;
    }

    async autoConnect() {
        const walletType = localStorage.getItem('walletType') || 'metamask';
        return await this.connectWallet(walletType);
    }

    async switchChain(chainId) {
        const chainConfig = this.supportedChains[chainId];
        if (!chainConfig) {
            throw new Error('Unsupported chain');
        }

        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: '0x' + chainId.toString(16) }]
            });
        } catch (switchError) {
            // Chain not added to wallet
            if (switchError.code === 4902) {
                await this.addChain(chainId);
            } else {
                throw switchError;
            }
        }
    }

    async addChain(chainId) {
        const chainConfig = this.supportedChains[chainId];
        
        const params = {
            chainId: '0x' + chainId.toString(16),
            chainName: chainConfig.name,
            rpcUrls: [chainConfig.rpc],
            nativeCurrency: {
                name: chainId === 137 ? 'MATIC' : 'ETH',
                symbol: chainId === 137 ? 'MATIC' : 'ETH',
                decimals: 18
            }
        };

        if (chainId === 137) {
            params.blockExplorerUrls = ['https://polygonscan.com'];
        }

        await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [params]
        });
    }

    disconnect() {
        this.web3 = null;
        this.account = null;
        this.chainId = null;
        this.isConnected = false;
        
        localStorage.removeItem('walletConnected');
        localStorage.removeItem('walletType');
        
        this.updateWalletUI();
        this.showNotification('Wallet disconnected', 'info');
    }

    updateWalletUI() {
        const connectButton = document.getElementById('connect-wallet');
        const walletStatus = document.getElementById('wallet-status');
        const walletIndicator = document.getElementById('wallet-indicator');

        if (this.isConnected && this.account) {
            // Update connect button
            if (connectButton) {
                connectButton.textContent = `${this.account.slice(0, 6)}...${this.account.slice(-4)}`;
                connectButton.classList.remove('animate-pulse-glow');
                connectButton.onclick = () => this.showWalletMenu();
            }

            // Update status
            if (walletStatus) {
                walletStatus.textContent = 'Connected';
            }

            // Update indicator
            if (walletIndicator) {
                walletIndicator.className = 'w-2 h-2 bg-green-500 rounded-full';
            }

            // Check chain
            if (this.chainId !== this.targetChainId) {
                this.showChainWarning();
            }
        } else {
            // Update connect button
            if (connectButton) {
                connectButton.textContent = 'Connect Wallet';
                connectButton.classList.add('animate-pulse-glow');
                connectButton.onclick = () => this.showConnectModal();
            }

            // Update status
            if (walletStatus) {
                walletStatus.textContent = 'Not Connected';
            }

            // Update indicator
            if (walletIndicator) {
                walletIndicator.className = 'w-2 h-2 bg-red-500 rounded-full';
            }
        }
    }

    showConnectModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4">
                <h3 class="text-2xl font-bold mb-6 text-center">Connect Wallet</h3>
                <div class="space-y-4">
                    <button onclick="walletConnector.connectWallet('metamask'); this.closest('.fixed').remove()" 
                            class="w-full flex items-center justify-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                        <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjEyIiBoZWlnaHQ9IjE4OSIgdmlld0JveD0iMCAwIDIxMiAxODkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PC9zdmc+" 
                             alt="MetaMask" class="w-8 h-8 mr-3">
                        <span class="font-medium">MetaMask</span>
                    </button>
                    <button onclick="walletConnector.connectWallet('walletconnect'); this.closest('.fixed').remove()" 
                            class="w-full flex items-center justify-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 mr-3 bg-blue-500 rounded-full flex items-center justify-center">
                            <span class="text-white font-bold text-sm">WC</span>
                        </div>
                        <span class="font-medium">WalletConnect</span>
                    </button>
                    <button onclick="walletConnector.connectWallet('coinbase'); this.closest('.fixed').remove()" 
                            class="w-full flex items-center justify-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 mr-3 bg-blue-600 rounded-full flex items-center justify-center">
                            <span class="text-white font-bold text-sm">CB</span>
                        </div>
                        <span class="font-medium">Coinbase Wallet</span>
                    </button>
                </div>
                <button onclick="this.closest('.fixed').remove()" 
                        class="w-full mt-6 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    Cancel
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    showWalletMenu() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4">
                <h3 class="text-2xl font-bold mb-6 text-center">Wallet Menu</h3>
                <div class="space-y-4">
                    <div class="text-center">
                        <p class="text-sm text-gray-500 mb-2">Connected Account</p>
                        <p class="font-mono text-lg">${this.account}</p>
                        <p class="text-sm text-gray-500 mt-2">
                            Chain: ${this.supportedChains[this.chainId]?.name || 'Unknown'}
                        </p>
                    </div>
                    <div class="border-t pt-4">
                        <button onclick="navigator.clipboard.writeText('${this.account}'); this.textContent='Copied!'" 
                                class="w-full mb-3 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                            Copy Address
                        </button>
                        <button onclick="walletConnector.disconnect(); this.closest('.fixed').remove()" 
                                class="w-full px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
                            Disconnect
                        </button>
                    </div>
                </div>
                <button onclick="this.closest('.fixed').remove()" 
                        class="w-full mt-6 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    showInstallMetaMaskModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4 text-center">
                <h3 class="text-2xl font-bold mb-4">MetaMask Required</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-6">
                    Please install MetaMask to connect your wallet and interact with GPUDx.
                </p>
                <div class="space-y-4">
                    <a href="https://metamask.io/download/" target="_blank" 
                       class="block w-full enhanced-button text-center">
                        Install MetaMask
                    </a>
                    <button onclick="this.closest('.fixed').remove()" 
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    promptChainSwitch() {
        this.showNotification(`Please switch to ${this.supportedChains[this.targetChainId].name} network`, 'warning');
    }

    showChainWarning() {
        const warning = document.createElement('div');
        warning.className = 'fixed top-20 right-4 bg-yellow-500 text-white px-4 py-2 rounded-lg z-40';
        warning.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                <span>Wrong network. Switch to ${this.supportedChains[this.targetChainId].name}</span>
                <button onclick="walletConnector.switchChain(${this.targetChainId}); this.closest('div').remove()" 
                        class="ml-3 bg-white text-yellow-500 px-2 py-1 rounded text-sm">
                    Switch
                </button>
            </div>
        `;
        
        document.body.appendChild(warning);
        
        setTimeout(() => {
            if (warning.parentNode) {
                warning.remove();
            }
        }, 10000);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Utility methods for contract interactions
    async getBalance() {
        if (!this.web3 || !this.account) return 0;
        const balance = await this.web3.eth.getBalance(this.account);
        return this.web3.utils.fromWei(balance, 'ether');
    }

    async signMessage(message) {
        if (!this.web3 || !this.account) return null;
        return await this.web3.eth.personal.sign(message, this.account);
    }
}

// Initialize wallet connector
const walletConnector = new WalletConnector(); 