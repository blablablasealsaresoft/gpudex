/**
 * GPUDx Staking Dashboard - Vanilla JavaScript Version
 * 4-Tier Staking System: Bronze, Silver, Gold, Diamond
 */

class StakingDashboard {
    constructor() {
        this.stakingTiers = {
            bronze: { min: 1000, apy: 8, color: 'from-orange-400 to-orange-600' },
            silver: { min: 10000, apy: 12, color: 'from-gray-400 to-gray-600' },
            gold: { min: 100000, apy: 15, color: 'from-yellow-400 to-yellow-600' },
            diamond: { min: 1000000, apy: 20, color: 'from-purple-400 to-pink-600' }
        };
        
        this.userStaking = {
            totalStaked: 0,
            currentTier: 'none',
            pendingRewards: 0,
            stakingHistory: []
        };
        
        this.init();
    }
    
    init() {
        this.createStakingInterface();
        this.loadUserData();
        this.startRewardsTimer();
    }
    
    createStakingInterface() {
        const stakingContainer = document.getElementById('staking-dashboard');
        if (!stakingContainer) return;
        
        stakingContainer.innerHTML = `
            <div class="staking-dashboard bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-bold gradient-text mb-4">GPUDX Staking Dashboard</h2>
                    <p class="text-gray-600 dark:text-gray-300">Stake GPUDX tokens to earn rewards and unlock exclusive benefits</p>
                </div>
                
                <!-- Current Staking Stats -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div class="stat-card bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Total Staked</h3>
                        <p class="text-2xl font-bold" id="total-staked">0 GPUDX</p>
                    </div>
                    <div class="stat-card bg-gradient-to-r from-green-500 to-blue-600 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Current Tier</h3>
                        <p class="text-2xl font-bold" id="current-tier">None</p>
                    </div>
                    <div class="stat-card bg-gradient-to-r from-yellow-500 to-red-600 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Pending Rewards</h3>
                        <p class="text-2xl font-bold" id="pending-rewards">0 GPUDX</p>
                    </div>
                </div>
                
                <!-- Staking Input -->
                <div class="staking-input mb-8 p-6 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <h3 class="text-xl font-bold mb-4">Stake GPUDX Tokens</h3>
                    <div class="flex gap-4">
                        <input type="number" id="stake-amount" placeholder="Enter amount to stake" 
                               class="flex-1 px-4 py-2 border rounded-lg dark:bg-gray-600 dark:text-white">
                        <button onclick="stakingDashboard.stakeTokens()" 
                                class="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90">
                            Stake Now
                        </button>
                    </div>
                    <p class="text-sm text-gray-500 mt-2">Minimum: 1,000 GPUDX</p>
                </div>
                
                <!-- Staking Tiers -->
                <div class="staking-tiers grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
                    ${this.renderStakingTiers()}
                </div>
                
                <!-- Staking History -->
                <div class="staking-history">
                    <h3 class="text-xl font-bold mb-4">Staking History</h3>
                    <div id="staking-history-list" class="space-y-3">
                        <p class="text-gray-500">No staking history yet. Start staking to see your records here!</p>
                    </div>
                </div>
                
                <!-- Rewards Calculator -->
                <div class="rewards-calculator mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <h3 class="text-xl font-bold mb-4">Rewards Calculator</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium mb-2">Amount to Stake</label>
                            <input type="number" id="calc-amount" placeholder="Enter amount" 
                                   oninput="stakingDashboard.calculateRewards()"
                                   class="w-full px-4 py-2 border rounded-lg dark:bg-gray-600 dark:text-white">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2">Estimated Annual Rewards</label>
                            <div id="estimated-rewards" class="text-2xl font-bold text-green-600">0 GPUDX</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderStakingTiers() {
        return Object.entries(this.stakingTiers).map(([tier, data]) => `
            <div class="tier-card bg-gradient-to-r ${data.color} text-white rounded-lg p-6 transform hover:scale-105 transition-all">
                <h4 class="text-xl font-bold mb-2 capitalize">${tier}</h4>
                <div class="tier-info space-y-2">
                    <p class="text-sm opacity-90">Minimum: ${data.min.toLocaleString()} GPUDX</p>
                    <p class="text-lg font-bold">${data.apy}% APY</p>
                    <div class="benefits mt-4">
                        <p class="text-sm font-semibold mb-1">Benefits:</p>
                        <ul class="text-xs space-y-1">
                            ${this.getTierBenefits(tier).map(benefit => `<li>• ${benefit}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    getTierBenefits(tier) {
        const benefits = {
            bronze: ['8% APY', 'Basic support', 'Standard fees'],
            silver: ['12% APY', 'Priority support', '2% fee discount'],
            gold: ['15% APY', 'Premium support', '5% fee discount', 'Early access'],
            diamond: ['20% APY', 'VIP support', '10% fee discount', 'Revenue sharing']
        };
        return benefits[tier] || [];
    }
    
    calculateTier(amount) {
        if (amount >= this.stakingTiers.diamond.min) return 'diamond';
        if (amount >= this.stakingTiers.gold.min) return 'gold';
        if (amount >= this.stakingTiers.silver.min) return 'silver';
        if (amount >= this.stakingTiers.bronze.min) return 'bronze';
        return 'none';
    }
    
    stakeTokens() {
        const amount = parseFloat(document.getElementById('stake-amount').value);
        
        if (!amount || amount < 1000) {
            this.showNotification('Minimum staking amount is 1,000 GPUDX', 'error');
            return;
        }
        
        // Simulate staking transaction
        this.userStaking.totalStaked += amount;
        this.userStaking.currentTier = this.calculateTier(this.userStaking.totalStaked);
        
        // Add to history
        this.userStaking.stakingHistory.push({
            amount: amount,
            timestamp: new Date(),
            type: 'stake',
            tier: this.userStaking.currentTier
        });
        
        // Save to localStorage
        localStorage.setItem('gpudx_staking', JSON.stringify(this.userStaking));
        
        // Update UI
        this.updateStakingDisplay();
        this.updateStakingHistory();
        
        // Clear input
        document.getElementById('stake-amount').value = '';
        
        this.showNotification(`Successfully staked ${amount.toLocaleString()} GPUDX!`, 'success');
    }
    
    calculateRewards() {
        const amount = parseFloat(document.getElementById('calc-amount').value) || 0;
        const tier = this.calculateTier(amount);
        const apy = tier !== 'none' ? this.stakingTiers[tier].apy : 0;
        const annualRewards = (amount * apy) / 100;
        
        document.getElementById('estimated-rewards').textContent = `${annualRewards.toLocaleString()} GPUDX`;
    }
    
    updateStakingDisplay() {
        document.getElementById('total-staked').textContent = `${this.userStaking.totalStaked.toLocaleString()} GPUDX`;
        document.getElementById('current-tier').textContent = this.userStaking.currentTier.charAt(0).toUpperCase() + this.userStaking.currentTier.slice(1);
        document.getElementById('pending-rewards').textContent = `${this.userStaking.pendingRewards.toFixed(2)} GPUDX`;
    }
    
    updateStakingHistory() {
        const historyContainer = document.getElementById('staking-history-list');
        if (!this.userStaking.stakingHistory.length) return;
        
        historyContainer.innerHTML = this.userStaking.stakingHistory
            .slice(-10) // Show last 10 transactions
            .reverse()
            .map(record => `
                <div class="history-item flex justify-between items-center p-3 bg-white dark:bg-gray-700 rounded-lg shadow">
                    <div>
                        <p class="font-semibold">${record.type === 'stake' ? 'Staked' : 'Unstaked'} ${record.amount.toLocaleString()} GPUDX</p>
                        <p class="text-sm text-gray-500">${record.timestamp.toLocaleDateString()}</p>
                    </div>
                    <div class="text-right">
                        <span class="tier-badge px-2 py-1 rounded text-xs font-bold bg-gradient-to-r ${this.stakingTiers[record.tier]?.color || 'from-gray-400 to-gray-600'} text-white">
                            ${record.tier.toUpperCase()}
                        </span>
                    </div>
                </div>
            `).join('');
    }
    
    loadUserData() {
        const saved = localStorage.getItem('gpudx_staking');
        if (saved) {
            this.userStaking = { ...this.userStaking, ...JSON.parse(saved) };
            // Convert timestamp strings back to Date objects
            this.userStaking.stakingHistory = this.userStaking.stakingHistory.map(record => ({
                ...record,
                timestamp: new Date(record.timestamp)
            }));
        }
        this.updateStakingDisplay();
        this.updateStakingHistory();
    }
    
    startRewardsTimer() {
        // Update rewards every minute
        setInterval(() => {
            if (this.userStaking.totalStaked > 0) {
                const tier = this.userStaking.currentTier;
                if (tier !== 'none') {
                    const apy = this.stakingTiers[tier].apy;
                    const rewardsPerMinute = (this.userStaking.totalStaked * apy / 100) / (365 * 24 * 60);
                    this.userStaking.pendingRewards += rewardsPerMinute;
                    this.updateStakingDisplay();
                }
            }
        }, 60000); // 1 minute
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize when DOM is loaded
let stakingDashboard;
document.addEventListener('DOMContentLoaded', () => {
    stakingDashboard = new StakingDashboard();
});

// Export for global use
window.StakingDashboard = StakingDashboard; 