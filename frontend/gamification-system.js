/**
 * GPUDex Advanced Gamification System
 * Achievements, Leaderboards, Missions, and Social Features
 * BILL GATES ON ADDERALL: MAXIMUM ENGAGEMENT!
 */

class GPUDexGamificationSystem {
    constructor(apiConnector) {
        this.api = apiConnector;
        this.userProfile = null;
        this.achievements = new Map();
        this.missions = new Map();
        this.leaderboards = new Map();
        this.socialEvents = [];
        this.userXP = 0;
        this.userLevel = 1;
        
        this.init();
    }
    
    init() {
        this.loadAchievements();
        this.loadMissions();
        this.loadLeaderboards();
        this.setupEventListeners();
        this.startMissionTimer();
    }
    
    // =============================================================================
    // ACHIEVEMENT SYSTEM
    // =============================================================================
    
    loadAchievements() {
        const achievementDefinitions = {
            // Welcome & Onboarding
            'welcome': {
                id: 'welcome',
                name: 'Welcome to GPUDex!',
                description: 'Successfully connected your wallet',
                icon: 'fas fa-hand-wave',
                rarity: 'common',
                reward: 100,
                category: 'onboarding',
                unlocked: false
            },
            'first_stake': {
                id: 'first_stake',
                name: 'Staking Pioneer',
                description: 'Made your first GPUDX stake',
                icon: 'fas fa-seedling',
                rarity: 'common',
                reward: 250,
                category: 'staking',
                unlocked: false
            },
            'first_rental': {
                id: 'first_rental',
                name: 'GPU Explorer',
                description: 'Completed your first GPU rental',
                icon: 'fas fa-rocket',
                rarity: 'common',
                reward: 200,
                category: 'rental',
                unlocked: false
            },
            
            // Staking Achievements
            'bronze_tier': {
                id: 'bronze_tier',
                name: 'Bronze Champion',
                description: 'Reached Bronze staking tier',
                icon: 'fas fa-medal',
                rarity: 'common',
                reward: 500,
                category: 'staking',
                unlocked: false
            },
            'silver_tier': {
                id: 'silver_tier',
                name: 'Silver Elite',
                description: 'Reached Silver staking tier',
                icon: 'fas fa-gem',
                rarity: 'uncommon',
                reward: 1000,
                category: 'staking',
                unlocked: false
            },
            'gold_tier': {
                id: 'gold_tier',
                name: 'Gold Aristocrat',
                description: 'Reached Gold staking tier',
                icon: 'fas fa-crown',
                rarity: 'rare',
                reward: 2500,
                category: 'staking',
                unlocked: false
            },
            'diamond_tier': {
                id: 'diamond_tier',
                name: 'Diamond Legend',
                description: 'Reached Diamond staking tier',
                icon: 'fas fa-star',
                rarity: 'legendary',
                reward: 10000,
                category: 'staking',
                unlocked: false
            },
            
            // Usage Achievements
            'gpu_addict': {
                id: 'gpu_addict',
                name: 'GPU Addict',
                description: 'Used 100+ GPU hours',
                icon: 'fas fa-fire',
                rarity: 'uncommon',
                reward: 1500,
                category: 'usage',
                unlocked: false
            },
            'power_user': {
                id: 'power_user',
                name: 'Power User',
                description: 'Used 1000+ GPU hours',
                icon: 'fas fa-bolt',
                rarity: 'rare',
                reward: 5000,
                category: 'usage',
                unlocked: false
            },
            'enterprise_client': {
                id: 'enterprise_client',
                name: 'Enterprise Elite',
                description: 'Registered as enterprise client',
                icon: 'fas fa-building',
                rarity: 'rare',
                reward: 3000,
                category: 'enterprise',
                unlocked: false
            },
            
            // Social Achievements
            'referral_champion': {
                id: 'referral_champion',
                name: 'Referral Champion',
                description: 'Referred 10 new users',
                icon: 'fas fa-users',
                rarity: 'rare',
                reward: 5000,
                category: 'social',
                unlocked: false
            },
            'community_leader': {
                id: 'community_leader',
                name: 'Community Leader',
                description: 'Top 10 on monthly leaderboard',
                icon: 'fas fa-trophy',
                rarity: 'legendary',
                reward: 15000,
                category: 'social',
                unlocked: false
            },
            
            // Special Events
            'early_adopter': {
                id: 'early_adopter',
                name: 'Early Adopter',
                description: 'Joined during beta period',
                icon: 'fas fa-rocket',
                rarity: 'legendary',
                reward: 25000,
                category: 'special',
                unlocked: false
            },
            'whale': {
                id: 'whale',
                name: 'Token Whale',
                description: 'Staked 1M+ GPUDX tokens',
                icon: 'fas fa-whale',
                rarity: 'mythical',
                reward: 50000,
                category: 'staking',
                unlocked: false
            }
        };
        
        Object.values(achievementDefinitions).forEach(achievement => {
            this.achievements.set(achievement.id, achievement);
        });
    }
    
    async checkAchievement(achievementId, currentValue = null) {
        const achievement = this.achievements.get(achievementId);
        if (!achievement || achievement.unlocked) return false;
        
        let shouldUnlock = false;
        
        // Check achievement conditions
        switch (achievementId) {
            case 'welcome':
                shouldUnlock = this.api && this.api.isAuthenticated;
                break;
            case 'bronze_tier':
                shouldUnlock = currentValue >= 10000; // 10K GPUDX
                break;
            case 'silver_tier':
                shouldUnlock = currentValue >= 100000; // 100K GPUDX
                break;
            case 'gold_tier':
                shouldUnlock = currentValue >= 500000; // 500K GPUDX
                break;
            case 'diamond_tier':
                shouldUnlock = currentValue >= 2000000; // 2M GPUDX
                break;
            case 'gpu_addict':
                shouldUnlock = currentValue >= 100; // 100 hours
                break;
            case 'power_user':
                shouldUnlock = currentValue >= 1000; // 1000 hours
                break;
            case 'whale':
                shouldUnlock = currentValue >= 1000000; // 1M GPUDX
                break;
            default:
                shouldUnlock = true; // For manually triggered achievements
        }
        
        if (shouldUnlock) {
            await this.unlockAchievement(achievementId);
            return true;
        }
        
        return false;
    }
    
    async unlockAchievement(achievementId) {
        const achievement = this.achievements.get(achievementId);
        if (!achievement || achievement.unlocked) return;
        
        // Mark as unlocked
        achievement.unlocked = true;
        achievement.unlockedAt = Date.now();
        
        // Award XP
        this.gainXP(achievement.reward);
        
        // Show achievement notification
        this.showAchievementUnlock(achievement);
        
        // Save to backend
        if (this.api) {
            try {
                await this.api.apiCall('/gamification/achievement-unlock', 'POST', {
                    achievement_id: achievementId,
                    user_address: this.api.userAccount
                });
            } catch (error) {
                console.error('Failed to save achievement:', error);
            }
        }
        
        // Trigger celebration effects
        this.triggerCelebration(achievement.rarity);
        
        // Check for combo achievements
        this.checkComboAchievements();
    }
    
    showAchievementUnlock(achievement) {
        const rarityColors = {
            common: 'from-gray-400 to-gray-600',
            uncommon: 'from-green-400 to-green-600',
            rare: 'from-blue-400 to-blue-600',
            legendary: 'from-purple-400 to-purple-600',
            mythical: 'from-pink-400 to-pink-600'
        };
        
        const notification = document.createElement('div');
        notification.className = `achievement-unlock fixed top-20 right-4 max-w-sm bg-gradient-to-r ${rarityColors[achievement.rarity]} text-white p-6 rounded-xl shadow-2xl transform translate-x-full transition-all duration-500 z-50`;
        notification.innerHTML = `
            <div class="flex items-center space-x-4">
                <div class="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                    <i class="${achievement.icon} text-2xl"></i>
                </div>
                <div class="flex-1">
                    <div class="flex items-center space-x-2 mb-1">
                        <span class="text-xs font-bold uppercase tracking-wide opacity-90">${achievement.rarity}</span>
                        <span class="text-xs">+${achievement.reward} XP</span>
                    </div>
                    <div class="font-bold text-lg">${achievement.name}</div>
                    <div class="text-sm opacity-90">${achievement.description}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Add sparkle effects
        this.addSparkleEffects(notification);
        
        // Remove after 6 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 500);
        }, 6000);
        
        // Play achievement sound (if enabled)
        this.playAchievementSound(achievement.rarity);
    }
    
    triggerCelebration(rarity) {
        // Screen effects based on rarity
        const celebrationIntensity = {
            common: 1,
            uncommon: 2,
            rare: 3,
            legendary: 4,
            mythical: 5
        };
        
        const intensity = celebrationIntensity[rarity];
        
        // Create fireworks effect
        for (let i = 0; i < intensity * 3; i++) {
            setTimeout(() => {
                this.createFirework();
            }, i * 200);
        }
        
        // Screen flash for legendary+
        if (intensity >= 4) {
            this.screenFlash();
        }
    }
    
    createFirework() {
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        const firework = document.createElement('div');
        firework.style.cssText = `
            position: fixed;
            width: 6px;
            height: 6px;
            background: ${color};
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
            left: ${Math.random() * window.innerWidth}px;
            top: ${Math.random() * window.innerHeight}px;
            box-shadow: 0 0 10px ${color};
        `;
        
        document.body.appendChild(firework);
        
        // Animate
        firework.animate([
            { transform: 'scale(0)', opacity: 1 },
            { transform: 'scale(3)', opacity: 0 }
        ], {
            duration: 1000,
            easing: 'ease-out'
        }).onfinish = () => firework.remove();
    }
    
    screenFlash() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(circle, rgba(102,126,234,0.3) 0%, transparent 70%);
            pointer-events: none;
            z-index: 9998;
        `;
        
        document.body.appendChild(flash);
        
        flash.animate([
            { opacity: 0 },
            { opacity: 1 },
            { opacity: 0 }
        ], {
            duration: 800,
            easing: 'ease-in-out'
        }).onfinish = () => flash.remove();
    }
    
    addSparkleEffects(element) {
        for (let i = 0; i < 8; i++) {
            const sparkle = document.createElement('div');
            sparkle.innerHTML = '✨';
            sparkle.style.cssText = `
                position: absolute;
                font-size: 12px;
                pointer-events: none;
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                animation: sparkle 2s linear infinite;
            `;
            
            element.appendChild(sparkle);
            
            setTimeout(() => sparkle.remove(), 2000);
        }
    }
    
    // =============================================================================
    // MISSION SYSTEM
    // =============================================================================
    
    loadMissions() {
        const missionDefinitions = {
            'daily_login': {
                id: 'daily_login',
                name: 'Daily Login',
                description: 'Log in to GPUDex',
                type: 'daily',
                target: 1,
                current: 0,
                reward: 50,
                expires: this.getTomorrowTimestamp()
            },
            'daily_stake': {
                id: 'daily_stake',
                name: 'Daily Staker',
                description: 'Stake GPUDX tokens',
                type: 'daily',
                target: 1,
                current: 0,
                reward: 100,
                expires: this.getTomorrowTimestamp()
            },
            'weekly_rental': {
                id: 'weekly_rental',
                name: 'Weekly Renter',
                description: 'Rent 5 GPU hours this week',
                type: 'weekly',
                target: 5,
                current: 0,
                reward: 500,
                expires: this.getNextWeekTimestamp()
            },
            'weekly_referral': {
                id: 'weekly_referral',
                name: 'Referral Master',
                description: 'Refer 3 new users this week',
                type: 'weekly',
                target: 3,
                current: 0,
                reward: 1000,
                expires: this.getNextWeekTimestamp()
            },
            'monthly_whale': {
                id: 'monthly_whale',
                name: 'Monthly Whale',
                description: 'Stake 100K+ GPUDX this month',
                type: 'monthly',
                target: 100000,
                current: 0,
                reward: 5000,
                expires: this.getNextMonthTimestamp()
            }
        };
        
        Object.values(missionDefinitions).forEach(mission => {
            this.missions.set(mission.id, mission);
        });
    }
    
    updateMissionProgress(missionId, amount = 1) {
        const mission = this.missions.get(missionId);
        if (!mission || mission.completed) return;
        
        mission.current = Math.min(mission.current + amount, mission.target);
        
        // Check if mission completed
        if (mission.current >= mission.target) {
            this.completeMission(missionId);
        }
        
        // Update UI
        this.updateMissionUI(mission);
    }
    
    completeMission(missionId) {
        const mission = this.missions.get(missionId);
        if (!mission || mission.completed) return;
        
        mission.completed = true;
        mission.completedAt = Date.now();
        
        // Award XP
        this.gainXP(mission.reward);
        
        // Show completion notification
        this.showMissionComplete(mission);
        
        // Save to backend
        if (this.api) {
            this.api.apiCall('/gamification/mission-complete', 'POST', {
                mission_id: missionId,
                user_address: this.api.userAccount
            }).catch(console.error);
        }
    }
    
    showMissionComplete(mission) {
        const notification = document.createElement('div');
        notification.className = 'mission-complete fixed top-20 left-4 max-w-sm bg-gradient-to-r from-green-400 to-blue-500 text-white p-4 rounded-lg shadow-lg transform -translate-x-full transition-transform duration-300 z-50';
        notification.innerHTML = `
            <div class="flex items-center space-x-3">
                <i class="fas fa-check-circle text-2xl"></i>
                <div>
                    <div class="font-bold">Mission Complete!</div>
                    <div class="text-sm opacity-90">${mission.name} - +${mission.reward} XP</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(-100%)';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
    
    resetDailyMissions() {
        this.missions.forEach(mission => {
            if (mission.type === 'daily' && mission.expires <= Date.now()) {
                mission.current = 0;
                mission.completed = false;
                mission.expires = this.getTomorrowTimestamp();
            }
        });
    }
    
    startMissionTimer() {
        // Check for mission resets every hour
        setInterval(() => {
            this.resetDailyMissions();
            this.resetWeeklyMissions();
            this.resetMonthlyMissions();
        }, 60 * 60 * 1000);
    }
    
    // =============================================================================
    // LEADERBOARD SYSTEM
    // =============================================================================
    
    async loadLeaderboards() {
        try {
            const leaderboardData = await this.api?.apiCall('/gamification/leaderboards') || this.getMockLeaderboards();
            
            this.leaderboards.set('xp', leaderboardData.xp || []);
            this.leaderboards.set('staking', leaderboardData.staking || []);
            this.leaderboards.set('rental', leaderboardData.rental || []);
            this.leaderboards.set('referrals', leaderboardData.referrals || []);
            
        } catch (error) {
            console.error('Failed to load leaderboards:', error);
            this.leaderboards.set('xp', this.getMockLeaderboards().xp);
        }
    }
    
    getMockLeaderboards() {
        return {
            xp: [
                { rank: 1, address: '0x1234...5678', username: 'GPUMaster', score: 125000, badge: 'Champion' },
                { rank: 2, address: '0x2345...6789', username: 'StakeKing', score: 98500, badge: 'Legend' },
                { rank: 3, address: '0x3456...7890', username: 'RentalQueen', score: 87200, badge: 'Elite' },
                { rank: 4, address: '0x4567...8901', username: 'DiamondHands', score: 76800, badge: 'Master' },
                { rank: 5, address: '0x5678...9012', username: 'ComputeGod', score: 65400, badge: 'Expert' }
            ],
            staking: [
                { rank: 1, address: '0x1234...5678', username: 'WhaleWatcher', score: 5000000, badge: 'Leviathan' },
                { rank: 2, address: '0x2345...6789', username: 'DiamondTier', score: 3500000, badge: 'Diamond' },
                { rank: 3, address: '0x3456...7890', username: 'GoldRush', score: 1200000, badge: 'Gold' }
            ],
            rental: [
                { rank: 1, address: '0x1234...5678', username: 'ComputeFarm', score: 15000, badge: 'Industrial' },
                { rank: 2, address: '0x2345...6789', username: 'AITrainer', score: 12500, badge: 'Professional' },
                { rank: 3, address: '0x3456...7890', username: 'CloudMiner', score: 9800, badge: 'Advanced' }
            ],
            referrals: [
                { rank: 1, address: '0x1234...5678', username: 'NetworkGod', score: 847, badge: 'Influencer' },
                { rank: 2, address: '0x2345...6789', username: 'CommunityBuilder', score: 623, badge: 'Ambassador' },
                { rank: 3, address: '0x3456...7890', username: 'GrowthHacker', score: 445, badge: 'Recruiter' }
            ]
        };
    }
    
    async updateLeaderboardPosition(category, score) {
        if (!this.api?.userAccount) return;
        
        try {
            await this.api.apiCall('/gamification/leaderboard-update', 'POST', {
                category,
                score,
                user_address: this.api.userAccount
            });
            
            // Refresh leaderboards
            await this.loadLeaderboards();
            
        } catch (error) {
            console.error('Failed to update leaderboard:', error);
        }
    }
    
    // =============================================================================
    // XP & LEVEL SYSTEM
    // =============================================================================
    
    gainXP(amount) {
        const oldLevel = this.userLevel;
        this.userXP += amount;
        
        // Calculate new level
        this.userLevel = Math.floor(Math.sqrt(this.userXP / 100)) + 1;
        
        // Show XP gain notification
        this.showXPGain(amount);
        
        // Check for level up
        if (this.userLevel > oldLevel) {
            this.showLevelUp(oldLevel, this.userLevel);
            this.onLevelUp(this.userLevel);
        }
        
        // Update UI
        this.updateXPUI();
    }
    
    showXPGain(amount) {
        const notification = document.createElement('div');
        notification.className = 'xp-gain fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-yellow-400 to-orange-500 text-white px-6 py-3 rounded-full font-bold text-lg shadow-lg z-50';
        notification.textContent = `+${amount} XP`;
        
        document.body.appendChild(notification);
        
        // Animate
        notification.animate([
            { transform: 'translate(-50%, -50%) scale(0)', opacity: 0 },
            { transform: 'translate(-50%, -50%) scale(1.2)', opacity: 1 },
            { transform: 'translate(-50%, -200%) scale(1)', opacity: 0 }
        ], {
            duration: 2000,
            easing: 'ease-out'
        }).onfinish = () => notification.remove();
    }
    
    showLevelUp(oldLevel, newLevel) {
        const notification = document.createElement('div');
        notification.className = 'level-up fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        notification.innerHTML = `
            <div class="bg-gradient-to-r from-purple-500 to-pink-500 text-white p-8 rounded-2xl text-center transform scale-0 animate-bounce">
                <div class="text-6xl mb-4">🎉</div>
                <div class="text-3xl font-bold mb-2">LEVEL UP!</div>
                <div class="text-xl">Level ${oldLevel} → Level ${newLevel}</div>
                <div class="text-sm opacity-90 mt-2">New rewards unlocked!</div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.querySelector('div').style.transform = 'scale(1)';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    onLevelUp(level) {
        // Award level up rewards
        const levelRewards = {
            5: { type: 'tokens', amount: 1000 },
            10: { type: 'discount', amount: 5 },
            15: { type: 'tokens', amount: 2500 },
            20: { type: 'exclusive_access', feature: 'beta_features' },
            25: { type: 'tokens', amount: 5000 }
        };
        
        const reward = levelRewards[level];
        if (reward) {
            this.awardLevelReward(reward);
        }
        
        // Check for level-based achievements
        this.checkAchievement('power_user', level);
    }
    
    awardLevelReward(reward) {
        // Implementation for awarding level rewards
        console.log('Level reward awarded:', reward);
    }
    
    // =============================================================================
    // SOCIAL FEATURES
    // =============================================================================
    
    async shareAchievement(achievementId) {
        const achievement = this.achievements.get(achievementId);
        if (!achievement) return;
        
        const shareText = `🎉 I just unlocked "${achievement.name}" on @GPUDex! ${achievement.description} #GPUDex #Web3 #Achievement`;
        
        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'GPUDex Achievement Unlocked!',
                    text: shareText,
                    url: window.location.href
                });
                
                // Award sharing bonus
                this.gainXP(25);
                this.updateMissionProgress('social_share');
                
            } catch (error) {
                console.log('Share canceled');
            }
        } else {
            // Fallback to Twitter
            const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
            window.open(twitterUrl, '_blank');
        }
    }
    
    async processReferral(referrerAddress) {
        if (!this.api?.userAccount) return;
        
        try {
            await this.api.apiCall('/gamification/referral', 'POST', {
                referrer_address: referrerAddress,
                referee_address: this.api.userAccount
            });
            
            // Award referral achievement to referrer
            this.updateMissionProgress('weekly_referral');
            
        } catch (error) {
            console.error('Failed to process referral:', error);
        }
    }
    
    generateReferralLink() {
        if (!this.api?.userAccount) return '';
        
        const baseUrl = window.location.origin;
        return `${baseUrl}?ref=${this.api.userAccount}`;
    }
    
    // =============================================================================
    // UI MANAGEMENT
    // =============================================================================
    
    updateXPUI() {
        const xpElements = document.querySelectorAll('[data-user-xp]');
        xpElements.forEach(el => {
            el.textContent = this.userXP.toLocaleString();
        });
        
        const levelElements = document.querySelectorAll('[data-user-level]');
        levelElements.forEach(el => {
            el.textContent = this.userLevel;
        });
        
        // Update progress bar
        const nextLevelXP = Math.pow(this.userLevel, 2) * 100;
        const currentLevelXP = Math.pow(this.userLevel - 1, 2) * 100;
        const progressPercent = ((this.userXP - currentLevelXP) / (nextLevelXP - currentLevelXP)) * 100;
        
        const progressBars = document.querySelectorAll('[data-xp-progress]');
        progressBars.forEach(bar => {
            bar.style.width = `${Math.min(progressPercent, 100)}%`;
        });
    }
    
    updateMissionUI(mission) {
        const missionElement = document.querySelector(`[data-mission="${mission.id}"]`);
        if (missionElement) {
            const progressBar = missionElement.querySelector('.mission-progress');
            const progressText = missionElement.querySelector('.mission-text');
            
            if (progressBar) {
                const percent = (mission.current / mission.target) * 100;
                progressBar.style.width = `${percent}%`;
            }
            
            if (progressText) {
                progressText.textContent = `${mission.current}/${mission.target}`;
            }
            
            if (mission.completed) {
                missionElement.classList.add('completed');
            }
        }
    }
    
    renderAchievements(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const achievementCategories = {};
        this.achievements.forEach(achievement => {
            if (!achievementCategories[achievement.category]) {
                achievementCategories[achievement.category] = [];
            }
            achievementCategories[achievement.category].push(achievement);
        });
        
        container.innerHTML = Object.entries(achievementCategories).map(([category, achievements]) => `
            <div class="achievement-category mb-8">
                <h3 class="text-xl font-bold mb-4 capitalize text-gray-900 dark:text-white">${category}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${achievements.map(achievement => this.renderAchievementCard(achievement)).join('')}
                </div>
            </div>
        `).join('');
    }
    
    renderAchievementCard(achievement) {
        const rarityColors = {
            common: 'border-gray-400',
            uncommon: 'border-green-400',
            rare: 'border-blue-400',
            legendary: 'border-purple-400',
            mythical: 'border-pink-400'
        };
        
        return `
            <div class="achievement-card bg-white dark:bg-gray-800 rounded-lg p-4 border-2 ${rarityColors[achievement.rarity]} ${achievement.unlocked ? '' : 'opacity-50'}">
                <div class="flex items-center space-x-3 mb-3">
                    <div class="w-12 h-12 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center text-white">
                        <i class="${achievement.icon}"></i>
                    </div>
                    <div>
                        <div class="font-bold text-gray-900 dark:text-white">${achievement.name}</div>
                        <div class="text-xs text-${rarityColors[achievement.rarity].replace('border-', '')} font-semibold uppercase">${achievement.rarity}</div>
                    </div>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-300 mb-3">${achievement.description}</p>
                <div class="flex justify-between items-center">
                    <span class="text-yellow-500 font-semibold">+${achievement.reward} XP</span>
                    ${achievement.unlocked ? 
                        `<button onclick="gamificationSystem.shareAchievement('${achievement.id}')" class="text-blue-500 hover:text-blue-700">
                            <i class="fas fa-share"></i> Share
                        </button>` : 
                        '<span class="text-gray-400">Locked</span>'
                    }
                </div>
            </div>
        `;
    }
    
    renderLeaderboard(type, containerId) {
        const container = document.getElementById(containerId);
        const leaderboard = this.leaderboards.get(type);
        
        if (!container || !leaderboard) return;
        
        container.innerHTML = `
            <div class="leaderboard">
                <h3 class="text-xl font-bold mb-4 text-gray-900 dark:text-white capitalize">${type} Leaderboard</h3>
                <div class="space-y-2">
                    ${leaderboard.map((entry, index) => `
                        <div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg ${index < 3 ? 'border-l-4 border-yellow-400' : ''}">
                            <div class="flex items-center space-x-3">
                                <div class="w-8 h-8 ${index === 0 ? 'bg-yellow-400' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-400' : 'bg-gray-600'} rounded-full flex items-center justify-center text-white font-bold">
                                    ${entry.rank}
                                </div>
                                <div>
                                    <div class="font-semibold text-gray-900 dark:text-white">${entry.username}</div>
                                    <div class="text-xs text-gray-500">${entry.address}</div>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="font-bold text-gray-900 dark:text-white">${entry.score.toLocaleString()}</div>
                                <div class="text-xs text-gray-500">${entry.badge}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // =============================================================================
    // UTILITY METHODS
    // =============================================================================
    
    setupEventListeners() {
        // Listen for wallet connection
        if (this.api) {
            this.api.on('walletConnected', () => {
                this.checkAchievement('welcome');
            });
            
            this.api.on('stakingComplete', (event) => {
                const { amount } = event.detail;
                this.checkAchievement('first_stake');
                this.checkAchievement('bronze_tier', amount);
                this.checkAchievement('silver_tier', amount);
                this.checkAchievement('gold_tier', amount);
                this.checkAchievement('diamond_tier', amount);
                this.checkAchievement('whale', amount);
                this.updateMissionProgress('daily_stake');
                this.updateLeaderboardPosition('staking', amount);
            });
            
            this.api.on('rentalComplete', (event) => {
                const { hours } = event.detail;
                this.checkAchievement('first_rental');
                this.updateMissionProgress('weekly_rental', hours);
                this.updateLeaderboardPosition('rental', hours);
            });
        }
    }
    
    getTomorrowTimestamp() {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        return tomorrow.getTime();
    }
    
    getNextWeekTimestamp() {
        const nextWeek = new Date();
        nextWeek.setDate(nextWeek.getDate() + (7 - nextWeek.getDay()));
        nextWeek.setHours(0, 0, 0, 0);
        return nextWeek.getTime();
    }
    
    getNextMonthTimestamp() {
        const nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        nextMonth.setDate(1);
        nextMonth.setHours(0, 0, 0, 0);
        return nextMonth.getTime();
    }
    
    checkComboAchievements() {
        // Check for achievements that require multiple other achievements
        const unlockedCount = Array.from(this.achievements.values()).filter(a => a.unlocked).length;
        
        if (unlockedCount >= 10) {
            this.checkAchievement('achievement_hunter');
        }
        
        if (unlockedCount >= 25) {
            this.checkAchievement('completionist');
        }
    }
    
    playAchievementSound(rarity) {
        // Play achievement sound based on rarity
        // Implementation would depend on available audio system
        console.log(`Playing ${rarity} achievement sound`);
    }
    
    resetWeeklyMissions() {
        this.missions.forEach(mission => {
            if (mission.type === 'weekly' && mission.expires <= Date.now()) {
                mission.current = 0;
                mission.completed = false;
                mission.expires = this.getNextWeekTimestamp();
            }
        });
    }
    
    resetMonthlyMissions() {
        this.missions.forEach(mission => {
            if (mission.type === 'monthly' && mission.expires <= Date.now()) {
                mission.current = 0;
                mission.completed = false;
                mission.expires = this.getNextMonthTimestamp();
            }
        });
    }
}

// Global instance
let gamificationSystem = null;

// Initialize gamification system
document.addEventListener('DOMContentLoaded', () => {
    // Wait for API connector to be ready
    setTimeout(() => {
        if (window.gpudexConnector) {
            gamificationSystem = new GPUDexGamificationSystem(window.gpudexConnector);
            window.gamificationSystem = gamificationSystem;
            console.log('🎮 Gamification system initialized!');
        }
    }, 1000);
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GPUDexGamificationSystem;
} 