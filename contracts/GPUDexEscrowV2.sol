// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IGPUDexTokenV2 {
    function processGPURental(address _user, uint256 _amount) external returns (uint256 discountAmount);
    function processProviderEarnings(address _provider, uint256 _baseAmount) external returns (uint256 totalAmount);
    function awardSocialReward(address _user, string memory _activity, uint256 _amount) external;
    function processReferral(address _referrer, address _referee, uint256 _rewardAmount) external;
    function getUserTierInfo(address _user) external view returns (uint8 tier, uint256 stakedAmount, uint256 minStakeForNextTier, uint256 apyBasisPoints, uint256 gpuDiscountBasisPoints, uint256 providerBoostBasisPoints);
}

/**
 * @title GPUDexEscrowV2
 * @dev Enhanced escrow system with comprehensive utility validation and social gamification
 */
contract GPUDexEscrowV2 is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    
    // Rental states
    enum RentalState {
        Created,        // Initial state
        Funded,         // Payment deposited
        Active,         // GPU access provided
        Completed,      // Service delivered successfully
        Disputed,       // Dispute raised
        Resolved,       // Dispute resolved
        Cancelled,      // Rental cancelled
        Refunded        // Payment refunded
    }
    
    // GPU performance tiers
    enum GPUTier {
        BASIC,      // GTX/RTX 3060, etc.
        GAMING,     // RTX 3070/4060, etc.
        PRO,        // RTX 3080/4070, etc.
        ENTERPRISE, // RTX 4080/4090, A100, etc.
        DATACENTER  // H100, A100 clusters, etc.
    }
    
    struct Rental {
        uint256 rentalId;
        address renter;
        address provider;
        string gpuType;
        GPUTier gpuTier;
        uint256 pricePerHour;
        uint256 duration; // Duration in hours
        uint256 totalAmount;
        uint256 depositAmount;
        uint256 discountApplied; // GPUDX discount amount
        address paymentToken;
        RentalState state;
        uint256 createdAt;
        uint256 startedAt;
        uint256 completedAt;
        uint256 disputeDeadline;
        string providerEndpoint;
        string accessCredentials;
        bool autoRelease;
        uint256 performanceScore; // 1-100 rating
        bool paidWithGPUDX; // If rental was paid with GPUDX tokens
    }
    
    struct ProviderStats {
        uint256 totalRentals;
        uint256 totalEarnings;
        uint256 totalHours;
        uint256 averagePerformance;
        uint256 lastActiveAt;
        uint256 stakingTier;
        bool isVerified;
    }
    
    struct UserStats {
        uint256 totalSpent;
        uint256 totalHours;
        uint256 favoriteGPUTier;
        uint256 totalSavings; // From GPUDX discounts
        uint256 referralCount;
        uint256 socialPoints;
    }
    
    // State variables
    mapping(uint256 => Rental) public rentals;
    mapping(address => ProviderStats) public providerStats;
    mapping(address => UserStats) public userStats;
    mapping(address => uint256[]) public renterRentals;
    mapping(address => uint256[]) public providerRentals;
    mapping(address => bool) public authorizedArbitrators;
    
    uint256 public nextRentalId = 1;
    uint256 public platformFeePercent = 300; // 3% (300 basis points)
    uint256 public disputePeriod = 24 hours;
    uint256 public autoReleaseDelay = 48 hours;
    
    address public feeRecipient;
    IGPUDexTokenV2 public gpudexToken;
    
    // Utility validation metrics
    uint256 public totalRentalsProcessed;
    uint256 public totalVolumeProcessed;
    uint256 public totalDiscountsProvided;
    uint256 public totalGPUDXUtilization;
    uint256 public averageUserSatisfaction;
    
    // Social gamification
    mapping(string => uint256) public socialRewardRates; // activity => reward amount
    mapping(address => mapping(string => uint256)) public userAchievements;
    
    // Events
    event RentalCreated(
        uint256 indexed rentalId,
        address indexed renter,
        address indexed provider,
        string gpuType,
        uint256 totalAmount,
        uint256 discount
    );
    
    event RentalCompleted(
        uint256 indexed rentalId,
        uint256 performanceScore,
        uint256 providerEarnings,
        uint256 platformFee
    );
    
    event UtilityMetricsUpdated(
        uint256 totalRentals,
        uint256 totalVolume,
        uint256 totalDiscounts,
        uint256 utilizationRate
    );
    
    event SocialAchievementUnlocked(
        address indexed user,
        string achievement,
        uint256 rewardAmount
    );
    
    event ProviderVerified(address indexed provider, uint256 stakingTier);
    
    modifier onlyRenter(uint256 _rentalId) {
        require(rentals[_rentalId].renter == msg.sender, "Not the renter");
        _;
    }
    
    modifier onlyProvider(uint256 _rentalId) {
        require(rentals[_rentalId].provider == msg.sender, "Not the provider");
        _;
    }
    
    constructor(address _feeRecipient, address _gpudexToken) {
        feeRecipient = _feeRecipient;
        gpudexToken = IGPUDexTokenV2(_gpudexToken);
        authorizedArbitrators[msg.sender] = true;
        
        // Initialize social reward rates
        _initializeSocialRewards();
    }
    
    /**
     * @dev Initialize social reward rates for different activities
     */
    function _initializeSocialRewards() internal {
        socialRewardRates["first_rental"] = 50 * 10**18; // 50 GPUDX
        socialRewardRates["power_user"] = 200 * 10**18; // 200 GPUDX for 100+ hours
        socialRewardRates["loyal_customer"] = 100 * 10**18; // 100 GPUDX for 10+ rentals
        socialRewardRates["provider_debut"] = 75 * 10**18; // 75 GPUDX for first GPU listing
        socialRewardRates["high_rating"] = 25 * 10**18; // 25 GPUDX for 95%+ rating
        socialRewardRates["referral_bonus"] = 50 * 10**18; // 50 GPUDX per successful referral
    }
    
    /**
     * @dev Create a new GPU rental with enhanced features
     */
    function createRental(
        address _provider,
        string memory _gpuType,
        GPUTier _gpuTier,
        uint256 _pricePerHour,
        uint256 _duration,
        address _paymentToken,
        bool _autoRelease,
        bool _payWithGPUDX,
        address _referrer
    ) external returns (uint256) {
        require(_provider != address(0), "Invalid provider");
        require(_provider != msg.sender, "Cannot rent from yourself");
        require(_pricePerHour > 0, "Invalid price");
        require(_duration > 0, "Invalid duration");
        
        uint256 totalAmount = _pricePerHour * _duration;
        uint256 discountAmount = 0;
        
        // Apply GPUDX discount if user has tokens staked
        if (_payWithGPUDX) {
            discountAmount = gpudexToken.processGPURental(msg.sender, totalAmount);
            totalAmount -= discountAmount;
        }
        
        uint256 depositAmount = totalAmount + (totalAmount * 20 / 100); // 20% security deposit
        uint256 rentalId = nextRentalId++;
        
        rentals[rentalId] = Rental({
            rentalId: rentalId,
            renter: msg.sender,
            provider: _provider,
            gpuType: _gpuType,
            gpuTier: _gpuTier,
            pricePerHour: _pricePerHour,
            duration: _duration,
            totalAmount: totalAmount,
            depositAmount: depositAmount,
            discountApplied: discountAmount,
            paymentToken: _paymentToken,
            state: RentalState.Created,
            createdAt: block.timestamp,
            startedAt: 0,
            completedAt: 0,
            disputeDeadline: 0,
            providerEndpoint: "",
            accessCredentials: "",
            autoRelease: _autoRelease,
            performanceScore: 0,
            paidWithGPUDX: _payWithGPUDX
        });
        
        renterRentals[msg.sender].push(rentalId);
        providerRentals[_provider].push(rentalId);
        
        // Update metrics
        totalRentalsProcessed++;
        totalVolumeProcessed += (totalAmount + discountAmount);
        totalDiscountsProvided += discountAmount;
        if (_payWithGPUDX) totalGPUDXUtilization++;
        
        // Process referral if provided
        if (_referrer != address(0) && _referrer != msg.sender) {
            gpudexToken.processReferral(_referrer, msg.sender, socialRewardRates["referral_bonus"]);
            userStats[_referrer].referralCount++;
        }
        
        // Check for first rental achievement
        if (renterRentals[msg.sender].length == 1) {
            _awardAchievement(msg.sender, "first_rental");
        }
        
        emit RentalCreated(rentalId, msg.sender, _provider, _gpuType, totalAmount + discountAmount, discountAmount);
        
        return rentalId;
    }
    
    /**
     * @dev Fund a rental with payment
     */
    function fundRental(uint256 _rentalId) 
        external 
        onlyRenter(_rentalId)
        nonReentrant
    {
        Rental storage rental = rentals[_rentalId];
        require(rental.state == RentalState.Created, "Invalid state");
        
        // Transfer payment tokens to escrow
        IERC20(rental.paymentToken).safeTransferFrom(
            msg.sender,
            address(this),
            rental.depositAmount
        );
        
        rental.state = RentalState.Funded;
    }
    
    /**
     * @dev Provider starts the rental and provides access
     */
    function startRental(
        uint256 _rentalId,
        string memory _providerEndpoint,
        string memory _accessCredentials
    ) 
        external 
        onlyProvider(_rentalId)
    {
        Rental storage rental = rentals[_rentalId];
        require(rental.state == RentalState.Funded, "Not funded");
        
        rental.state = RentalState.Active;
        rental.startedAt = block.timestamp;
        rental.disputeDeadline = block.timestamp + disputePeriod;
        rental.providerEndpoint = _providerEndpoint;
        rental.accessCredentials = _accessCredentials;
        
        // Check if this is provider's first rental
        if (providerRentals[msg.sender].length == 1) {
            _awardAchievement(msg.sender, "provider_debut");
        }
    }
    
    /**
     * @dev Complete rental with performance rating
     */
    function completeRental(uint256 _rentalId, uint256 _performanceScore) 
        external
        onlyRenter(_rentalId)
        nonReentrant
    {
        require(_performanceScore >= 1 && _performanceScore <= 100, "Invalid performance score");
        
        Rental storage rental = rentals[_rentalId];
        require(rental.state == RentalState.Active, "Not active");
        
        rental.state = RentalState.Completed;
        rental.completedAt = block.timestamp;
        rental.performanceScore = _performanceScore;
        
        // Calculate and distribute payments
        uint256 platformFee = rental.totalAmount * platformFeePercent / 10000;
        uint256 baseProviderAmount = rental.totalAmount - platformFee;
        
        // Process provider earnings with potential boost
        uint256 finalProviderAmount = gpudexToken.processProviderEarnings(rental.provider, baseProviderAmount);
        
        // Transfer payments
        IERC20(rental.paymentToken).safeTransfer(rental.provider, finalProviderAmount);
        IERC20(rental.paymentToken).safeTransfer(feeRecipient, platformFee);
        
        // Refund security deposit
        uint256 refundAmount = rental.depositAmount - rental.totalAmount;
        IERC20(rental.paymentToken).safeTransfer(rental.renter, refundAmount);
        
        // Update stats
        _updateUserStats(rental.renter, rental);
        _updateProviderStats(rental.provider, rental.duration, _performanceScore);
        
        // Check for achievements
        _checkAchievements(rental.renter, rental.provider, _performanceScore);
        
        emit RentalCompleted(_rentalId, _performanceScore, finalProviderAmount, platformFee);
        emit UtilityMetricsUpdated(totalRentalsProcessed, totalVolumeProcessed, totalDiscountsProvided, (totalGPUDXUtilization * 100) / totalRentalsProcessed);
    }
    
    /**
     * @dev Update user statistics
     */
    function _updateUserStats(address _user, Rental memory _rental) internal {
        UserStats storage stats = userStats[_user];
        stats.totalSpent += (_rental.totalAmount + _rental.discountApplied);
        stats.totalHours += _rental.duration;
        stats.totalSavings += _rental.discountApplied;
        
        // Update favorite GPU tier (most used)
        stats.favoriteGPUTier = uint256(_rental.gpuTier);
    }
    
    /**
     * @dev Update provider statistics
     */
    function _updateProviderStats(address _provider, uint256 _hours, uint256 _performanceScore) internal {
        ProviderStats storage stats = providerStats[_provider];
        stats.totalRentals++;
        stats.totalHours += _hours;
        stats.totalEarnings += msg.value;
        
        // Update performance score (weighted average)
        if (stats.totalRentals == 1) {
            stats.averagePerformance = _performanceScore;
        } else {
            stats.averagePerformance = ((stats.averagePerformance * (stats.totalRentals - 1)) + _performanceScore) / stats.totalRentals;
        }
        
        stats.lastActiveAt = block.timestamp;
    }
    
    /**
     * @dev Check and award achievements
     */
    function _checkAchievements(address _renter, address _provider, uint256 _performanceScore) internal {
        UserStats storage renterStats = userStats[_renter];
        ProviderStats storage stats = providerStats[_provider];
        
        // Power user achievement (100+ hours)
        if (renterStats.totalHours >= 100 && userAchievements[_renter]["power_user"] == 0) {
            _awardAchievement(_renter, "power_user");
        }
        
        // Loyal customer (10+ rentals)
        if (renterRentals[_renter].length >= 10 && userAchievements[_renter]["loyal_customer"] == 0) {
            _awardAchievement(_renter, "loyal_customer");
        }
        
        // High-rating provider (95%+ average rating with 5+ rentals)
        if (stats.averagePerformance >= 95 && stats.totalRentals >= 5 && userAchievements[_provider]["high_rating"] == 0) {
            _awardAchievement(_provider, "high_rating");
        }
    }
    
    /**
     * @dev Award achievement to user
     */
    function _awardAchievement(address _user, string memory _achievement) internal {
        uint256 rewardAmount = socialRewardRates[_achievement];
        if (rewardAmount > 0) {
            userAchievements[_user][_achievement] = block.timestamp;
            userStats[_user].socialPoints += rewardAmount;
            
            gpudexToken.awardSocialReward(_user, _achievement, rewardAmount);
            emit SocialAchievementUnlocked(_user, _achievement, rewardAmount);
        }
    }
    
    /**
     * @dev Verify provider with staking requirement check
     */
    function verifyProvider(address _provider) external onlyOwner {
        (uint8 tier,,,,,) = gpudexToken.getUserTierInfo(_provider);
        require(tier > 0, "Provider must stake GPUDX tokens");
        
        providerStats[_provider].isVerified = true;
        providerStats[_provider].stakingTier = tier;
        
        emit ProviderVerified(_provider, tier);
    }
    
    /**
     * @dev Get comprehensive platform metrics for utility validation
     */
    function getPlatformMetrics() external view returns (
        uint256 totalRentals,
        uint256 totalVolume,
        uint256 totalDiscounts,
        uint256 gpudxUtilizationRate,
        uint256 avgSatisfaction,
        uint256 verifiedProviders,
        uint256 activeUsers
    ) {
        totalRentals = totalRentalsProcessed;
        totalVolume = totalVolumeProcessed;
        totalDiscounts = totalDiscountsProvided;
        gpudxUtilizationRate = totalRentalsProcessed > 0 ? (totalGPUDXUtilization * 100) / totalRentalsProcessed : 0;
        avgSatisfaction = averageUserSatisfaction;
        
        // Count verified providers and active users (simplified)
        // In production, these would be tracked more efficiently
        verifiedProviders = 0; // Would need separate tracking
        activeUsers = totalRentalsProcessed; // Simplified metric
    }
    
    /**
     * @dev Get user achievement status
     */
    function getUserAchievements(address _user) external view returns (
        uint256 firstRental,
        uint256 powerUser,
        uint256 loyalCustomer,
        uint256 providerDebut,
        uint256 highRating,
        uint256 socialPoints
    ) {
        firstRental = userAchievements[_user]["first_rental"];
        powerUser = userAchievements[_user]["power_user"];
        loyalCustomer = userAchievements[_user]["loyal_customer"];
        providerDebut = userAchievements[_user]["provider_debut"];
        highRating = userAchievements[_user]["high_rating"];
        socialPoints = userStats[_user].socialPoints;
    }
    
    /**
     * @dev Update social reward rates
     */
    function updateSocialRewardRate(string memory _activity, uint256 _rewardAmount) external onlyOwner {
        socialRewardRates[_activity] = _rewardAmount;
    }
    
    /**
     * @dev Update platform fee
     */
    function updatePlatformFee(uint256 _feePercent) external onlyOwner {
        require(_feePercent <= 1000, "Fee too high"); // Max 10%
        platformFeePercent = _feePercent;
    }
    
    /**
     * @dev Get rental details
     */
    function getRental(uint256 _rentalId) external view returns (Rental memory) {
        return rentals[_rentalId];
    }
    
    /**
     * @dev Get user statistics
     */
    function getUserStats(address _user) external view returns (UserStats memory) {
        return userStats[_user];
    }
    
    /**
     * @dev Get provider statistics
     */
    function getProviderStats(address _provider) external view returns (ProviderStats memory) {
        return providerStats[_provider];
    }
} 