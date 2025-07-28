// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IGPUDexTokenV2 {
    function processGPURental(address _user, uint256 _amount) external returns (uint256 discountAmount);
    function getUserTierInfo(address _user) external view returns (uint8 tier, uint256 stakedAmount, uint256 minStakeForNextTier, uint256 apyBasisPoints, uint256 gpuDiscountBasisPoints, uint256 providerBoostBasisPoints);
    function distributeRevenue(uint256 _rewardAmount, uint256 _feeAmount) external;
}

/**
 * @title GPUDexEnterpriseV2
 * @dev Enterprise-focused contract for B2B client management and revenue optimization
 */
contract GPUDexEnterpriseV2 is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Enterprise client tiers
    enum EnterpriseTier { STARTUP, GROWTH, PROFESSIONAL, ENTERPRISE, PLATINUM }

    // Contract types
    enum ContractType { PAYPERUSE, MONTHLY, QUARTERLY, ANNUAL, CUSTOM }

    struct EnterpriseClient {
        address clientAddress;
        string companyName;
        string contactEmail;
        EnterpriseTier tier;
        ContractType contractType;
        uint256 volumeDiscount; // Basis points (100 = 1%)
        uint256 monthlyCommitment; // Minimum monthly spend in USD
        uint256 totalSpent;
        uint256 totalHours;
        uint256 joinedAt;
        bool isActive;
        bool hasCustomPricing;
        uint256 customPricePerHour; // Custom rate in wei
    }

    struct InstitutionalStaking {
        address institution;
        uint256 stakedAmount;
        uint256 lockPeriod; // In days
        uint256 customAPY; // Basis points
        uint256 stakedAt;
        uint256 lockedUntil;
        bool isActive;
        string institutionName;
        uint256 minimumStake;
    }

    struct RevenueShare {
        address recipient;
        uint256 sharePercentage; // Basis points
        uint256 totalReceived;
        bool isActive;
    }

    // State variables
    mapping(address => EnterpriseClient) public enterpriseClients;
    mapping(address => InstitutionalStaking) public institutionalStaking;
    mapping(address => RevenueShare) public revenueShares;
    
    address[] public clientList;
    address[] public institutionList;
    
    IGPUDexTokenV2 public gpudexToken;
    
    // Platform metrics
    uint256 public totalEnterpriseRevenue;
    uint256 public totalInstitutionalStaked;
    uint256 public activeEnterpriseClients;
    uint256 public totalRevenueShared;
    
    // Pricing configuration
    mapping(EnterpriseTier => uint256) public tierDiscounts; // Basis points
    mapping(EnterpriseTier => uint256) public tierMinimums; // Minimum monthly spend
    
    uint256 public baseGPUPricePerHour = 50000000000000000; // 0.05 ETH base price
    uint256 public platformFeePercent = 300; // 3%
    uint256 public maxVolumeDiscount = 5000; // 50% max discount
    
    // Events
    event EnterpriseClientRegistered(address indexed client, string companyName, EnterpriseTier tier);
    event ContractUpgraded(address indexed client, EnterpriseTier oldTier, EnterpriseTier newTier);
    event InstitutionalStakingCreated(address indexed institution, uint256 amount, uint256 customAPY);
    event EnterpriseRentalProcessed(address indexed client, uint256 amount, uint256 discount, uint256 rentalHours);
    event RevenueShareDistributed(address indexed recipient, uint256 amount);
    event CustomPricingSet(address indexed client, uint256 customPrice);

    constructor(address _gpudexToken) {
        gpudexToken = IGPUDexTokenV2(_gpudexToken);
        
        // Initialize tier discounts
        tierDiscounts[EnterpriseTier.STARTUP] = 500;     // 5%
        tierDiscounts[EnterpriseTier.GROWTH] = 1000;     // 10%
        tierDiscounts[EnterpriseTier.PROFESSIONAL] = 1500; // 15%
        tierDiscounts[EnterpriseTier.ENTERPRISE] = 2000;   // 20%
        tierDiscounts[EnterpriseTier.PLATINUM] = 3000;     // 30%
        
        // Initialize tier minimums (in USD, scaled by 1e18)
        tierMinimums[EnterpriseTier.STARTUP] = 1000 * 1e18;      // $1,000
        tierMinimums[EnterpriseTier.GROWTH] = 5000 * 1e18;       // $5,000
        tierMinimums[EnterpriseTier.PROFESSIONAL] = 25000 * 1e18; // $25,000
        tierMinimums[EnterpriseTier.ENTERPRISE] = 100000 * 1e18;  // $100,000
        tierMinimums[EnterpriseTier.PLATINUM] = 500000 * 1e18;    // $500,000
    }

    /**
     * @dev Register a new enterprise client
     */
    function registerEnterpriseClient(
        string memory _companyName,
        string memory _contactEmail,
        EnterpriseTier _tier,
        ContractType _contractType
    ) external returns (bool) {
        require(!enterpriseClients[msg.sender].isActive, "Client already registered");
        require(bytes(_companyName).length > 0, "Company name required");
        
        enterpriseClients[msg.sender] = EnterpriseClient({
            clientAddress: msg.sender,
            companyName: _companyName,
            contactEmail: _contactEmail,
            tier: _tier,
            contractType: _contractType,
            volumeDiscount: tierDiscounts[_tier],
            monthlyCommitment: tierMinimums[_tier],
            totalSpent: 0,
            totalHours: 0,
            joinedAt: block.timestamp,
            isActive: true,
            hasCustomPricing: false,
            customPricePerHour: 0
        });
        
        clientList.push(msg.sender);
        activeEnterpriseClients++;
        
        emit EnterpriseClientRegistered(msg.sender, _companyName, _tier);
        return true;
    }

    /**
     * @dev Process enterprise GPU rental with custom pricing
     */
    function processEnterpriseRental(
        address _client,
        uint256 _hours,
        string memory _gpuType
    ) external onlyOwner nonReentrant returns (uint256 totalCost, uint256 discount) {
        require(enterpriseClients[_client].isActive, "Client not active");
        
        EnterpriseClient storage client = enterpriseClients[_client];
        
        // Calculate base cost
        uint256 baseCost = client.hasCustomPricing ? 
            client.customPricePerHour * _hours : 
            baseGPUPricePerHour * _hours;
        
        // Apply enterprise tier discount
        discount = (baseCost * client.volumeDiscount) / 10000;
        
        // Apply additional GPUDX token discount if client has staked tokens
        uint256 additionalDiscount = gpudexToken.processGPURental(_client, baseCost - discount);
        discount += additionalDiscount;
        
        totalCost = baseCost - discount;
        
        // Update client statistics
        client.totalSpent += totalCost;
        client.totalHours += _hours;
        totalEnterpriseRevenue += totalCost;
        
        // Check for tier upgrade eligibility
        _checkTierUpgrade(_client);
        
        emit EnterpriseRentalProcessed(_client, totalCost, discount, _hours);
        
        return (totalCost, discount);
    }

    /**
     * @dev Create institutional staking program
     */
    function createInstitutionalStaking(
        address _institution,
        string memory _institutionName,
        uint256 _customAPY,
        uint256 _lockPeriodDays,
        uint256 _minimumStake
    ) external onlyOwner {
        require(_customAPY <= 10000, "APY too high"); // Max 100%
        require(_lockPeriodDays >= 30, "Minimum 30 days lock");
        require(_minimumStake >= 100000 * 10**18, "Minimum 100K tokens"); // 100K GPUDX minimum
        
        institutionalStaking[_institution] = InstitutionalStaking({
            institution: _institution,
            stakedAmount: 0,
            lockPeriod: _lockPeriodDays,
            customAPY: _customAPY,
            stakedAt: 0,
            lockedUntil: 0,
            isActive: true,
            institutionName: _institutionName,
            minimumStake: _minimumStake
        });
        
        institutionList.push(_institution);
        
        emit InstitutionalStakingCreated(_institution, _minimumStake, _customAPY);
    }

    /**
     * @dev Institution stakes tokens with custom terms
     */
    function stakeInstitutional(uint256 _amount) external nonReentrant {
        InstitutionalStaking storage staking = institutionalStaking[msg.sender];
        require(staking.isActive, "Institution not registered");
        require(_amount >= staking.minimumStake, "Below minimum stake");
        
        // Transfer tokens to this contract
        IERC20(address(gpudexToken)).safeTransferFrom(msg.sender, address(this), _amount);
        
        staking.stakedAmount += _amount;
        staking.stakedAt = block.timestamp;
        staking.lockedUntil = block.timestamp + (staking.lockPeriod * 1 days);
        
        totalInstitutionalStaked += _amount;
    }

    /**
     * @dev Set custom pricing for enterprise client
     */
    function setCustomPricing(address _client, uint256 _customPricePerHour) external onlyOwner {
        require(enterpriseClients[_client].isActive, "Client not active");
        require(_customPricePerHour > 0, "Invalid price");
        
        enterpriseClients[_client].hasCustomPricing = true;
        enterpriseClients[_client].customPricePerHour = _customPricePerHour;
        
        emit CustomPricingSet(_client, _customPricePerHour);
    }

    /**
     * @dev Setup revenue sharing for partners
     */
    function setupRevenueShare(address _recipient, uint256 _sharePercentage) external onlyOwner {
        require(_sharePercentage <= 1000, "Max 10% share"); // Max 10%
        
        revenueShares[_recipient] = RevenueShare({
            recipient: _recipient,
            sharePercentage: _sharePercentage,
            totalReceived: 0,
            isActive: true
        });
    }

    /**
     * @dev Distribute revenue to share holders
     */
    function distributeRevenueShares(uint256 _totalRevenue) external onlyOwner {
        // This would iterate through revenue share recipients
        // Simplified for gas efficiency
        uint256 platformShare = (_totalRevenue * 7000) / 10000; // 70% to platform
        uint256 stakingRewards = (_totalRevenue * 3000) / 10000; // 30% to staking rewards
        
        // Distribute to GPUDX staking rewards
        gpudexToken.distributeRevenue(stakingRewards, 0);
        
        totalRevenueShared += stakingRewards;
    }

    /**
     * @dev Check and upgrade client tier based on spending
     */
    function _checkTierUpgrade(address _client) internal {
        EnterpriseClient storage client = enterpriseClients[_client];
        EnterpriseTier currentTier = client.tier;
        EnterpriseTier newTier = currentTier;
        
        // Check tier upgrade eligibility based on total spending
        if (client.totalSpent >= tierMinimums[EnterpriseTier.PLATINUM] && currentTier != EnterpriseTier.PLATINUM) {
            newTier = EnterpriseTier.PLATINUM;
        } else if (client.totalSpent >= tierMinimums[EnterpriseTier.ENTERPRISE] && uint8(currentTier) < uint8(EnterpriseTier.ENTERPRISE)) {
            newTier = EnterpriseTier.ENTERPRISE;
        } else if (client.totalSpent >= tierMinimums[EnterpriseTier.PROFESSIONAL] && uint8(currentTier) < uint8(EnterpriseTier.PROFESSIONAL)) {
            newTier = EnterpriseTier.PROFESSIONAL;
        } else if (client.totalSpent >= tierMinimums[EnterpriseTier.GROWTH] && uint8(currentTier) < uint8(EnterpriseTier.GROWTH)) {
            newTier = EnterpriseTier.GROWTH;
        }
        
        if (newTier != currentTier) {
            client.tier = newTier;
            client.volumeDiscount = tierDiscounts[newTier];
            emit ContractUpgraded(_client, currentTier, newTier);
        }
    }

    /**
     * @dev Get enterprise client details
     */
    function getEnterpriseClient(address _client) external view returns (EnterpriseClient memory) {
        return enterpriseClients[_client];
    }

    /**
     * @dev Get institutional staking details
     */
    function getInstitutionalStaking(address _institution) external view returns (InstitutionalStaking memory) {
        return institutionalStaking[_institution];
    }

    /**
     * @dev Calculate enterprise pricing for quote
     */
    function calculateEnterpriseQuote(
        address _client,
        uint256 _hours,
        string memory _gpuType
    ) external view returns (uint256 baseCost, uint256 discount, uint256 finalCost) {
        if (!enterpriseClients[_client].isActive) {
            baseCost = baseGPUPricePerHour * _hours;
            discount = 0;
            finalCost = baseCost;
            return (baseCost, discount, finalCost);
        }
        
        EnterpriseClient memory client = enterpriseClients[_client];
        
        baseCost = client.hasCustomPricing ? 
            client.customPricePerHour * _hours : 
            baseGPUPricePerHour * _hours;
        
        discount = (baseCost * client.volumeDiscount) / 10000;
        finalCost = baseCost - discount;
        
        return (baseCost, discount, finalCost);
    }

    /**
     * @dev Get platform enterprise metrics
     */
    function getEnterpriseMetrics() external view returns (
        uint256 totalRevenue,
        uint256 totalClients,
        uint256 totalInstitutionalStaking,
        uint256 averageClientValue
    ) {
        totalRevenue = totalEnterpriseRevenue;
        totalClients = activeEnterpriseClients;
        totalInstitutionalStaking = totalInstitutionalStaked;
        averageClientValue = totalClients > 0 ? totalRevenue / totalClients : 0;
    }

    /**
     * @dev Update base pricing
     */
    function updateBasePricing(uint256 _newBasePrice) external onlyOwner {
        require(_newBasePrice > 0, "Invalid price");
        baseGPUPricePerHour = _newBasePrice;
    }

    /**
     * @dev Update tier discounts
     */
    function updateTierDiscount(EnterpriseTier _tier, uint256 _discount) external onlyOwner {
        require(_discount <= maxVolumeDiscount, "Discount too high");
        tierDiscounts[_tier] = _discount;
    }

    /**
     * @dev Emergency withdraw
     */
    function emergencyWithdraw(address _token, uint256 _amount) external onlyOwner {
        IERC20(_token).safeTransfer(owner(), _amount);
    }
} 