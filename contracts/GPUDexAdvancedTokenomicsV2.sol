// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IGPUDexTokenV2 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function burn(uint256 amount) external;
    function distributeRevenue(uint256 _rewardAmount, uint256 _feeAmount) external;
    function totalStaked() external view returns (uint256);
}

interface IPriceOracle {
    function getPrice(address token) external view returns (uint256);
    function getPlatformDemandScore() external view returns (uint256);
}

/**
 * @title GPUDexAdvancedTokenomicsV2
 * @dev Advanced tokenomics engine with dynamic APY, cross-chain features, and intelligent burn mechanisms
 */
contract GPUDexAdvancedTokenomicsV2 is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Dynamic APY configuration
    struct DynamicAPYConfig {
        uint256 baseAPY;           // Base APY in basis points
        uint256 demandMultiplier;  // Multiplier based on platform demand
        uint256 maxAPY;            // Maximum APY cap
        uint256 minAPY;            // Minimum APY floor
        uint256 lastUpdate;       // Last update timestamp
    }

    // Cross-chain bridge information
    struct BridgeInfo {
        uint256 chainId;
        address bridgeContract;
        address tokenAddress;
        uint256 totalBridged;
        bool isActive;
        uint256 bridgeFee; // Basis points
    }

    // Burn mechanism configuration
    struct BurnMechanics {
        uint256 demandBasedBurnRate;    // Basis points
        uint256 revenueBurnRate;        // Basis points
        uint256 deflationTarget;       // Target deflation rate
        uint256 totalBurned;           // Total tokens burned
        uint256 lastBurnTime;          // Last burn execution
    }

    // Yield optimization data
    struct YieldOptimization {
        uint256 platformRevenue;       // Platform revenue in last period
        uint256 stakingParticipation;  // Staking participation rate
        uint256 optimalAPY;            // AI-calculated optimal APY
        uint256 yieldSustainabilityScore; // 0-100 sustainability score
    }

    // Institutional program configuration
    struct InstitutionalProgram {
        uint256 minimumStake;          // Minimum stake for institutions
        uint256 lockupPeriod;          // Lockup period in seconds
        uint256 bonusAPY;              // Bonus APY for institutions
        uint256 totalInstitutional;   // Total institutional stakes
        bool isActive;
    }

    // State variables
    IGPUDexTokenV2 public gpudexToken;
    IPriceOracle public priceOracle;
    
    DynamicAPYConfig public dynamicAPY;
    BurnMechanics public burnConfig;
    YieldOptimization public yieldOptim;
    InstitutionalProgram public institutional;
    
    mapping(uint256 => BridgeInfo) public bridges; // chainId => BridgeInfo
    mapping(address => uint256) public crossChainBalances;
    mapping(address => uint256) public institutionalStakes;
    mapping(address => uint256) public lastClaimTime;
    
    uint256[] public supportedChains;
    
    // Advanced metrics
    uint256 public demandScore;
    uint256 public velocityScore;
    uint256 public utilityScore;
    uint256 public sustainabilityScore;
    
    // Events
    event DynamicAPYUpdated(uint256 oldAPY, uint256 newAPY, uint256 demandScore);
    event TokensBurned(uint256 amount, string reason);
    event CrossChainBridge(address indexed user, uint256 fromChain, uint256 toChain, uint256 amount);
    event InstitutionalStakeCreated(address indexed institution, uint256 amount, uint256 bonusAPY);
    event YieldOptimizationUpdate(uint256 optimalAPY, uint256 sustainabilityScore);
    event AdvancedMetricsUpdate(uint256 demand, uint256 velocity, uint256 utility, uint256 sustainability);

    constructor(
        address _gpudexToken,
        address _priceOracle
    ) {
        gpudexToken = IGPUDexTokenV2(_gpudexToken);
        priceOracle = IPriceOracle(_priceOracle);
        
        // Initialize dynamic APY
        dynamicAPY = DynamicAPYConfig({
            baseAPY: 1000,        // 10% base APY
            demandMultiplier: 150, // 1.5x multiplier
            maxAPY: 5000,         // 50% max APY
            minAPY: 500,          // 5% min APY
            lastUpdate: block.timestamp
        });
        
        // Initialize burn mechanics
        burnConfig = BurnMechanics({
            demandBasedBurnRate: 100,    // 1% of revenue
            revenueBurnRate: 50,         // 0.5% of revenue
            deflationTarget: 200,        // 2% annual deflation target
            totalBurned: 0,
            lastBurnTime: block.timestamp
        });
        
        // Initialize institutional program
        institutional = InstitutionalProgram({
            minimumStake: 1000000 * 10**18, // 1M GPUDX minimum
            lockupPeriod: 365 days,         // 1 year lockup
            bonusAPY: 500,                  // 5% bonus APY
            totalInstitutional: 0,
            isActive: true
        });
    }

    /**
     * @dev Update dynamic APY based on platform demand and metrics
     */
    function updateDynamicAPY() external {
        require(address(priceOracle) != address(0), "Price oracle not set");
        
        // Get current demand score (0-100)
        uint256 currentScore = demandScore > 50 ? 20 : (demandScore * 20) / 50;
        
        // Calculate new APY based on demand
        uint256 baseAPY = dynamicAPY.baseAPY;
        uint256 multiplier = dynamicAPY.demandMultiplier + currentScore;
        uint256 newAPY = (baseAPY * multiplier) / 100;
        
        // Apply bounds
        if (newAPY > dynamicAPY.maxAPY) {
            newAPY = dynamicAPY.maxAPY;
        } else if (newAPY < dynamicAPY.minAPY) {
            newAPY = dynamicAPY.minAPY;
        }
        
        // Update APY in the main token contract (if accessible)
        // gpudexToken.updateAPY(newAPY); // Uncomment when function is available
        
        emit DynamicAPYUpdated(dynamicAPY.baseAPY, newAPY, currentScore);
    }

    /**
     * @dev Execute demand-based token burn
     */
    function executeDemandBasedBurn(uint256 _platformRevenue) external onlyOwner {
        require(block.timestamp >= burnConfig.lastBurnTime + 1 days, "Daily burn limit");
        
        // Calculate burn amount based on demand and revenue
        uint256 demandBurnAmount = (_platformRevenue * burnConfig.demandBasedBurnRate) / 10000;
        uint256 revenueBurnAmount = (_platformRevenue * burnConfig.revenueBurnRate) / 10000;
        
        uint256 totalBurnAmount = demandBurnAmount + revenueBurnAmount;
        
        // Ensure we don't burn more than available
        uint256 availableBalance = gpudexToken.balanceOf(address(this));
        if (totalBurnAmount > availableBalance) {
            totalBurnAmount = availableBalance;
        }
        
        if (totalBurnAmount > 0) {
            gpudexToken.burn(totalBurnAmount);
            burnConfig.totalBurned += totalBurnAmount;
            burnConfig.lastBurnTime = block.timestamp;
            
            emit TokensBurned(totalBurnAmount, "Demand-based burn");
        }
    }

    /**
     * @dev Setup cross-chain bridge
     */
    function setupCrossChainBridge(
        uint256 _chainId,
        address _bridgeContract,
        address _tokenAddress,
        uint256 _bridgeFee
    ) external onlyOwner {
        require(_bridgeFee <= 1000, "Bridge fee too high"); // Max 10%
        
        bridges[_chainId] = BridgeInfo({
            chainId: _chainId,
            bridgeContract: _bridgeContract,
            tokenAddress: _tokenAddress,
            totalBridged: 0,
            isActive: true,
            bridgeFee: _bridgeFee
        });
        
        supportedChains.push(_chainId);
    }

    /**
     * @dev Bridge tokens to another chain
     */
    function bridgeToChain(uint256 _toChainId, uint256 _amount) external nonReentrant {
        require(bridges[_toChainId].isActive, "Bridge not active");
        require(_amount > 0, "Invalid amount");
        
        BridgeInfo storage bridge = bridges[_toChainId];
        
        // Calculate bridge fee
        uint256 bridgeFee = (_amount * bridge.bridgeFee) / 10000;
        uint256 bridgeAmount = _amount - bridgeFee;
        
        // Transfer tokens from user
        gpudexToken.transfer(address(this), _amount);
        
        // Update bridge statistics
        bridge.totalBridged += bridgeAmount;
        crossChainBalances[msg.sender] += bridgeAmount;
        
        // Burn bridge fee (deflationary mechanism)
        if (bridgeFee > 0) {
            gpudexToken.burn(bridgeFee);
            emit TokensBurned(bridgeFee, "Cross-chain bridge fee");
        }
        
        emit CrossChainBridge(msg.sender, block.chainid, _toChainId, bridgeAmount);
    }

    /**
     * @dev Create institutional staking position
     */
    function createInstitutionalStake(uint256 _amount) external nonReentrant {
        require(institutional.isActive, "Institutional program not active");
        require(_amount >= institutional.minimumStake, "Below minimum stake");
        
        // Transfer tokens to contract
        gpudexToken.transfer(address(this), _amount);
        
        // Record institutional stake
        institutionalStakes[msg.sender] += _amount;
        institutional.totalInstitutional += _amount;
        
        emit InstitutionalStakeCreated(msg.sender, _amount, institutional.bonusAPY);
    }

    /**
     * @dev Calculate optimal yield and sustainability score
     * @return optimalAPY The calculated optimal APY
     * @return sustainability The sustainability score (0-100)
     */
    function calculateOptimalYield() external view returns (uint256 optimalAPY, uint256 sustainability) {
        // Get platform metrics
        uint256 totalStaked = gpudexToken.totalSupply() / 4; // Assume 25% staked
        uint256 platformRevenue = address(this).balance; // Simple revenue proxy
        
        // Calculate optimal APY based on staking participation and revenue
        uint256 stakingParticipation = totalStaked > 0 ? (totalStaked * 100) / gpudexToken.totalSupply() : 0;
        
        // Target 30-50% staking participation
        if (stakingParticipation < 30) {
            optimalAPY = dynamicAPY.maxAPY; // High APY to attract stakers
        } else if (stakingParticipation > 50) {
            optimalAPY = dynamicAPY.minAPY; // Lower APY when over-staked
        } else {
            // Linear interpolation between min and max
            uint256 range = dynamicAPY.maxAPY - dynamicAPY.minAPY;
            uint256 factor = (50 - stakingParticipation) * 100 / 20; // 20% range
            optimalAPY = dynamicAPY.minAPY + (range * factor / 100);
        }
        
        // Calculate sustainability (higher revenue = higher sustainability)
        sustainability = platformRevenue > 1 ether ? 100 : (platformRevenue * 100) / 1 ether;
        if (sustainability > 100) sustainability = 100;
        
        return (optimalAPY, sustainability);
    }

    /**
     * @dev Update platform metrics and recalculate tokenomics
     * @param _platformRevenue Current platform revenue
     * @param _stakingParticipation Current staking participation rate (basis points)
     */
    function updatePlatformMetrics(uint256 _platformRevenue, uint256 _stakingParticipation) external onlyOwner {
        // Calculate optimal APY and sustainability
        (uint256 optimalAPY, uint256 sustainabilityValue) = this.calculateOptimalYield();
        
        // Update dynamic APY if needed
        if (optimalAPY != dynamicAPY.baseAPY) {
            dynamicAPY.baseAPY = optimalAPY;
            emit DynamicAPYUpdated(dynamicAPY.baseAPY, optimalAPY, demandScore);
        }
        
        // Update advanced metrics
        this.updateAdvancedMetrics();
        
        emit YieldOptimizationUpdate(optimalAPY, sustainabilityValue);
    }

    /**
     * @dev Calculate and update advanced metrics
     */
    function updateAdvancedMetrics() external {
        // Calculate demand score based on recent activity
        uint256 currentScore = demandScore > 50 ? 20 : (demandScore * 20) / 50;
        
        // Update velocity score
        uint256 currentVelocity = gpudexToken.totalSupply() > 0 ? 
            (address(gpudexToken).balance * 10000) / gpudexToken.totalSupply() : 0;
        velocityScore = currentVelocity > 10000 ? 10000 : currentVelocity;
        
        // Update utility score (simplified calculation)
        utilityScore = (currentScore + velocityScore) / 2;
        if (utilityScore > 10000) utilityScore = 10000;
        
        // Update sustainability score
        sustainabilityScore = utilityScore > 5000 ? 10000 : (utilityScore * 2);
        
        emit AdvancedMetricsUpdate(currentScore, velocityScore, utilityScore, sustainabilityScore);
    }

    /**
     * @dev Internal function to calculate velocity score
     */
    function _calculateVelocityScore() internal view returns (uint256) {
        // Simplified velocity calculation
        // In production, would use transaction count and volume data
        uint256 totalSupply = gpudexToken.totalSupply();
        uint256 totalStaked = gpudexToken.totalStaked();
        
        if (totalSupply == 0) return 0;
        
        uint256 circulatingSupply = totalSupply - totalStaked;
        uint256 velocityRatio = totalStaked > 0 ? (circulatingSupply * 100) / totalStaked : 100;
        
        return velocityRatio > 100 ? 100 : velocityRatio;
    }

    /**
     * @dev Internal function to calculate utility score
     */
    function _calculateUtilityScore() internal view returns (uint256) {
        // Utility score based on burns, platform usage, and real transactions
        uint256 burnScore = burnConfig.totalBurned > 0 ? 40 : 0;
        uint256 revenueScore = yieldOptim.platformRevenue > 0 ? 40 : 0;
        uint256 currentDemandScore = demandScore > 50 ? 20 : (demandScore * 20) / 50;
        
        return burnScore + revenueScore + demandScore;
    }

    /**
     * @dev Get current dynamic APY
     */
    function getCurrentAPY() external view returns (uint256) {
        return dynamicAPY.baseAPY;
    }

    /**
     * @dev Get burn statistics
     */
    function getBurnStatistics() external view returns (
        uint256 totalBurned,
        uint256 burnRate,
        uint256 deflationRate
    ) {
        totalBurned = burnConfig.totalBurned;
        burnRate = burnConfig.demandBasedBurnRate + burnConfig.revenueBurnRate;
        
        uint256 totalSupply = gpudexToken.totalSupply();
        deflationRate = totalSupply > 0 ? (totalBurned * 10000) / totalSupply : 0;
        
        return (totalBurned, burnRate, deflationRate);
    }

    /**
     * @dev Get cross-chain bridge information
     */
    function getBridgeInfo(uint256 _chainId) external view returns (BridgeInfo memory) {
        return bridges[_chainId];
    }

    /**
     * @dev Get supported chains
     */
    function getSupportedChains() external view returns (uint256[] memory) {
        return supportedChains;
    }

    /**
     * @dev Get institutional staking information
     */
    function getInstitutionalInfo() external view returns (InstitutionalProgram memory) {
        return institutional;
    }

    /**
     * @dev Get user's institutional stake
     */
    function getInstitutionalStake(address _user) external view returns (uint256) {
        return institutionalStakes[_user];
    }

    /**
     * @dev Update dynamic APY configuration
     */
    function updateDynamicAPYConfig(
        uint256 _baseAPY,
        uint256 _demandMultiplier,
        uint256 _maxAPY,
        uint256 _minAPY
    ) external onlyOwner {
        require(_maxAPY > _minAPY, "Invalid APY bounds");
        require(_maxAPY <= 10000, "APY too high"); // Max 100%
        
        dynamicAPY.baseAPY = _baseAPY;
        dynamicAPY.demandMultiplier = _demandMultiplier;
        dynamicAPY.maxAPY = _maxAPY;
        dynamicAPY.minAPY = _minAPY;
    }

    /**
     * @dev Update burn configuration
     */
    function updateBurnConfig(
        uint256 _demandBasedBurnRate,
        uint256 _revenueBurnRate,
        uint256 _deflationTarget
    ) external onlyOwner {
        require(_demandBasedBurnRate <= 1000, "Burn rate too high"); // Max 10%
        require(_revenueBurnRate <= 1000, "Burn rate too high"); // Max 10%
        
        burnConfig.demandBasedBurnRate = _demandBasedBurnRate;
        burnConfig.revenueBurnRate = _revenueBurnRate;
        burnConfig.deflationTarget = _deflationTarget;
    }

    /**
     * @dev Emergency functions
     */
    function pauseBridge(uint256 _chainId) external onlyOwner {
        bridges[_chainId].isActive = false;
    }

    function unpauseBridge(uint256 _chainId) external onlyOwner {
        bridges[_chainId].isActive = true;
    }

    function emergencyWithdraw(address _token, uint256 _amount) external onlyOwner {
        IERC20(_token).safeTransfer(owner(), _amount);
    }
} 