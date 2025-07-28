/**
 * GPUDx Achievement System - Vanilla JavaScript Version
 * Comprehensive gamification with achievements, badges, and rewards
 */

class AchievementSystem {
    constructor() {
        this.achievements = {
            firstStake: {
                id: 'first-stake',
                name: 'First Steps',
                description: 'Complete your first GPUDX stake',
                reward: 100,
                icon: '🚀',
                category: 'staking',
                unlocked: false,
                progress: 0,
                required: 1
            },
            bronzeStaker: {
                id: 'bronze-staker',
                name: 'Bronze Warrior',
                description: 'Reach Bronze staking tier',
                reward: 500,
                icon: '🥉',
                category: 'staking',
                unlocked: false,
                progress: 0,
                required: 1000
            },
            silverStaker: {
                id: 'silver-staker',
                name: 'Silver Guardian',
                description: 'Reach Silver staking tier',
                reward: 1000,
                icon: '🥈',
                category: 'staking',
                unlocked: false,
                progress: 0,
                required: 10000
            },
            goldStaker: {
                id: 'gold-staker',
                name: 'Gold Champion',
                description: 'Reach Gold staking tier',
                reward: 2500,
                icon: '🥇',
                category: 'staking',
                unlocked: false,
                progress: 0,
                required: 100000
            },
            diamondStaker: {
                id: 'diamond-staker',
                name: 'Diamond Legend',
                description: 'Reach Diamond staking tier',
                reward: 10000,
                icon: '💎',
                category: 'staking',
                unlocked: false,
                progress: 0,
                required: 1000000
            },
            firstRental: {
                id: 'first-rental',
                name: 'GPU Explorer',
                description: 'Complete your first GPU rental',
                reward: 250,
                icon: '⚡',
                category: 'rental',
                unlocked: false,
                progress: 0,
                required: 1
            },
            powerUser: {
                id: 'power-user',
                name: 'Power User',
                description: 'Complete 10 GPU rentals',
                reward: 1000,
                icon: '💪',
                category: 'rental',
                unlocked: false,
                progress: 0,
                required: 10
            },
            socialButterfly: {
                id: 'social-butterfly',
                name: 'Social Butterfly',
                description: 'Share GPUDx on 3 social platforms',
                reward: 500,
                icon: '🦋',
                category: 'social',
                unlocked: false,
                progress: 0,
                required: 3
            },
            referralMaster: {
                id: 'referral-master',
                name: 'Referral Master',
                description: 'Refer 5 new users to GPUDx',
                reward: 2000,
                icon: '👑',
                category: 'social',
                unlocked: false,
                progress: 0,
                required: 5
            },
            earlyAdopter: {
                id: 'early-adopter',
                name: 'Early Adopter',
                description: 'Join GPUDx in the first month',
                reward: 1000,
                icon: '🏆',
                category: 'special',
                unlocked: false,
                progress: 0,
                required: 1
            }
        };
        
        this.userProgress = {
            totalAchievements: 0,
            totalRewards: 0,
            unlockedAchievements: [],
            stats: {
                stakingAmount: 0,
                rentalCount: 0,
                socialShares: 0,
                referrals: 0
            }
        };
        
        this.init();
    }
    
    init() {
        this.loadUserProgress();
        this.createAchievementInterface();
        this.updateAchievementDisplay();
    }
    
    createAchievementInterface() {
        const achievementContainer = document.getElementById('achievement-system');
        if (!achievementContainer) return;
        
        achievementContainer.innerHTML = `
            <div class="achievement-system bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-bold gradient-text mb-4">🏆 Achievement Center</h2>
                    <p class="text-gray-600 dark:text-gray-300">Complete challenges and earn GPUDX rewards!</p>
                </div>
                
                <!-- Achievement Stats -->
                <div class="achievement-stats grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div class="stat-card bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Achievements Unlocked</h3>
                        <p class="text-3xl font-bold" id="total-achievements">0/${Object.keys(this.achievements).length}</p>
                    </div>
                    <div class="stat-card bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Total Rewards Earned</h3>
                        <p class="text-3xl font-bold" id="total-rewards">0 GPUDX</p>
                    </div>
                    <div class="stat-card bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-lg p-6">
                        <h3 class="text-lg font-semibold mb-2">Completion Rate</h3>
                        <p class="text-3xl font-bold" id="completion-rate">0%</p>
                    </div>
                </div>
                
                <!-- Category Filters -->
                <div class="category-filters mb-6">
                    <div class="flex flex-wrap gap-2">
                        <button onclick="achievementSystem.filterAchievements('all')" 
                                class="filter-btn active px-4 py-2 rounded-lg bg-purple-500 text-white hover:bg-purple-600">
                            All
                        </button>
                        <button onclick="achievementSystem.filterAchievements('staking')" 
                                class="filter-btn px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300">
                            Staking
                        </button>
                        <button onclick="achievementSystem.filterAchievements('rental')" 
                                class="filter-btn px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300">
                            Rental
                        </button>
                        <button onclick="achievementSystem.filterAchievements('social')" 
                                class="filter-btn px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300">
                            Social
                        </button>
                        <button onclick="achievementSystem.filterAchievements('special')" 
                                class="filter-btn px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300">
                            Special
                        </button>
                    </div>
                </div>
                
                <!-- Achievements Grid -->
                <div id="achievements-grid" class="achievements-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                    ${this.renderAchievements()}
                </div>
                
                <!-- Recent Achievements -->
                <div class="recent-achievements">
                    <h3 class="text-xl font-bold mb-4">🎉 Recent Achievements</h3>
                    <div id="recent-achievements-list" class="space-y-3">
                        <p class="text-gray-500">No achievements unlocked yet. Start exploring to earn your first achievement!</p>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="quick-actions mt-8 p-6 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg">
                    <h3 class="text-xl font-bold mb-4">🚀 Quick Actions</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <button onclick="achievementSystem.shareToSocial('twitter')" 
                                class="action-btn p-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                            Share on Twitter
                        </button>
                        <button onclick="achievementSystem.shareToSocial('facebook')" 
                                class="action-btn p-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                            Share on Facebook
                        </button>
                        <button onclick="achievementSystem.generateReferralLink()" 
                                class="action-btn p-4 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors">
                            Get Referral Link
                        </button>
                        <button onclick="achievementSystem.claimEarlyAdopter()" 
                                class="action-btn p-4 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors">
                            Claim Early Adopter
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderAchievements() {
        return Object.values(this.achievements).map(achievement => {
            const progressPercent = Math.min((achievement.progress / achievement.required) * 100, 100);
            const isUnlocked = achievement.unlocked;
            
            return `
                <div class="achievement-card ${isUnlocked ? 'unlocked' : 'locked'} bg-white dark:bg-gray-700 rounded-lg p-6 border-2 ${isUnlocked ? 'border-green-500 shadow-green-200' : 'border-gray-200'} hover:shadow-xl transition-all" data-category="${achievement.category}">
                    <div class="achievement-header flex items-center mb-4">
                        <div class="achievement-icon text-4xl mr-4 ${isUnlocked ? '' : 'grayscale opacity-50'}">${achievement.icon}</div>
                        <div class="achievement-info flex-1">
                            <h4 class="text-lg font-bold ${isUnlocked ? 'text-green-600' : 'text-gray-700 dark:text-gray-300'}">${achievement.name}</h4>
                            <p class="text-sm text-gray-500">${achievement.description}</p>
                        </div>
                        ${isUnlocked ? '<span class="unlocked-badge bg-green-500 text-white px-2 py-1 rounded text-xs font-bold">UNLOCKED</span>' : ''}
                    </div>
                    
                    <div class="achievement-progress mb-4">
                        <div class="progress-bar bg-gray-200 rounded-full h-2 mb-2">
                            <div class="progress-fill bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-500" 
                                 style="width: ${progressPercent}%"></div>
                        </div>
                        <div class="progress-text text-sm text-gray-600 flex justify-between">
                            <span>${achievement.progress.toLocaleString()} / ${achievement.required.toLocaleString()}</span>
                            <span>${Math.round(progressPercent)}%</span>
                        </div>
                    </div>
                    
                    <div class="achievement-reward flex items-center justify-between">
                        <span class="reward-amount bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-bold">
                            +${achievement.reward} GPUDX
                        </span>
                        <span class="achievement-category bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs uppercase">
                            ${achievement.category}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    filterAchievements(category) {
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-purple-500', 'text-white');
            btn.classList.add('bg-gray-200', 'text-gray-700');
        });
        event.target.classList.add('active', 'bg-purple-500', 'text-white');
        event.target.classList.remove('bg-gray-200', 'text-gray-700');
        
        // Filter achievements
        const achievementCards = document.querySelectorAll('.achievement-card');
        achievementCards.forEach(card => {
            if (category === 'all' || card.dataset.category === category) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    updateProgress(type, amount) {
        switch (type) {
            case 'stake':
                this.userProgress.stats.stakingAmount += amount;
                this.checkStakingAchievements();
                break;
            case 'rental':
                this.userProgress.stats.rentalCount++;
                this.checkRentalAchievements();
                break;
            case 'social':
                this.userProgress.stats.socialShares++;
                this.checkSocialAchievements();
                break;
            case 'referral':
                this.userProgress.stats.referrals++;
                this.checkReferralAchievements();
                break;
        }
        
        this.saveUserProgress();
        this.updateAchievementDisplay();
    }
    
    checkStakingAchievements() {
        const stakingAmount = this.userProgress.stats.stakingAmount;
        
        if (stakingAmount >= 1 && !this.achievements.firstStake.unlocked) {
            this.unlockAchievement('firstStake');
        }
        if (stakingAmount >= 1000 && !this.achievements.bronzeStaker.unlocked) {
            this.unlockAchievement('bronzeStaker');
        }
        if (stakingAmount >= 10000 && !this.achievements.silverStaker.unlocked) {
            this.unlockAchievement('silverStaker');
        }
        if (stakingAmount >= 100000 && !this.achievements.goldStaker.unlocked) {
            this.unlockAchievement('goldStaker');
        }
        if (stakingAmount >= 1000000 && !this.achievements.diamondStaker.unlocked) {
            this.unlockAchievement('diamondStaker');
        }
        
        // Update progress for locked achievements
        Object.keys(this.achievements).forEach(key => {
            const achievement = this.achievements[key];
            if (achievement.category === 'staking' && !achievement.unlocked) {
                achievement.progress = Math.min(stakingAmount, achievement.required);
            }
        });
    }
    
    checkRentalAchievements() {
        const rentalCount = this.userProgress.stats.rentalCount;
        
        if (rentalCount >= 1 && !this.achievements.firstRental.unlocked) {
            this.unlockAchievement('firstRental');
        }
        if (rentalCount >= 10 && !this.achievements.powerUser.unlocked) {
            this.unlockAchievement('powerUser');
        }
        
        // Update progress
        if (!this.achievements.powerUser.unlocked) {
            this.achievements.powerUser.progress = Math.min(rentalCount, 10);
        }
    }
    
    checkSocialAchievements() {
        const socialShares = this.userProgress.stats.socialShares;
        
        if (socialShares >= 3 && !this.achievements.socialButterfly.unlocked) {
            this.unlockAchievement('socialButterfly');
        }
        
        // Update progress
        if (!this.achievements.socialButterfly.unlocked) {
            this.achievements.socialButterfly.progress = Math.min(socialShares, 3);
        }
    }
    
    checkReferralAchievements() {
        const referrals = this.userProgress.stats.referrals;
        
        if (referrals >= 5 && !this.achievements.referralMaster.unlocked) {
            this.unlockAchievement('referralMaster');
        }
        
        // Update progress
        if (!this.achievements.referralMaster.unlocked) {
            this.achievements.referralMaster.progress = Math.min(referrals, 5);
        }
    }
    
    unlockAchievement(achievementKey) {
        const achievement = this.achievements[achievementKey];
        if (achievement.unlocked) return;
        
        achievement.unlocked = true;
        achievement.progress = achievement.required;
        
        this.userProgress.totalAchievements++;
        this.userProgress.totalRewards += achievement.reward;
        this.userProgress.unlockedAchievements.unshift({
            ...achievement,
            unlockedAt: new Date()
        });
        
        this.showAchievementNotification(achievement);
        this.saveUserProgress();
    }
    
    showAchievementNotification(achievement) {
        const notification = document.createElement('div');
        notification.className = 'achievement-notification fixed top-4 right-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white p-6 rounded-lg shadow-2xl z-50 max-w-sm';
        notification.innerHTML = `
            <div class="flex items-center">
                <div class="text-4xl mr-4">${achievement.icon}</div>
                <div>
                    <h4 class="font-bold text-lg">Achievement Unlocked!</h4>
                    <p class="text-sm opacity-90">${achievement.name}</p>
                    <p class="text-xs mt-1">+${achievement.reward} GPUDX earned!</p>
                </div>
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
    
    updateAchievementDisplay() {
        const totalAchievements = Object.keys(this.achievements).length;
        const unlockedCount = this.userProgress.totalAchievements;
        const completionRate = Math.round((unlockedCount / totalAchievements) * 100);
        
        const totalAchievementsEl = document.getElementById('total-achievements');
        const totalRewardsEl = document.getElementById('total-rewards');
        const completionRateEl = document.getElementById('completion-rate');
        
        if (totalAchievementsEl) totalAchievementsEl.textContent = `${unlockedCount}/${totalAchievements}`;
        if (totalRewardsEl) totalRewardsEl.textContent = `${this.userProgress.totalRewards.toLocaleString()} GPUDX`;
        if (completionRateEl) completionRateEl.textContent = `${completionRate}%`;
        
        // Update recent achievements
        this.updateRecentAchievements();
        
        // Re-render achievements grid
        const achievementsGrid = document.getElementById('achievements-grid');
        if (achievementsGrid) {
            achievementsGrid.innerHTML = this.renderAchievements();
        }
    }
    
    updateRecentAchievements() {
        const recentList = document.getElementById('recent-achievements-list');
        if (!recentList) return;
        
        if (this.userProgress.unlockedAchievements.length === 0) return;
        
        recentList.innerHTML = this.userProgress.unlockedAchievements
            .slice(0, 5)
            .map(achievement => `
                <div class="recent-achievement flex items-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div class="text-2xl mr-3">${achievement.icon}</div>
                    <div class="flex-1">
                        <p class="font-semibold text-green-800 dark:text-green-300">${achievement.name}</p>
                        <p class="text-sm text-green-600 dark:text-green-400">+${achievement.reward} GPUDX earned</p>
                    </div>
                    <div class="text-xs text-gray-500">
                        ${new Date(achievement.unlockedAt).toLocaleDateString()}
                    </div>
                </div>
            `).join('');
    }
    
    shareToSocial(platform) {
        const messages = {
            twitter: "Just joined @GPUDex - the ultimate GPU rental platform! 🚀⚡ #GPUDex #GPU #Crypto",
            facebook: "Check out GPUDex - rent GPUs on demand and earn crypto rewards! 🚀",
            linkedin: "Excited to try GPUDx - the decentralized GPU rental marketplace!"
        };
        
        const urls = {
            twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(messages.twitter)}`,
            facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent('https://gpudex.ai')}`,
            linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent('https://gpudex.ai')}`
        };
        
        window.open(urls[platform], '_blank', 'width=600,height=400');
        this.updateProgress('social');
    }
    
    generateReferralLink() {
        const referralCode = Math.random().toString(36).substring(2, 8).toUpperCase();
        const referralLink = `https://gpudex.ai/ref/${referralCode}`;
        
        navigator.clipboard.writeText(referralLink).then(() => {
            this.showNotification('Referral link copied to clipboard!', 'success');
        });
    }
    
    claimEarlyAdopter() {
        if (!this.achievements.earlyAdopter.unlocked) {
            this.unlockAchievement('earlyAdopter');
        } else {
            this.showNotification('Early adopter badge already claimed!', 'info');
        }
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
    
    loadUserProgress() {
        const saved = localStorage.getItem('gpudx_achievements');
        if (saved) {
            const data = JSON.parse(saved);
            this.userProgress = { ...this.userProgress, ...data.userProgress };
            this.achievements = { ...this.achievements, ...data.achievements };
        }
    }
    
    saveUserProgress() {
        localStorage.setItem('gpudx_achievements', JSON.stringify({
            userProgress: this.userProgress,
            achievements: this.achievements
        }));
    }
}

// Initialize when DOM is loaded
let achievementSystem;
document.addEventListener('DOMContentLoaded', () => {
    achievementSystem = new AchievementSystem();
});

// Export for global use
window.AchievementSystem = AchievementSystem; 