// ===============================================================================
// 🔥 BILL GATES ON ADDERALL: REAL WEB3 SMART CONTRACT INTEGRATION! 🔥
// ===============================================================================

class GPUDexWeb3Connector {
    constructor() {
        this.web3 = null;
        this.userAccount = null;
        this.contracts = {};
        this.chainId = null;
        this.isConnected = false;
        
        // Contract addresses from deployment
        this.contractAddresses = {
            GPUDX_TOKEN_V2: '0x5FbDB2315678afecb367f032d93F642f64180aa3',
            GPUDX_STAKING: '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
            GPUDX_ESCROW_V2: '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0',
            GPUDX_TOKENOMICS_V2: '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9'
        };
        
        // Contract ABIs (simplified - in production, load from artifacts)
        this.contractABIs = {
            GPUDX_TOKEN_V2: [
                {
                    "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ],
            GPUDX_STAKING: [
                {
                    "inputs": [{"name": "amount", "type": "uint256"}, {"name": "lockPeriod", "type": "uint256"}],
                    "name": "stake",
                    "outputs": [],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "stakingId", "type": "uint256"}],
                    "name": "claimRewards",
                    "outputs": [],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "stakingId", "type": "uint256"}],
                    "name": "unstake",
                    "outputs": [],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "user", "type": "address"}],
                    "name": "getStakingPositions",
                    "outputs": [{"name": "", "type": "tuple[]"}],
                    "type": "function"
                }
            ],
            GPUDX_ESCROW_V2: [
                {
                    "inputs": [
                        {"name": "provider", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                        {"name": "duration", "type": "uint256"},
                        {"name": "metadata", "type": "string"}
                    ],
                    "name": "createRental",
                    "outputs": [{"name": "rentalId", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "rentalId", "type": "uint256"}],
                    "name": "completeRental",
                    "outputs": [],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "user", "type": "address"}],
                    "name": "getUserRentals",
                    "outputs": [{"name": "", "type": "tuple[]"}],
                    "type": "function"
                }
            ]
        };
        
        this.initialize();
    }

    async initialize() {
        console.log('🚀 Initializing GPUDex Web3 Connector...');
        
        if (typeof window.ethereum !== 'undefined') {
            this.web3 = new Web3(window.ethereum);
            
            // Check if already connected
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                await this.handleAccountsChanged(accounts);
            }
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Initialize contracts
            await this.initializeContracts();
            
            console.log('✅ Web3 connector initialized successfully');
        } else {
            console.warn('⚠️ MetaMask not detected');
            this.showInstallMetaMaskModal();
        }
    }

    setupEventListeners() {
        window.ethereum.on('accountsChanged', this.handleAccountsChanged.bind(this));
        window.ethereum.on('chainChanged', this.handleChainChanged.bind(this));
        window.ethereum.on('disconnect', this.handleDisconnect.bind(this));
    }

    async initializeContracts() {
        try {
            for (const [name, address] of Object.entries(this.contractAddresses)) {
                if (this.contractABIs[name]) {
                    this.contracts[name] = new this.web3.eth.Contract(
                        this.contractABIs[name],
                        address
                    );
                    console.log(`✅ Contract ${name} initialized at ${address}`);
                }
            }
        } catch (error) {
            console.error('❌ Failed to initialize contracts:', error);
        }
    }

    // MAIN CONNECTION FUNCTION
    async connectWallet() {
        try {
            console.log('🔗 Connecting wallet...');
            
            if (!this.web3) {
                throw new Error('Web3 not available. Please install MetaMask.');
            }

            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            await this.handleAccountsChanged(accounts);
            
            // Verify we're on the correct network
            await this.checkNetwork();
            
            this.showNotification('✅ Wallet connected successfully!', 'success');
            console.log(`✅ Connected to wallet: ${this.userAccount}`);
            
            return {
                success: true,
                account: this.userAccount,
                chainId: this.chainId
            };

        } catch (error) {
            console.error('❌ Wallet connection failed:', error);
            this.showNotification(`❌ Connection failed: ${error.message}`, 'error');
            return { success: false, error: error.message };
        }
    }

    async handleAccountsChanged(accounts) {
        if (accounts.length === 0) {
            // User disconnected
            this.userAccount = null;
            this.isConnected = false;
            console.log('👋 Wallet disconnected');
        } else {
            this.userAccount = accounts[0];
            this.isConnected = true;
            
            // Update UI
            this.updateWalletDisplay();
            
            // Load user data
            await this.loadUserData();
        }
        
        // Notify other components
        window.dispatchEvent(new CustomEvent('walletChanged', {
            detail: { account: this.userAccount, connected: this.isConnected }
        }));
    }

    async handleChainChanged(chainId) {
        this.chainId = chainId;
        console.log(`🔄 Chain changed to: ${chainId}`);
        
        // Reload contracts for new chain
        await this.initializeContracts();
        
        // Check if we're on the correct network
        await this.checkNetwork();
    }

    handleDisconnect() {
        this.userAccount = null;
        this.isConnected = false;
        console.log('🔌 Wallet disconnected');
        this.updateWalletDisplay();
    }

    async checkNetwork() {
        const chainId = await this.web3.eth.getChainId();
        this.chainId = chainId;
        
        // Check if we're on Polygon (137) or localhost (31337) for development
        const supportedChains = [137, 31337, 80001]; // Polygon, Localhost, Mumbai
        
        if (!supportedChains.includes(chainId)) {
            this.showNetworkSwitchModal();
            return false;
        }
        
        return true;
    }

    // ===============================================================================
    // 🔥 SMART CONTRACT INTERACTION FUNCTIONS - THE REAL DEAL! 🔥
    // ===============================================================================

    // REAL STAKING FUNCTION WITH SMART CONTRACT
    async stakeTokens(amount, lockPeriodDays = 0) {
        try {
            if (!this.isConnected) {
                throw new Error('Please connect your wallet first');
            }

            console.log(`🥩 Staking ${amount} GPUDX tokens for ${lockPeriodDays} days...`);
            
            const amountWei = this.web3.utils.toWei(amount.toString(), 'ether');
            const lockPeriodSeconds = lockPeriodDays * 24 * 60 * 60;

            // Step 1: Approve token spending
            await this.approveTokenSpending(amountWei, this.contractAddresses.GPUDX_STAKING);

            // Step 2: Call staking contract
            const stakingContract = this.contracts.GPUDX_STAKING;
            
            const txHash = await stakingContract.methods
                .stake(amountWei, lockPeriodSeconds)
                .send({
                    from: this.userAccount,
                    gas: 500000
                });

            console.log(`✅ Staking transaction sent: ${txHash.transactionHash}`);
            
            return {
                success: true,
                transactionHash: txHash.transactionHash,
                amount: amount,
                lockPeriod: lockPeriodDays
            };

        } catch (error) {
            console.error('❌ Staking failed:', error);
            throw new Error(`Staking failed: ${error.message}`);
        }
    }

    // REAL GPU RENTAL WITH SMART CONTRACT ESCROW
    async createGPURental(providerAddress, rentalAmount, durationHours, metadata) {
        try {
            if (!this.isConnected) {
                throw new Error('Please connect your wallet first');
            }

            console.log(`🖥️ Creating GPU rental with ${providerAddress} for ${durationHours} hours...`);
            
            const amountWei = this.web3.utils.toWei(rentalAmount.toString(), 'ether');
            const durationSeconds = durationHours * 60 * 60;

            // Step 1: Approve token spending for escrow
            await this.approveTokenSpending(amountWei, this.contractAddresses.GPUDX_ESCROW_V2);

            // Step 2: Create rental in escrow contract
            const escrowContract = this.contracts.GPUDX_ESCROW_V2;
            
            const txHash = await escrowContract.methods
                .createRental(providerAddress, amountWei, durationSeconds, metadata)
                .send({
                    from: this.userAccount,
                    gas: 800000
                });

            console.log(`✅ Rental transaction sent: ${txHash.transactionHash}`);
            
            return {
                success: true,
                transactionHash: txHash.transactionHash,
                rentalId: txHash.events.RentalCreated?.returnValues?.rentalId,
                amount: rentalAmount,
                duration: durationHours
            };

        } catch (error) {
            console.error('❌ Rental creation failed:', error);
            throw new Error(`Rental creation failed: ${error.message}`);
        }
    }

    // APPROVE TOKEN SPENDING
    async approveTokenSpending(amount, spenderAddress) {
        try {
            console.log(`🔓 Approving ${amount} token spending for ${spenderAddress}...`);
            
            const tokenContract = this.contracts.GPUDX_TOKEN_V2;
            
            const txHash = await tokenContract.methods
                .approve(spenderAddress, amount)
                .send({
                    from: this.userAccount,
                    gas: 100000
                });

            console.log(`✅ Approval transaction sent: ${txHash.transactionHash}`);
            return txHash.transactionHash;

        } catch (error) {
            console.error('❌ Token approval failed:', error);
            throw new Error(`Token approval failed: ${error.message}`);
        }
    }

    // GET USER TOKEN BALANCE
    async getUserBalance() {
        try {
            if (!this.isConnected) return '0';
            
            const tokenContract = this.contracts.GPUDX_TOKEN_V2;
            const balanceWei = await tokenContract.methods.balanceOf(this.userAccount).call();
            const balance = this.web3.utils.fromWei(balanceWei, 'ether');
            
            return parseFloat(balance).toFixed(4);

        } catch (error) {
            console.error('❌ Failed to get user balance:', error);
            return '0';
        }
    }

    // GET USER STAKING POSITIONS
    async getUserStakingPositions() {
        try {
            if (!this.isConnected) return [];
            
            const stakingContract = this.contracts.GPUDX_STAKING;
            const positions = await stakingContract.methods.getStakingPositions(this.userAccount).call();
            
            return positions.map(position => ({
                id: position.id,
                amount: this.web3.utils.fromWei(position.amount, 'ether'),
                lockPeriod: position.lockPeriod,
                startTime: new Date(position.startTime * 1000),
                unlockTime: new Date((position.startTime + position.lockPeriod) * 1000),
                rewards: this.web3.utils.fromWei(position.pendingRewards, 'ether'),
                tier: this.calculateStakingTier(position.amount),
                apy: this.calculateAPY(position.lockPeriod)
            }));

        } catch (error) {
            console.error('❌ Failed to get staking positions:', error);
            return [];
        }
    }

    // GET USER RENTALS
    async getUserRentals() {
        try {
            if (!this.isConnected) return [];
            
            const escrowContract = this.contracts.GPUDX_ESCROW_V2;
            const rentals = await escrowContract.methods.getUserRentals(this.userAccount).call();
            
            return rentals.map(rental => ({
                id: rental.id,
                provider: rental.provider,
                amount: this.web3.utils.fromWei(rental.amount, 'ether'),
                duration: rental.duration / 3600, // Convert to hours
                startTime: new Date(rental.startTime * 1000),
                endTime: new Date((rental.startTime + rental.duration) * 1000),
                status: rental.status,
                metadata: JSON.parse(rental.metadata || '{}')
            }));

        } catch (error) {
            console.error('❌ Failed to get user rentals:', error);
            return [];
        }
    }

    // CLAIM STAKING REWARDS
    async claimStakingRewards(stakingId) {
        try {
            if (!this.isConnected) {
                throw new Error('Please connect your wallet first');
            }

            console.log(`💰 Claiming rewards for staking position ${stakingId}...`);
            
            const stakingContract = this.contracts.GPUDX_STAKING;
            
            const txHash = await stakingContract.methods
                .claimRewards(stakingId)
                .send({
                    from: this.userAccount,
                    gas: 300000
                });

            console.log(`✅ Claim rewards transaction sent: ${txHash.transactionHash}`);
            
            return {
                success: true,
                transactionHash: txHash.transactionHash
            };

        } catch (error) {
            console.error('❌ Claim rewards failed:', error);
            throw new Error(`Claim rewards failed: ${error.message}`);
        }
    }

    // ===============================================================================
    // 🔥 UTILITY FUNCTIONS 🔥
    // ===============================================================================

    calculateStakingTier(amountWei) {
        const amount = parseFloat(this.web3.utils.fromWei(amountWei, 'ether'));
        
        if (amount >= 100000) return 'Diamond';
        if (amount >= 50000) return 'Platinum';
        if (amount >= 10000) return 'Gold';
        if (amount >= 1000) return 'Silver';
        return 'Bronze';
    }

    calculateAPY(lockPeriodSeconds) {
        const lockPeriodDays = lockPeriodSeconds / (24 * 60 * 60);
        
        if (lockPeriodDays >= 365) return 15; // 15% APY for 1 year+
        if (lockPeriodDays >= 180) return 12; // 12% APY for 6 months+
        if (lockPeriodDays >= 90) return 8;   // 8% APY for 3 months+
        if (lockPeriodDays >= 30) return 5;   // 5% APY for 1 month+
        return 2; // 2% APY for no lock
    }

    async loadUserData() {
        if (!this.isConnected) return;
        
        try {
            // Load balance
            const balance = await this.getUserBalance();
            
            // Update balance display
            const balanceElements = document.querySelectorAll('.user-balance');
            balanceElements.forEach(el => {
                el.textContent = `${balance} GPUDX`;
            });
            
            // Load staking positions
            const stakingPositions = await this.getUserStakingPositions();
            
            // Load rentals
            const rentals = await this.getUserRentals();
            
            console.log(`✅ Loaded user data: ${balance} GPUDX, ${stakingPositions.length} stakes, ${rentals.length} rentals`);
            
        } catch (error) {
            console.warn('⚠️ Failed to load user data:', error);
        }
    }

    updateWalletDisplay() {
        const connectButton = document.getElementById('connect-wallet');
        const walletStatus = document.getElementById('wallet-status');
        const userBalanceElements = document.querySelectorAll('.user-balance');
        
        if (this.isConnected && this.userAccount) {
            const shortAddress = `${this.userAccount.slice(0, 6)}...${this.userAccount.slice(-4)}`;
            
            if (connectButton) {
                connectButton.textContent = shortAddress;
                connectButton.onclick = () => this.disconnectWallet();
            }
            
            if (walletStatus) {
                walletStatus.textContent = `Connected: ${shortAddress}`;
            }
            
            // Load and display balance
            this.getUserBalance().then(balance => {
                userBalanceElements.forEach(el => {
                    el.textContent = `${balance} GPUDX`;
                });
            });
            
        } else {
            if (connectButton) {
                connectButton.textContent = 'Connect Wallet';
                connectButton.onclick = () => this.connectWallet();
            }
            
            if (walletStatus) {
                walletStatus.textContent = 'Not Connected';
            }
            
            userBalanceElements.forEach(el => {
                el.textContent = '0 GPUDX';
            });
        }
    }

    disconnectWallet() {
        this.userAccount = null;
        this.isConnected = false;
        this.updateWalletDisplay();
        
        this.showNotification('👋 Wallet disconnected', 'info');
        
        // Notify other components
        window.dispatchEvent(new CustomEvent('walletChanged', {
            detail: { account: null, connected: false }
        }));
    }

    // UI UTILITY FUNCTIONS
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg text-white z-50 transform translate-x-full transition-transform duration-300 ${
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
        
        setTimeout(() => notification.style.transform = 'translateX(0)', 100);
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    showInstallMetaMaskModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4 text-center">
                <i class="fas fa-wallet text-6xl text-orange-500 mb-4"></i>
                <h3 class="text-2xl font-bold mb-4">MetaMask Required</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-6">
                    You need MetaMask to interact with GPUDex smart contracts.
                </p>
                <div class="flex gap-4">
                    <button onclick="this.closest('.fixed').remove()" 
                            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                        Cancel
                    </button>
                    <a href="https://metamask.io/download/" target="_blank" 
                       class="flex-1 bg-gradient-to-r from-primary to-secondary text-white px-4 py-2 rounded-lg hover:shadow-lg text-center">
                        Install MetaMask
                    </a>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    showNetworkSwitchModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4 text-center">
                <i class="fas fa-network-wired text-6xl text-purple-500 mb-4"></i>
                <h3 class="text-2xl font-bold mb-4">Switch Network</h3>
                <p class="text-gray-600 dark:text-gray-300 mb-6">
                    Please switch to Polygon network to use GPUDex.
                </p>
                <div class="flex gap-4">
                    <button onclick="this.closest('.fixed').remove()" 
                            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                        Cancel
                    </button>
                    <button onclick="gpuDexConnector.switchToPolygon(); this.closest('.fixed').remove()" 
                            class="flex-1 bg-gradient-to-r from-primary to-secondary text-white px-4 py-2 rounded-lg hover:shadow-lg">
                        Switch to Polygon
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    async switchToPolygon() {
        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: '0x89' }], // Polygon Mainnet
            });
        } catch (switchError) {
            // If the chain hasn't been added to MetaMask
            if (switchError.code === 4902) {
                try {
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: '0x89',
                            chainName: 'Polygon',
                            nativeCurrency: {
                                name: 'MATIC',
                                symbol: 'MATIC',
                                decimals: 18,
                            },
                            rpcUrls: ['https://polygon-rpc.com/'],
                            blockExplorerUrls: ['https://polygonscan.com/'],
                        }],
                    });
                } catch (addError) {
                    console.error('Failed to add Polygon network:', addError);
                }
            }
        }
    }
}

// ===============================================================================
// 🔥 INITIALIZE GLOBAL CONNECTOR INSTANCE 🔥
// ===============================================================================

// Create global instance
window.gpuDexConnector = new GPUDexWeb3Connector();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GPUDexWeb3Connector;
}

console.log('🔥 GPUDEX WEB3 CONNECTOR LOADED - READY FOR MAXIMUM BLOCKCHAIN INTEGRATION! 🔥'); 