// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title GPUDexTokenV2 (GPUDX)
 * @dev Utility-focused platform token with tiered staking and comprehensive rewards
 * NO GOVERNANCE - Pure utility and value accrual focus
 */
contract GPUDexTokenV2 is ERC20, ERC20Burnable, Pausable, Ownable, ERC20Permit, ReentrancyGuard {
    
    // Token distribution
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens
    uint256 public constant TEAM_ALLOCATION = 150_000_000 * 10**18; // 15%
    uint256 public constant TREASURY_ALLOCATION = 100_000_000 * 10**18; // 10%
    uint256 public constant USER_REWARDS_ALLOCATION = 300_000_000 * 10**18; // 30%
    uint256 public constant PROVIDER_INCENTIVES_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant ENTERPRISE_CASHBACK_ALLOCATION = 100_000_000 * 10**18; // 10%
    uint256 public constant ECOSYSTEM_RESERVE_ALLOCATION = 150_000_000 * 10**18; // 15%
    
    // Staking tiers
    enum StakingTier { NONE, BRONZE, SILVER, GOLD, DIAMOND }
    
    struct StakingInfo {
        uint256 amount;
        uint256 rewardDebt;
        uint256 feeDebt;
        uint256 stakedAt;
        uint256 lockUntil;
        StakingTier tier;
        uint256 lastClaimTime;
        uint256 totalRewardsClaimed;
        uint256 totalFeesClaimed;
    }
    
    struct TierConfig {
        uint256 minStake;
        uint256 apyBasisPoints; // APY in basis points (100 = 1%)
        uint256 gpuDiscountBasisPoints; // Discount in basis points
        uint256 providerBoostBasisPoints; // Provider earnings boost
        uint256 revenueShareBasisPoints; // Revenue share (Diamond only)
    }
    
    // Staking and rewards
    mapping(address => StakingInfo) public stakingInfo;
    mapping(address => bool) public isProvider;
    mapping(StakingTier => TierConfig) public tierConfigs;
    
    uint256 public totalStaked;
    uint256 public accRewardPerShare;
    uint256 public lastRewardDistribution;
    
    // Fee distribution
    uint256 public totalFeesCollected;
    uint256 public accFeePerShare;
    
    // Platform integration
    mapping(address => uint256) public userGPURentals; // Total GPU spending
    mapping(address => uint256) public providerEarnings; // Provider earnings
    mapping(address => uint256) public socialRewards; // Social activity rewards
    mapping(address => address) public referrals; // Referral tracking
    
    // Utility metrics
    uint256 public totalGPUSpending;
    uint256 public totalProviderEarnings;
    uint256 public totalUsersServed;
    uint256 public platformRevenueGenerated;
    
    // Events
    event Staked(address indexed user, uint256 amount, uint256 lockDays, StakingTier tier);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    event FeesClaimed(address indexed user, uint256 amount);
    event TierUpgraded(address indexed user, StakingTier oldTier, StakingTier newTier);
    event ProviderRegistered(address indexed provider, StakingTier tier);
    event ProviderUnregistered(address indexed provider);
    event RevenueDistributed(uint256 rewardAmount, uint256 feeAmount);
    event GPURentalDiscount(address indexed user, uint256 originalAmount, uint256 discountAmount);
    event ProviderEarningsBoost(address indexed provider, uint256 originalAmount, uint256 boostAmount);
    event SocialRewardEarned(address indexed user, string activity, uint256 amount);
    event ReferralReward(address indexed referrer, address indexed referee, uint256 amount);
    
    constructor(address _initialOwner) 
        ERC20("GPUDex Token V2", "GPUDX") 
        ERC20Permit("GPUDex Token V2")
        Ownable()
    {
        _transferOwnership(_initialOwner);
        
        // Initialize tier configurations
        _setupTierConfigs();
        
        // Initial minting
        _mint(_initialOwner, TEAM_ALLOCATION);
        _mint(_initialOwner, TREASURY_ALLOCATION);
        _mint(address(this), USER_REWARDS_ALLOCATION + PROVIDER_INCENTIVES_ALLOCATION + ENTERPRISE_CASHBACK_ALLOCATION);
        
        lastRewardDistribution = block.timestamp;
    }
    
    /**
     * @dev Setup staking tier configurations
     */
    function _setupTierConfigs() internal {
        // Bronze: 1K tokens, 8% APY, 5% GPU discount, 5% provider boost
        tierConfigs[StakingTier.BRONZE] = TierConfig({
            minStake: 1_000 * 10**18,
            apyBasisPoints: 800,
            gpuDiscountBasisPoints: 500,
            providerBoostBasisPoints: 500,
            revenueShareBasisPoints: 0
        });
        
        // Silver: 10K tokens, 12% APY, 10% GPU discount, 10% provider boost
        tierConfigs[StakingTier.SILVER] = TierConfig({
            minStake: 10_000 * 10**18,
            apyBasisPoints: 1200,
            gpuDiscountBasisPoints: 1000,
            providerBoostBasisPoints: 1000,
            revenueShareBasisPoints: 0
        });
        
        // Gold: 100K tokens, 15% APY, 15% GPU discount, 15% provider boost
        tierConfigs[StakingTier.GOLD] = TierConfig({
            minStake: 100_000 * 10**18,
            apyBasisPoints: 1500,
            gpuDiscountBasisPoints: 1500,
            providerBoostBasisPoints: 1500,
            revenueShareBasisPoints: 0
        });
        
        // Diamond: 1M tokens, 20% APY, 20% GPU discount, 20% provider boost, 1% revenue share
        tierConfigs[StakingTier.DIAMOND] = TierConfig({
            minStake: 1_000_000 * 10**18,
            apyBasisPoints: 2000,
            gpuDiscountBasisPoints: 2000,
            providerBoostBasisPoints: 2000,
            revenueShareBasisPoints: 100
        });
    }
    
    /**
     * @dev Stake tokens for utility benefits and rewards
     */
    function stake(uint256 _amount, uint256 _lockDays) external whenNotPaused nonReentrant {
        require(_amount > 0, "Cannot stake 0");
        require(_lockDays <= 365, "Lock period too long");
        
        StakingInfo storage user = stakingInfo[msg.sender];
        
        // Claim any pending rewards
        if (user.amount > 0) {
            _claimRewards(msg.sender);
            _claimFees(msg.sender);
        }
        
        // Transfer tokens to contract
        _transfer(msg.sender, address(this), _amount);
        
        // Update staking info
        user.amount += _amount;
        user.stakedAt = block.timestamp;
        user.lockUntil = block.timestamp + (_lockDays * 1 days);
        user.lastClaimTime = block.timestamp;
        
        // Update reward and fee debt
        user.rewardDebt = (user.amount * accRewardPerShare) / 1e12;
        user.feeDebt = (user.amount * accFeePerShare) / 1e12;
        
        totalStaked += _amount;
        
        // Determine and upgrade tier
        StakingTier newTier = _calculateTier(user.amount);
        StakingTier oldTier = user.tier;
        user.tier = newTier;
        
        if (newTier != oldTier) {
            emit TierUpgraded(msg.sender, oldTier, newTier);
        }
        
        emit Staked(msg.sender, _amount, _lockDays, newTier);
    }
    
    /**
     * @dev Unstake tokens (respects lock period)
     */
    function unstake(uint256 _amount) external nonReentrant {
        StakingInfo storage user = stakingInfo[msg.sender];
        require(user.amount >= _amount, "Insufficient staked amount");
        require(block.timestamp >= user.lockUntil, "Tokens still locked");
        
        // Claim pending rewards and fees
        _claimRewards(msg.sender);
        _claimFees(msg.sender);
        
        // Update staking info
        user.amount -= _amount;
        totalStaked -= _amount;
        
        // Recalculate tier
        StakingTier newTier = _calculateTier(user.amount);
        StakingTier oldTier = user.tier;
        user.tier = newTier;
        
        // Update debt
        user.rewardDebt = (user.amount * accRewardPerShare) / 1e12;
        user.feeDebt = (user.amount * accFeePerShare) / 1e12;
        
        // Transfer tokens back to user
        _transfer(address(this), msg.sender, _amount);
        
        if (newTier != oldTier) {
            emit TierUpgraded(msg.sender, oldTier, newTier);
        }
        
        emit Unstaked(msg.sender, _amount);
    }
    
    /**
     * @dev Calculate user's staking tier based on amount
     */
    function _calculateTier(uint256 _amount) internal view returns (StakingTier) {
        if (_amount >= tierConfigs[StakingTier.DIAMOND].minStake) return StakingTier.DIAMOND;
        if (_amount >= tierConfigs[StakingTier.GOLD].minStake) return StakingTier.GOLD;
        if (_amount >= tierConfigs[StakingTier.SILVER].minStake) return StakingTier.SILVER;
        if (_amount >= tierConfigs[StakingTier.BRONZE].minStake) return StakingTier.BRONZE;
        return StakingTier.NONE;
    }
    
    /**
     * @dev Process GPU rental payment with tier-based discount
     */
    function processGPURental(address _user, uint256 _amount) external onlyOwner returns (uint256 discountAmount) {
        StakingInfo storage user = stakingInfo[_user];
        
        if (user.tier != StakingTier.NONE) {
            uint256 discountBasisPoints = tierConfigs[user.tier].gpuDiscountBasisPoints;
            discountAmount = (_amount * discountBasisPoints) / 10000;
            
            // Track metrics
            userGPURentals[_user] += _amount;
            totalGPUSpending += _amount;
            totalUsersServed++;
            
            emit GPURentalDiscount(_user, _amount, discountAmount);
        }
        
        return discountAmount;
    }
    
    /**
     * @dev Process provider earnings with tier-based boost
     */
    function processProviderEarnings(address _provider, uint256 _baseAmount) external onlyOwner returns (uint256 totalAmount) {
        require(isProvider[_provider], "Not a registered provider");
        
        StakingInfo storage provider = stakingInfo[_provider];
        totalAmount = _baseAmount;
        
        if (provider.tier != StakingTier.NONE) {
            uint256 boostBasisPoints = tierConfigs[provider.tier].providerBoostBasisPoints;
            uint256 boostAmount = (_baseAmount * boostBasisPoints) / 10000;
            totalAmount = _baseAmount + boostAmount;
            
            // Mint boost tokens (from provider incentives allocation)
            if (balanceOf(address(this)) >= boostAmount) {
                _transfer(address(this), _provider, boostAmount);
            }
            
            emit ProviderEarningsBoost(_provider, _baseAmount, boostAmount);
        }
        
        // Track metrics
        providerEarnings[_provider] += totalAmount;
        totalProviderEarnings += totalAmount;
        
        return totalAmount;
    }
    
    /**
     * @dev Register as GPU provider (requires minimum staking)
     */
    function registerProvider() external {
        StakingInfo storage user = stakingInfo[msg.sender];
        require(user.tier >= StakingTier.BRONZE, "Must stake minimum amount to be provider");
        require(!isProvider[msg.sender], "Already registered as provider");
        
        isProvider[msg.sender] = true;
        emit ProviderRegistered(msg.sender, user.tier);
    }
    
    /**
     * @dev Unregister as provider
     */
    function unregisterProvider() external {
        require(isProvider[msg.sender], "Not a registered provider");
        isProvider[msg.sender] = false;
        emit ProviderUnregistered(msg.sender);
    }
    
    /**
     * @dev Distribute platform revenue to stakers and fee collectors
     */
    function distributeRevenue(uint256 _rewardAmount, uint256 _feeAmount) external onlyOwner {
        require(_rewardAmount > 0 || _feeAmount > 0, "No revenue to distribute");
        require(totalStaked > 0, "No stakers to distribute to");
        
        if (_rewardAmount > 0) {
            // Transfer reward tokens to contract for distribution
            _transfer(msg.sender, address(this), _rewardAmount);
            accRewardPerShare += (_rewardAmount * 1e12) / totalStaked;
        }
        
        if (_feeAmount > 0) {
            // Transfer fee tokens to contract for distribution
            _transfer(msg.sender, address(this), _feeAmount);
            accFeePerShare += (_feeAmount * 1e12) / totalStaked;
            totalFeesCollected += _feeAmount;
        }
        
        platformRevenueGenerated += (_rewardAmount + _feeAmount);
        lastRewardDistribution = block.timestamp;
        
        emit RevenueDistributed(_rewardAmount, _feeAmount);
    }
    
    /**
     * @dev Claim staking rewards
     */
    function claimRewards() external nonReentrant {
        _claimRewards(msg.sender);
    }
    
    /**
     * @dev Internal function to claim rewards
     */
    function _claimRewards(address _user) internal {
        StakingInfo storage user = stakingInfo[_user];
        require(user.amount > 0, "No staked tokens");
        
        uint256 pending = ((user.amount * accRewardPerShare) / 1e12) - user.rewardDebt;
        
        if (pending > 0) {
            // Add tier-based APY calculation
            uint256 timeStaked = block.timestamp - user.lastClaimTime;
            uint256 apyReward = 0;
            
            if (user.tier != StakingTier.NONE) {
                uint256 apyBasisPoints = tierConfigs[user.tier].apyBasisPoints;
                apyReward = (user.amount * apyBasisPoints * timeStaked) / (10000 * 365 days);
            }
            
            uint256 totalReward = pending + apyReward;
            
            // Ensure we have enough tokens to distribute
            if (balanceOf(address(this)) >= totalReward) {
                user.rewardDebt = (user.amount * accRewardPerShare) / 1e12;
                user.lastClaimTime = block.timestamp;
                user.totalRewardsClaimed += totalReward;
                
                _transfer(address(this), _user, totalReward);
                emit RewardsClaimed(_user, totalReward);
            }
        }
    }
    
    /**
     * @dev Claim fee share
     */
    function claimFees() external nonReentrant {
        _claimFees(msg.sender);
    }
    
    /**
     * @dev Internal function to claim fees
     */
    function _claimFees(address _user) internal {
        StakingInfo storage user = stakingInfo[_user];
        require(user.amount > 0, "No staked tokens");
        
        uint256 pending = ((user.amount * accFeePerShare) / 1e12) - user.feeDebt;
        
        if (pending > 0) {
            user.feeDebt = (user.amount * accFeePerShare) / 1e12;
            user.totalFeesClaimed += pending;
            
            _transfer(address(this), _user, pending);
            emit FeesClaimed(_user, pending);
        }
    }
    
    /**
     * @dev Award social activity rewards
     */
    function awardSocialReward(address _user, string memory _activity, uint256 _amount) external onlyOwner {
        require(_amount > 0, "Invalid reward amount");
        require(balanceOf(address(this)) >= _amount, "Insufficient reward tokens");
        
        socialRewards[_user] += _amount;
        _transfer(address(this), _user, _amount);
        
        emit SocialRewardEarned(_user, _activity, _amount);
    }
    
    /**
     * @dev Process referral reward
     */
    function processReferral(address _referrer, address _referee, uint256 _rewardAmount) external onlyOwner {
        require(_referrer != address(0) && _referee != address(0), "Invalid addresses");
        require(referrals[_referee] == address(0), "Referee already has referrer");
        require(_referrer != _referee, "Cannot refer yourself");
        
        referrals[_referee] = _referrer;
        
        if (_rewardAmount > 0 && balanceOf(address(this)) >= _rewardAmount) {
            _transfer(address(this), _referrer, _rewardAmount);
            emit ReferralReward(_referrer, _referee, _rewardAmount);
        }
    }
    
    /**
     * @dev Get user's tier information
     */
    function getUserTierInfo(address _user) external view returns (
        StakingTier tier,
        uint256 stakedAmount,
        uint256 minStakeForNextTier,
        uint256 apyBasisPoints,
        uint256 gpuDiscountBasisPoints,
        uint256 providerBoostBasisPoints
    ) {
        StakingInfo storage user = stakingInfo[_user];
        tier = user.tier;
        stakedAmount = user.amount;
        
        if (tier == StakingTier.DIAMOND) {
            minStakeForNextTier = 0; // Already at max tier
        } else {
            StakingTier nextTier = StakingTier(uint256(tier) + 1);
            minStakeForNextTier = tierConfigs[nextTier].minStake;
        }
        
        if (tier != StakingTier.NONE) {
            TierConfig storage config = tierConfigs[tier];
            apyBasisPoints = config.apyBasisPoints;
            gpuDiscountBasisPoints = config.gpuDiscountBasisPoints;
            providerBoostBasisPoints = config.providerBoostBasisPoints;
        }
    }
    
    /**
     * @dev Get pending rewards for user
     */
    function pendingRewards(address _user) external view returns (uint256 platformRewards, uint256 apyRewards, uint256 fees) {
        StakingInfo storage user = stakingInfo[_user];
        
        // Platform rewards
        platformRewards = ((user.amount * accRewardPerShare) / 1e12) - user.rewardDebt;
        
        // APY rewards
        if (user.tier != StakingTier.NONE) {
            uint256 timeStaked = block.timestamp - user.lastClaimTime;
            uint256 apyBasisPoints = tierConfigs[user.tier].apyBasisPoints;
            apyRewards = (user.amount * apyBasisPoints * timeStaked) / (10000 * 365 days);
        }
        
        // Fee rewards
        fees = ((user.amount * accFeePerShare) / 1e12) - user.feeDebt;
    }
    
    /**
     * @dev Get platform utility metrics
     */
    function getUtilityMetrics() external view returns (
        uint256 totalGPUSpendingValue,
        uint256 totalProviderEarningsValue,
        uint256 totalUsersServedCount,
        uint256 platformRevenueGeneratedValue,
        uint256 totalStakedTokens,
        uint256 utilityTokenPercentage
    ) {
        totalGPUSpendingValue = totalGPUSpending;
        totalProviderEarningsValue = totalProviderEarnings;
        totalUsersServedCount = totalUsersServed;
        platformRevenueGeneratedValue = platformRevenueGenerated;
        totalStakedTokens = totalStaked;
        utilityTokenPercentage = totalSupply() > 0 ? (totalStaked * 100) / totalSupply() : 0;
    }
    
    /**
     * @dev Update tier configuration (owner only)
     */
    function updateTierConfig(
        StakingTier _tier,
        uint256 _minStake,
        uint256 _apyBasisPoints,
        uint256 _gpuDiscountBasisPoints,
        uint256 _providerBoostBasisPoints,
        uint256 _revenueShareBasisPoints
    ) external onlyOwner {
        require(_tier != StakingTier.NONE, "Cannot configure NONE tier");
        require(_apyBasisPoints <= 5000, "APY too high"); // Max 50%
        require(_gpuDiscountBasisPoints <= 3000, "Discount too high"); // Max 30%
        require(_providerBoostBasisPoints <= 3000, "Boost too high"); // Max 30%
        require(_revenueShareBasisPoints <= 500, "Revenue share too high"); // Max 5%
        
        tierConfigs[_tier] = TierConfig({
            minStake: _minStake,
            apyBasisPoints: _apyBasisPoints,
            gpuDiscountBasisPoints: _gpuDiscountBasisPoints,
            providerBoostBasisPoints: _providerBoostBasisPoints,
            revenueShareBasisPoints: _revenueShareBasisPoints
        });
    }
    
    /**
     * @dev Emergency pause
     */
    function pause() public onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause
     */
    function unpause() public onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Required override for pausable transfers
     */
    function _beforeTokenTransfer(address from, address to, uint256 amount)
        internal
        whenNotPaused
        override
    {
        super._beforeTokenTransfer(from, to, amount);
    }
} 