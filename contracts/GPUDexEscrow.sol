// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title GPUDexEscrow
 * @dev Decentralized escrow system for GPU rentals
 * Holds payments until service delivery is confirmed
 */
contract GPUDexEscrow is ReentrancyGuard, Ownable {
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
    
    // Dispute reasons
    enum DisputeReason {
        NoAccess,           // Provider didn't provide access
        PoorPerformance,    // GPU performance issues
        Downtime,           // Unexpected downtime
        Other               // Other reasons
    }
    
    struct Rental {
        uint256 rentalId;
        address renter;
        address provider;
        string gpuType;
        uint256 pricePerHour;
        uint256 duration; // Duration in hours
        uint256 totalAmount;
        uint256 depositAmount;
        address paymentToken;       // ERC20 token (USDC, USDT, etc.)
        RentalState state;
        uint256 createdAt;
        uint256 startedAt;
        uint256 completedAt;
        uint256 disputeDeadline;
        string providerEndpoint;    // SSH/API endpoint for access
        string accessCredentials;   // Encrypted access credentials
        bool autoRelease;          // Auto-release after period
    }
    
    struct Dispute {
        uint256 rentalId;
        address initiator;
        DisputeReason reason;
        string description;
        uint256 createdAt;
        uint256 resolvedAt;
        address arbitrator;
        uint256 refundAmount;      // Amount to refund to renter
        uint256 paymentAmount;     // Amount to pay to provider
        bool resolved;
    }
    
    // State variables
    mapping(uint256 => Rental) public rentals;
    mapping(uint256 => Dispute) public disputes;
    mapping(address => bool) public authorizedArbitrators;
    mapping(address => uint256) public providerStakes;
    mapping(address => uint256[]) public renterRentals;
    mapping(address => uint256[]) public providerRentals;
    
    uint256 public nextRentalId = 1;
    uint256 public platformFeePercent = 300; // 3% (300 basis points)
    uint256 public disputePeriod = 24 hours;
    uint256 public autoReleaseDelay = 48 hours;
    uint256 public minimumStake = 1000 * 10**18; // 1000 tokens minimum stake
    
    address public feeRecipient;
    address public gpudexToken; // Platform token for staking
    
    // Events
    event RentalCreated(
        uint256 indexed rentalId,
        address indexed renter,
        address indexed provider,
        string gpuType,
        uint256 totalAmount
    );
    
    event RentalFunded(uint256 indexed rentalId, uint256 amount);
    event RentalStarted(uint256 indexed rentalId, string accessInfo);
    event RentalCompleted(uint256 indexed rentalId);
    event RentalCancelled(uint256 indexed rentalId);
    
    event DisputeCreated(
        uint256 indexed rentalId,
        address indexed initiator,
        DisputeReason reason
    );
    
    event DisputeResolved(
        uint256 indexed rentalId,
        uint256 refundAmount,
        uint256 paymentAmount
    );
    
    event ProviderStaked(address indexed provider, uint256 amount);
    event ProviderUnstaked(address indexed provider, uint256 amount);
    event ProviderSlashed(address indexed provider, uint256 amount);
    
    modifier onlyRenter(uint256 _rentalId) {
        require(rentals[_rentalId].renter == msg.sender, "Not the renter");
        _;
    }
    
    modifier onlyProvider(uint256 _rentalId) {
        require(rentals[_rentalId].provider == msg.sender, "Not the provider");
        _;
    }
    
    modifier onlyArbitrator() {
        require(authorizedArbitrators[msg.sender], "Not authorized arbitrator");
        _;
    }
    
    modifier inState(uint256 _rentalId, RentalState _state) {
        require(rentals[_rentalId].state == _state, "Invalid rental state");
        _;
    }
    
    constructor(address _feeRecipient, address _gpudexToken) {
        feeRecipient = _feeRecipient;
        gpudexToken = _gpudexToken;
        authorizedArbitrators[msg.sender] = true;
    }
    
    /**
     * @dev Create a new GPU rental
     */
    function createRental(
        address _provider,
        string memory _gpuType,
        uint256 _pricePerHour,
        uint256 _duration,
        address _paymentToken,
        bool _autoRelease
    ) external returns (uint256) {
        require(_provider != address(0), "Invalid provider");
        require(_provider != msg.sender, "Cannot rent from yourself");
        require(_pricePerHour > 0, "Invalid price");
        require(_duration > 0, "Invalid duration");
        require(providerStakes[_provider] >= minimumStake, "Provider not staked");
        
        uint256 totalAmount = _pricePerHour * _duration;
        uint256 depositAmount = totalAmount + (totalAmount * 20 / 100); // 20% security deposit
        
        uint256 rentalId = nextRentalId++;
        
        rentals[rentalId] = Rental({
            rentalId: rentalId,
            renter: msg.sender,
            provider: _provider,
            gpuType: _gpuType,
            pricePerHour: _pricePerHour,
            duration: _duration,
            totalAmount: totalAmount,
            depositAmount: depositAmount,
            paymentToken: _paymentToken,
            state: RentalState.Created,
            createdAt: block.timestamp,
            startedAt: 0,
            completedAt: 0,
            disputeDeadline: 0,
            providerEndpoint: "",
            accessCredentials: "",
            autoRelease: _autoRelease
        });
        
        renterRentals[msg.sender].push(rentalId);
        providerRentals[_provider].push(rentalId);
        
        emit RentalCreated(rentalId, msg.sender, _provider, _gpuType, totalAmount);
        
        return rentalId;
    }
    
    /**
     * @dev Fund a rental with payment
     */
    function fundRental(uint256 _rentalId) 
        external 
        onlyRenter(_rentalId)
        inState(_rentalId, RentalState.Created)
        nonReentrant
    {
        Rental storage rental = rentals[_rentalId];
        
        // Transfer payment tokens to escrow
        IERC20(rental.paymentToken).safeTransferFrom(
            msg.sender,
            address(this),
            rental.depositAmount
        );
        
        rental.state = RentalState.Funded;
        
        emit RentalFunded(_rentalId, rental.depositAmount);
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
        inState(_rentalId, RentalState.Funded)
    {
        Rental storage rental = rentals[_rentalId];
        
        rental.state = RentalState.Active;
        rental.startedAt = block.timestamp;
        rental.disputeDeadline = block.timestamp + disputePeriod;
        rental.providerEndpoint = _providerEndpoint;
        rental.accessCredentials = _accessCredentials;
        
        emit RentalStarted(_rentalId, _providerEndpoint);
    }
    
    /**
     * @dev Complete rental and release payment
     */
    function completeRental(uint256 _rentalId) 
        external
        nonReentrant
    {
        Rental storage rental = rentals[_rentalId];
        
        require(
            rental.state == RentalState.Active,
            "Rental not active"
        );
        
        require(
            msg.sender == rental.renter || 
            msg.sender == rental.provider ||
            (rental.autoRelease && block.timestamp >= rental.disputeDeadline),
            "Not authorized to complete"
        );
        
        // If auto-release and past deadline, or manual completion
        if (block.timestamp >= rental.disputeDeadline || msg.sender == rental.renter) {
            _releasePayment(_rentalId);
        }
    }
    
    /**
     * @dev Create a dispute
     */
    function createDispute(
        uint256 _rentalId,
        DisputeReason _reason,
        string memory _description
    ) 
        external
        onlyRenter(_rentalId)
        inState(_rentalId, RentalState.Active)
    {
        require(block.timestamp <= rentals[_rentalId].disputeDeadline, "Dispute period expired");
        
        disputes[_rentalId] = Dispute({
            rentalId: _rentalId,
            initiator: msg.sender,
            reason: _reason,
            description: _description,
            createdAt: block.timestamp,
            resolvedAt: 0,
            arbitrator: address(0),
            refundAmount: 0,
            paymentAmount: 0,
            resolved: false
        });
        
        rentals[_rentalId].state = RentalState.Disputed;
        
        emit DisputeCreated(_rentalId, msg.sender, _reason);
    }
    
    /**
     * @dev Resolve dispute (arbitrator only)
     */
    function resolveDispute(
        uint256 _rentalId,
        uint256 _refundAmount,
        uint256 _paymentAmount
    ) 
        external
        onlyArbitrator
        inState(_rentalId, RentalState.Disputed)
        nonReentrant
    {
        Rental storage rental = rentals[_rentalId];
        Dispute storage dispute = disputes[_rentalId];
        
        require(_refundAmount + _paymentAmount <= rental.depositAmount, "Invalid amounts");
        
        dispute.arbitrator = msg.sender;
        dispute.refundAmount = _refundAmount;
        dispute.paymentAmount = _paymentAmount;
        dispute.resolvedAt = block.timestamp;
        dispute.resolved = true;
        
        rental.state = RentalState.Resolved;
        
        // Transfer refund to renter
        if (_refundAmount > 0) {
            IERC20(rental.paymentToken).safeTransfer(rental.renter, _refundAmount);
        }
        
        // Transfer payment to provider
        if (_paymentAmount > 0) {
            uint256 platformFee = _paymentAmount * platformFeePercent / 10000;
            uint256 providerAmount = _paymentAmount - platformFee;
            
            IERC20(rental.paymentToken).safeTransfer(rental.provider, providerAmount);
            IERC20(rental.paymentToken).safeTransfer(feeRecipient, platformFee);
        }
        
        // Remaining amount goes to platform (penalty)
        uint256 remaining = rental.depositAmount - _refundAmount - _paymentAmount;
        if (remaining > 0) {
            IERC20(rental.paymentToken).safeTransfer(feeRecipient, remaining);
        }
        
        emit DisputeResolved(_rentalId, _refundAmount, _paymentAmount);
    }
    
    /**
     * @dev Cancel unfunded rental
     */
    function cancelRental(uint256 _rentalId) 
        external
        inState(_rentalId, RentalState.Created)
    {
        require(
            msg.sender == rentals[_rentalId].renter || 
            msg.sender == rentals[_rentalId].provider,
            "Not authorized"
        );
        
        rentals[_rentalId].state = RentalState.Cancelled;
        
        emit RentalCancelled(_rentalId);
    }
    
    /**
     * @dev Stake tokens as a provider
     */
    function stakeAsProvider(uint256 _amount) external nonReentrant {
        require(_amount >= minimumStake, "Amount below minimum stake");
        
        IERC20(gpudexToken).safeTransferFrom(msg.sender, address(this), _amount);
        providerStakes[msg.sender] += _amount;
        
        emit ProviderStaked(msg.sender, _amount);
    }
    
    /**
     * @dev Unstake tokens (with delay for security)
     */
    function unstakeProvider(uint256 _amount) external nonReentrant {
        require(providerStakes[msg.sender] >= _amount, "Insufficient stake");
        require(providerStakes[msg.sender] - _amount >= minimumStake, "Must maintain minimum stake");
        
        providerStakes[msg.sender] -= _amount;
        IERC20(gpudexToken).safeTransfer(msg.sender, _amount);
        
        emit ProviderUnstaked(msg.sender, _amount);
    }
    
    /**
     * @dev Internal function to release payment
     */
    function _releasePayment(uint256 _rentalId) internal {
        Rental storage rental = rentals[_rentalId];
        
        rental.state = RentalState.Completed;
        rental.completedAt = block.timestamp;
        
        // Calculate fees
        uint256 platformFee = rental.totalAmount * platformFeePercent / 10000;
        uint256 providerAmount = rental.totalAmount - platformFee;
        uint256 refundAmount = rental.depositAmount - rental.totalAmount;
        
        // Transfer payment to provider
        IERC20(rental.paymentToken).safeTransfer(rental.provider, providerAmount);
        
        // Transfer platform fee
        IERC20(rental.paymentToken).safeTransfer(feeRecipient, platformFee);
        
        // Refund security deposit
        IERC20(rental.paymentToken).safeTransfer(rental.renter, refundAmount);
        
        emit RentalCompleted(_rentalId);
    }
    
    /**
     * @dev Add authorized arbitrator
     */
    function addArbitrator(address _arbitrator) external onlyOwner {
        authorizedArbitrators[_arbitrator] = true;
    }
    
    /**
     * @dev Remove arbitrator
     */
    function removeArbitrator(address _arbitrator) external onlyOwner {
        authorizedArbitrators[_arbitrator] = false;
    }
    
    /**
     * @dev Update platform fee
     */
    function updatePlatformFee(uint256 _feePercent) external onlyOwner {
        require(_feePercent <= 1000, "Fee too high"); // Max 10%
        platformFeePercent = _feePercent;
    }
    
    /**
     * @dev Emergency withdrawal (owner only)
     */
    function emergencyWithdraw(address _token, uint256 _amount) external onlyOwner {
        IERC20(_token).safeTransfer(owner(), _amount);
    }
    
    /**
     * @dev Get rental details
     */
    function getRental(uint256 _rentalId) external view returns (Rental memory) {
        return rentals[_rentalId];
    }
    
    /**
     * @dev Get user rentals
     */
    function getUserRentals(address _user, bool _asRenter) external view returns (uint256[] memory) {
        return _asRenter ? renterRentals[_user] : providerRentals[_user];
    }
    
    /**
     * @dev Get provider stake amount
     */
    function getProviderStake(address _provider) external view returns (uint256) {
        return providerStakes[_provider];
    }
} 