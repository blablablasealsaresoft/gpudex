/**
 * GPUDx Influencer Dashboard - Vanilla JavaScript Version
 * Social media influencer engagement tracking and rewards system
 */

class InfluencerDashboard {
    constructor() {
        this.influencerData = {
            profile: {
                username: '',
                tier: 'Bronze',
                totalFollowers: 0,
                totalEngagement: 0,
                contentCreated: 0,
                referralsGenerated: 0
            },
            earnings: {
                totalEarned: 0,
                monthlyEarned: 0,
                pendingPayouts: 0,
                referralBonus: 0
            },
            campaigns: [],
            socialLinks: {
                twitter: '',
                youtube: '',
                instagram: '',
                tiktok: '',
                twitch: ''
            },
            contentLibrary: []
        };
        
        this.influencerTiers = {
            bronze: { min: 0, commission: 5, bonus: 0, color: 'from-orange-400 to-orange-600' },
            silver: { min: 1000, commission: 8, bonus: 100, color: 'from-gray-400 to-gray-600' },
            gold: { min: 10000, commission: 12, bonus: 500, color: 'from-yellow-400 to-yellow-600' },
            platinum: { min: 50000, commission: 15, bonus: 1000, color: 'from-purple-400 to-pink-600' },
            diamond: { min: 100000, commission: 20, bonus: 2500, color: 'from-blue-400 to-purple-600' }
        };
        
        this.init();
    }
    
    init() {
        this.loadInfluencerData();
        this.createInfluencerInterface();
        this.updateInfluencerDisplay();
    }
    
    createInfluencerInterface() {
        const influencerContainer = document.getElementById('influencer-dashboard');
        if (!influencerContainer) return;
        
        influencerContainer.innerHTML = `
            <div class="influencer-dashboard bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-bold gradient-text mb-4">🌟 Influencer Dashboard</h2>
                    <p class="text-gray-600 dark:text-gray-300">Create content, engage your audience, and earn GPUDX rewards!</p>
                </div>
                
                <!-- Influencer Profile -->
                <div class="influencer-profile grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                    <div class="profile-card col-span-1 bg-gradient-to-r ${this.influencerTiers[this.influencerData.profile.tier.toLowerCase()].color} text-white rounded-lg p-6">
                        <div class="text-center">
                            <div class="profile-avatar w-20 h-20 bg-white/20 rounded-full mx-auto mb-4 flex items-center justify-center">
                                <span class="text-3xl">👤</span>
                            </div>
                            <h3 class="text-xl font-bold mb-2" id="influencer-username">@${this.influencerData.profile.username || 'YourUsername'}</h3>
                            <p class="text-lg font-semibold">${this.influencerData.profile.tier} Influencer</p>
                            <p class="text-sm opacity-90 mt-2">${this.influencerTiers[this.influencerData.profile.tier.toLowerCase()].commission}% Commission Rate</p>
                        </div>
                    </div>
                    
                    <div class="stats-grid col-span-2 grid grid-cols-2 gap-4">
                        <div class="stat-card bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Followers</h4>
                            <p class="text-2xl font-bold text-blue-600" id="total-followers">${this.influencerData.profile.totalFollowers.toLocaleString()}</p>
                        </div>
                        <div class="stat-card bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Earned</h4>
                            <p class="text-2xl font-bold text-green-600" id="total-earned">${this.influencerData.earnings.totalEarned} GPUDX</p>
                        </div>
                        <div class="stat-card bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400">Content Created</h4>
                            <p class="text-2xl font-bold text-purple-600" id="content-created">${this.influencerData.profile.contentCreated}</p>
                        </div>
                        <div class="stat-card bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400">Referrals</h4>
                            <p class="text-2xl font-bold text-yellow-600" id="referrals-generated">${this.influencerData.profile.referralsGenerated}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Earnings Overview -->
                <div class="earnings-overview mb-8">
                    <h3 class="text-xl font-bold mb-4">💰 Earnings Overview</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="earning-card bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg p-6">
                            <h4 class="text-lg font-semibold mb-2">This Month</h4>
                            <p class="text-3xl font-bold" id="monthly-earned">${this.influencerData.earnings.monthlyEarned} GPUDX</p>
                            <p class="text-sm opacity-90">+12% from last month</p>
                        </div>
                        <div class="earning-card bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg p-6">
                            <h4 class="text-lg font-semibold mb-2">Pending Payouts</h4>
                            <p class="text-3xl font-bold" id="pending-payouts">${this.influencerData.earnings.pendingPayouts} GPUDX</p>
                            <button onclick="influencerDashboard.requestPayout()" class="mt-2 px-3 py-1 bg-white/20 rounded text-sm hover:bg-white/30">
                                Request Payout
                            </button>
                        </div>
                        <div class="earning-card bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg p-6">
                            <h4 class="text-lg font-semibold mb-2">Referral Bonus</h4>
                            <p class="text-3xl font-bold" id="referral-bonus">${this.influencerData.earnings.referralBonus} GPUDX</p>
                            <p class="text-sm opacity-90">From ${this.influencerData.profile.referralsGenerated} referrals</p>
                        </div>
                    </div>
                </div>
                
                <!-- Social Media Links -->
                <div class="social-links mb-8">
                    <h3 class="text-xl font-bold mb-4">🔗 Social Media Profiles</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        ${this.renderSocialLinks()}
                    </div>
                </div>
                
                <!-- Campaign Center -->
                <div class="campaign-center mb-8">
                    <h3 class="text-xl font-bold mb-4">📢 Campaign Center</h3>
                    <div class="campaign-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        ${this.renderActiveCampaigns()}
                    </div>
                </div>
                
                <!-- Content Library -->
                <div class="content-library mb-8">
                    <h3 class="text-xl font-bold mb-4">📚 Content Library</h3>
                    <div class="content-actions mb-4">
                        <button onclick="influencerDashboard.openContentCreator()" 
                                class="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90">
                            Create New Content
                        </button>
                        <button onclick="influencerDashboard.downloadAssets()" 
                                class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 ml-4">
                            Download Assets
                        </button>
                    </div>
                    <div id="content-library-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        ${this.renderContentLibrary()}
                    </div>
                </div>
                
                <!-- Tier Progress -->
                <div class="tier-progress">
                    <h3 class="text-xl font-bold mb-4">🏆 Tier Progress</h3>
                    <div class="tier-progress-card bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
                        ${this.renderTierProgress()}
                    </div>
                </div>
            </div>
        `;
    }
    
    renderSocialLinks() {
        const platforms = [
            { name: 'twitter', icon: '🐦', color: 'bg-blue-400', placeholder: 'Twitter Handle' },
            { name: 'youtube', icon: '📺', color: 'bg-red-500', placeholder: 'YouTube Channel' },
            { name: 'instagram', icon: '📷', color: 'bg-pink-500', placeholder: 'Instagram Handle' },
            { name: 'tiktok', icon: '🎵', color: 'bg-black', placeholder: 'TikTok Handle' },
            { name: 'twitch', icon: '🎮', color: 'bg-purple-600', placeholder: 'Twitch Channel' }
        ];
        
        return platforms.map(platform => `
            <div class="social-link-card ${platform.color} text-white rounded-lg p-4">
                <div class="flex items-center mb-2">
                    <span class="text-2xl mr-2">${platform.icon}</span>
                    <h4 class="font-semibold capitalize">${platform.name}</h4>
                </div>
                <input type="text" 
                       placeholder="${platform.placeholder}"
                       value="${this.influencerData.socialLinks[platform.name] || ''}"
                       onchange="influencerDashboard.updateSocialLink('${platform.name}', this.value)"
                       class="w-full px-3 py-1 rounded bg-white/20 placeholder-white/70 text-white text-sm">
                <button onclick="influencerDashboard.verifyAccount('${platform.name}')" 
                        class="mt-2 text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30">
                    Verify Account
                </button>
            </div>
        `).join('');
    }
    
    renderActiveCampaigns() {
        const campaigns = [
            {
                title: 'GPU Rental Promotion',
                reward: '500 GPUDX',
                description: 'Create content about GPU rental benefits',
                deadline: '2024-12-31',
                status: 'active'
            },
            {
                title: 'Staking Challenge',
                reward: '1000 GPUDX',
                description: 'Show your staking journey and rewards',
                deadline: '2024-12-15',
                status: 'active'
            },
            {
                title: 'Referral Contest',
                reward: '2000 GPUDX',
                description: 'Bring 10 new users to GPUDx',
                deadline: '2024-11-30',
                status: 'featured'
            }
        ];
        
        return campaigns.map(campaign => `
            <div class="campaign-card bg-white dark:bg-gray-700 rounded-lg p-6 border-2 ${campaign.status === 'featured' ? 'border-yellow-400' : 'border-gray-200'} hover:shadow-xl transition-all">
                ${campaign.status === 'featured' ? '<div class="featured-badge bg-yellow-400 text-yellow-900 px-2 py-1 rounded text-xs font-bold mb-3">FEATURED</div>' : ''}
                <h4 class="text-lg font-bold mb-2">${campaign.title}</h4>
                <p class="text-gray-600 dark:text-gray-300 text-sm mb-4">${campaign.description}</p>
                <div class="campaign-details space-y-2 mb-4">
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-500">Reward:</span>
                        <span class="text-sm font-bold text-green-600">${campaign.reward}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-500">Deadline:</span>
                        <span class="text-sm text-gray-700 dark:text-gray-300">${campaign.deadline}</span>
                    </div>
                </div>
                <button onclick="influencerDashboard.joinCampaign('${campaign.title}')" 
                        class="w-full px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90">
                    Join Campaign
                </button>
            </div>
        `).join('');
    }
    
    renderContentLibrary() {
        const contentTypes = [
            { type: 'Video Tutorial', icon: '🎥', count: 5 },
            { type: 'Instagram Posts', icon: '📱', count: 12 },
            { type: 'Twitter Threads', icon: '🧵', count: 8 },
            { type: 'Blog Articles', icon: '📝', count: 3 }
        ];
        
        return contentTypes.map(content => `
            <div class="content-type-card bg-white dark:bg-gray-700 rounded-lg p-4 hover:shadow-lg transition-all cursor-pointer"
                 onclick="influencerDashboard.viewContent('${content.type}')">
                <div class="text-center">
                    <div class="text-4xl mb-2">${content.icon}</div>
                    <h4 class="font-semibold mb-1">${content.type}</h4>
                    <p class="text-sm text-gray-500">${content.count} items</p>
                </div>
            </div>
        `).join('');
    }
    
    renderTierProgress() {
        const currentTier = this.influencerData.profile.tier.toLowerCase();
        const currentFollowers = this.influencerData.profile.totalFollowers;
        const tiers = Object.keys(this.influencerTiers);
        const currentTierIndex = tiers.indexOf(currentTier);
        const nextTier = tiers[currentTierIndex + 1];
        
        if (!nextTier) {
            return `
                <div class="text-center">
                    <h4 class="text-lg font-bold text-purple-600 mb-2">🏆 Maximum Tier Reached!</h4>
                    <p class="text-gray-600">You've achieved the highest influencer tier. Keep creating amazing content!</p>
                </div>
            `;
        }
        
        const nextTierData = this.influencerTiers[nextTier];
        const progress = Math.min((currentFollowers / nextTierData.min) * 100, 100);
        const remaining = Math.max(nextTierData.min - currentFollowers, 0);
        
        return `
            <div class="tier-progress-content">
                <div class="flex justify-between items-center mb-4">
                    <h4 class="text-lg font-bold">Current: ${currentTier.charAt(0).toUpperCase() + currentTier.slice(1)}</h4>
                    <h4 class="text-lg font-bold">Next: ${nextTier.charAt(0).toUpperCase() + nextTier.slice(1)}</h4>
                </div>
                
                <div class="progress-bar bg-gray-200 rounded-full h-4 mb-4">
                    <div class="progress-fill bg-gradient-to-r from-purple-500 to-pink-500 h-4 rounded-full transition-all duration-500" 
                         style="width: ${progress}%"></div>
                </div>
                
                <div class="tier-info grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p class="text-sm text-gray-600 mb-2">Progress: ${Math.round(progress)}%</p>
                        <p class="text-sm text-gray-600">Followers needed: ${remaining.toLocaleString()}</p>
                    </div>
                    <div>
                        <p class="text-sm text-gray-600 mb-1">Next tier benefits:</p>
                        <ul class="text-xs text-gray-500 space-y-1">
                            <li>• ${nextTierData.commission}% commission rate</li>
                            <li>• ${nextTierData.bonus} GPUDX bonus</li>
                            <li>• Priority campaign access</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateSocialLink(platform, value) {
        this.influencerData.socialLinks[platform] = value;
        this.saveInfluencerData();
    }
    
    verifyAccount(platform) {
        // Simulate account verification
        this.showNotification(`${platform.charAt(0).toUpperCase() + platform.slice(1)} account verification initiated!`, 'info');
        
        // In a real implementation, this would integrate with platform APIs
        setTimeout(() => {
            this.showNotification(`${platform.charAt(0).toUpperCase() + platform.slice(1)} account verified successfully!`, 'success');
        }, 2000);
    }
    
    joinCampaign(campaignTitle) {
        this.showNotification(`Joined campaign: ${campaignTitle}`, 'success');
        
        // Add campaign to user's active campaigns
        this.influencerData.campaigns.push({
            title: campaignTitle,
            joinedAt: new Date(),
            status: 'active'
        });
        
        this.saveInfluencerData();
    }
    
    openContentCreator() {
        // Open content creation modal or redirect
        this.showNotification('Content creator opened! Start creating amazing content!', 'info');
    }
    
    downloadAssets() {
        // Simulate asset download
        this.showNotification('GPUDx marketing assets downloaded!', 'success');
    }
    
    viewContent(contentType) {
        this.showNotification(`Viewing ${contentType} library`, 'info');
    }
    
    requestPayout() {
        if (this.influencerData.earnings.pendingPayouts > 0) {
            this.showNotification(`Payout request submitted for ${this.influencerData.earnings.pendingPayouts} GPUDX`, 'success');
            this.influencerData.earnings.totalEarned += this.influencerData.earnings.pendingPayouts;
            this.influencerData.earnings.pendingPayouts = 0;
            this.updateInfluencerDisplay();
            this.saveInfluencerData();
        } else {
            this.showNotification('No pending payouts available', 'error');
        }
    }
    
    addFollowers(count) {
        this.influencerData.profile.totalFollowers += count;
        this.checkTierUpgrade();
        this.updateInfluencerDisplay();
        this.saveInfluencerData();
    }
    
    addEarnings(amount) {
        this.influencerData.earnings.pendingPayouts += amount;
        this.influencerData.earnings.monthlyEarned += amount;
        this.updateInfluencerDisplay();
        this.saveInfluencerData();
    }
    
    checkTierUpgrade() {
        const followers = this.influencerData.profile.totalFollowers;
        let newTier = 'bronze';
        
        Object.entries(this.influencerTiers).forEach(([tier, data]) => {
            if (followers >= data.min) {
                newTier = tier;
            }
        });
        
        if (newTier !== this.influencerData.profile.tier.toLowerCase()) {
            const oldTier = this.influencerData.profile.tier;
            this.influencerData.profile.tier = newTier.charAt(0).toUpperCase() + newTier.slice(1);
            
            this.showNotification(`🎉 Tier upgraded! ${oldTier} → ${this.influencerData.profile.tier}`, 'success');
            
            // Award tier upgrade bonus
            const bonus = this.influencerTiers[newTier].bonus;
            if (bonus > 0) {
                this.influencerData.earnings.pendingPayouts += bonus;
                this.showNotification(`💰 Tier bonus: +${bonus} GPUDX`, 'success');
            }
        }
    }
    
    updateInfluencerDisplay() {
        // Update all display elements
        document.getElementById('total-followers').textContent = this.influencerData.profile.totalFollowers.toLocaleString();
        document.getElementById('total-earned').textContent = `${this.influencerData.earnings.totalEarned} GPUDX`;
        document.getElementById('content-created').textContent = this.influencerData.profile.contentCreated;
        document.getElementById('referrals-generated').textContent = this.influencerData.profile.referralsGenerated;
        document.getElementById('monthly-earned').textContent = `${this.influencerData.earnings.monthlyEarned} GPUDX`;
        document.getElementById('pending-payouts').textContent = `${this.influencerData.earnings.pendingPayouts} GPUDX`;
        document.getElementById('referral-bonus').textContent = `${this.influencerData.earnings.referralBonus} GPUDX`;
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
    
    loadInfluencerData() {
        const saved = localStorage.getItem('gpudx_influencer');
        if (saved) {
            this.influencerData = { ...this.influencerData, ...JSON.parse(saved) };
        }
    }
    
    saveInfluencerData() {
        localStorage.setItem('gpudx_influencer', JSON.stringify(this.influencerData));
    }
}

// Initialize when DOM is loaded
let influencerDashboard;
document.addEventListener('DOMContentLoaded', () => {
    influencerDashboard = new InfluencerDashboard();
});

// Export for global use
window.InfluencerDashboard = InfluencerDashboard; 