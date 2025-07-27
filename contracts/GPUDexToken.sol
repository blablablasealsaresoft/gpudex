// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";

/**
 * @title GPUDexToken (GPUDX)
 * @dev Platform governance token with staking rewards and fee distribution
 */
contract GPUDexToken is ERC20, ERC20Burnable, Pausable, Ownable, ERC20Permit, ERC20Votes {
    
    // Token distribution
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens
    uint256 public constant TEAM_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant INVESTORS_ALLOCATION = 150_000_000 * 10**18; // 15%
    uint256 public constant LIQUIDITY_ALLOCATION = 100_000_000 * 10**18; // 10%
    uint256 public constant TREASURY_ALLOCATION = 300_000_000 * 10**18; // 30%
    uint256 public constant STAKING_REWARDS_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant AIRDROP_ALLOCATION = 50_000_000 * 10**18; // 5%
    
    // Staking and rewards
    struct StakingInfo {
        uint256 amount;
        uint256 rewardDebt;
        uint256 stakedAt;
        uint256 lockUntil;
    }
    
    mapping(address => StakingInfo) public stakingInfo;
    mapping(address => bool) public isProvider;
    
    uint256 public totalStaked;
    uint256 public accRewardPerShare;
    uint256 public lastRewardBlock;
    uint256 public rewardPerBlock = 100 * 10**18; // 100 tokens per block
    
    // Fee distribution
    uint256 public totalFeesCollected;
    uint256 public feesPerTokenStaked;
    mapping(address => uint256) public feeDebt;
    
    // Governance
    uint256 public proposalCount;
    
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startBlock;
        uint256 endBlock;
        bool executed;
        bool cancelled;
        mapping(address => bool) hasVoted;
        mapping(address => bool) voteChoice; // true = for, false = against
    }
    
    mapping(uint256 => Proposal) public proposals;
    uint256 public constant VOTING_DELAY = 7200; // 1 day (assuming 12 second blocks)
    uint256 public constant VOTING_PERIOD = 50400; // 7 days
    uint256 public constant PROPOSAL_THRESHOLD = 1_000_000 * 10**18; // 1M tokens to propose
    uint256 public constant QUORUM = 50_000_000 * 10**18; // 50M tokens for quorum
    
    // Events
    event Staked(address indexed user, uint256 amount, uint256 lockPeriod);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    event FeesDistributed(uint256 amount);
    event ProviderRegistered(address indexed provider);
    event ProviderUnregistered(address indexed provider);
    
    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        string description,
        uint256 startBlock,
        uint256 endBlock
    );
    
    event VoteCast(
        address indexed voter,
        uint256 indexed proposalId,
        bool support,
        uint256 weight
    );
    
    event ProposalExecuted(uint256 indexed proposalId);
    
    constructor(address _initialOwner) 
        ERC20("GPUDex Token", "GPUDX") 
        ERC20Permit("GPUDex Token")
        Ownable()
    {
        _transferOwnership(_initialOwner);
        
        // Initial minting
        _mint(_initialOwner, TEAM_ALLOCATION);
        _mint(_initialOwner, TREASURY_ALLOCATION);
        _mint(address(this), STAKING_REWARDS_ALLOCATION); // For staking rewards
        
        lastRewardBlock = block.number;
    }
    
    /**
     * @dev Mint tokens to specific addresses (owner only)
     */
    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }
    
    /**
     * @dev Stake tokens for rewards and governance power
     */
    function stake(uint256 _amount, uint256 _lockDays) external whenNotPaused {
        require(_amount > 0, "Cannot stake 0");
        require(_lockDays <= 365, "Lock period too long");
        
        updateRewards();
        
        StakingInfo storage user = stakingInfo[msg.sender];
        
        // Claim pending rewards
        if (user.amount > 0) {
            uint256 pending = (user.amount * accRewardPerShare / 1e12) - user.rewardDebt;
            if (pending > 0) {
                _transfer(address(this), msg.sender, pending);
                emit RewardsClaimed(msg.sender, pending);
            }
        }
        
        // Transfer tokens to contract
        _transfer(msg.sender, address(this), _amount);
        
        // Update staking info
        user.amount += _amount;
        user.stakedAt = block.timestamp;
        user.lockUntil = block.timestamp + (_lockDays * 1 days);
        user.rewardDebt = user.amount * accRewardPerShare / 1e12;
        
        totalStaked += _amount;
        
        // Delegate voting power to self
        _delegate(msg.sender, msg.sender);
        
        emit Staked(msg.sender, _amount, _lockDays);
    }
    
    /**
     * @dev Unstake tokens
     */
    function unstake(uint256 _amount) external {
        StakingInfo storage user = stakingInfo[msg.sender];
        require(user.amount >= _amount, "Insufficient staked amount");
        require(block.timestamp >= user.lockUntil, "Tokens still locked");
        
        updateRewards();
        
        // Claim pending rewards
        uint256 pending = (user.amount * accRewardPerShare / 1e12) - user.rewardDebt;
        if (pending > 0) {
            _transfer(address(this), msg.sender, pending);
            emit RewardsClaimed(msg.sender, pending);
        }
        
        // Update staking info
        user.amount -= _amount;
        user.rewardDebt = user.amount * accRewardPerShare / 1e12;
        totalStaked -= _amount;
        
        // Transfer tokens back to user
        _transfer(address(this), msg.sender, _amount);
        
        emit Unstaked(msg.sender, _amount);
    }
    
    /**
     * @dev Claim staking rewards
     */
    function claimRewards() external {
        updateRewards();
        
        StakingInfo storage user = stakingInfo[msg.sender];
        uint256 pending = (user.amount * accRewardPerShare / 1e12) - user.rewardDebt;
        
        require(pending > 0, "No rewards to claim");
        
        user.rewardDebt = user.amount * accRewardPerShare / 1e12;
        _transfer(address(this), msg.sender, pending);
        
        emit RewardsClaimed(msg.sender, pending);
    }
    
    /**
     * @dev Update reward calculations
     */
    function updateRewards() public {
        if (block.number <= lastRewardBlock) {
            return;
        }
        
        if (totalStaked == 0) {
            lastRewardBlock = block.number;
            return;
        }
        
        uint256 multiplier = block.number - lastRewardBlock;
        uint256 reward = multiplier * rewardPerBlock;
        
        // Check if we have enough rewards in contract
        uint256 contractBalance = balanceOf(address(this)) - totalStaked;
        if (reward > contractBalance) {
            reward = contractBalance;
        }
        
        if (reward > 0) {
            accRewardPerShare += (reward * 1e12) / totalStaked;
        }
        
        lastRewardBlock = block.number;
    }
    
    /**
     * @dev Distribute platform fees to stakers
     */
    function distributeFees(uint256 _amount) external onlyOwner {
        require(_amount > 0, "No fees to distribute");
        require(totalStaked > 0, "No stakers");
        
        _transfer(msg.sender, address(this), _amount);
        
        feesPerTokenStaked += (_amount * 1e12) / totalStaked;
        totalFeesCollected += _amount;
        
        emit FeesDistributed(_amount);
    }
    
    /**
     * @dev Claim fee share
     */
    function claimFees() external {
        StakingInfo storage user = stakingInfo[msg.sender];
        require(user.amount > 0, "No staked tokens");
        
        uint256 pending = (user.amount * feesPerTokenStaked / 1e12) - feeDebt[msg.sender];
        require(pending > 0, "No fees to claim");
        
        feeDebt[msg.sender] = user.amount * feesPerTokenStaked / 1e12;
        _transfer(address(this), msg.sender, pending);
    }
    
    /**
     * @dev Register as GPU provider
     */
    function registerProvider() external {
        require(stakingInfo[msg.sender].amount >= 10_000 * 10**18, "Insufficient stake for provider"); // 10k tokens minimum
        isProvider[msg.sender] = true;
        emit ProviderRegistered(msg.sender);
    }
    
    /**
     * @dev Unregister as provider
     */
    function unregisterProvider() external {
        isProvider[msg.sender] = false;
        emit ProviderUnregistered(msg.sender);
    }
    
    /**
     * @dev Create governance proposal
     */
    function propose(string memory _description) external returns (uint256) {
        require(
            getVotes(msg.sender) >= PROPOSAL_THRESHOLD,
            "Insufficient voting power to propose"
        );
        
        uint256 proposalId = ++proposalCount;
        Proposal storage proposal = proposals[proposalId];
        
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.description = _description;
        proposal.startBlock = block.number + VOTING_DELAY;
        proposal.endBlock = proposal.startBlock + VOTING_PERIOD;
        
        emit ProposalCreated(
            proposalId,
            msg.sender,
            _description,
            proposal.startBlock,
            proposal.endBlock
        );
        
        return proposalId;
    }
    
    /**
     * @dev Vote on proposal
     */
    function castVote(uint256 _proposalId, bool _support) external {
        Proposal storage proposal = proposals[_proposalId];
        require(_proposalId > 0 && _proposalId <= proposalCount, "Invalid proposal");
        require(block.number >= proposal.startBlock, "Voting not started");
        require(block.number <= proposal.endBlock, "Voting ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        
        uint256 weight = getVotes(msg.sender);
        require(weight > 0, "No voting power");
        
        proposal.hasVoted[msg.sender] = true;
        proposal.voteChoice[msg.sender] = _support;
        
        if (_support) {
            proposal.forVotes += weight;
        } else {
            proposal.againstVotes += weight;
        }
        
        emit VoteCast(msg.sender, _proposalId, _support, weight);
    }
    
    /**
     * @dev Execute proposal (if passed)
     */
    function executeProposal(uint256 _proposalId) external {
        Proposal storage proposal = proposals[_proposalId];
        require(_proposalId > 0 && _proposalId <= proposalCount, "Invalid proposal");
        require(block.number > proposal.endBlock, "Voting not ended");
        require(!proposal.executed && !proposal.cancelled, "Already executed or cancelled");
        require(proposal.forVotes > proposal.againstVotes, "Proposal failed");
        require(proposal.forVotes >= QUORUM, "Quorum not reached");
        
        proposal.executed = true;
        
        // Proposal execution logic would go here
        // For now, just emit event
        
        emit ProposalExecuted(_proposalId);
    }
    
    /**
     * @dev Get pending staking rewards
     */
    function pendingRewards(address _user) external view returns (uint256) {
        StakingInfo storage user = stakingInfo[_user];
        uint256 _accRewardPerShare = accRewardPerShare;
        
        if (block.number > lastRewardBlock && totalStaked != 0) {
            uint256 multiplier = block.number - lastRewardBlock;
            uint256 reward = multiplier * rewardPerBlock;
            uint256 contractBalance = balanceOf(address(this)) - totalStaked;
            if (reward > contractBalance) {
                reward = contractBalance;
            }
            _accRewardPerShare += (reward * 1e12) / totalStaked;
        }
        
        return (user.amount * _accRewardPerShare / 1e12) - user.rewardDebt;
    }
    
    /**
     * @dev Get pending fee rewards
     */
    function pendingFees(address _user) external view returns (uint256) {
        StakingInfo storage user = stakingInfo[_user];
        return (user.amount * feesPerTokenStaked / 1e12) - feeDebt[_user];
    }
    
    /**
     * @dev Pause contract (emergency)
     */
    function pause() public onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause contract
     */
    function unpause() public onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Update reward per block
     */
    function updateRewardPerBlock(uint256 _rewardPerBlock) external onlyOwner {
        updateRewards();
        rewardPerBlock = _rewardPerBlock;
    }
    
    // Required overrides
    function _beforeTokenTransfer(address from, address to, uint256 amount)
        internal
        whenNotPaused
        override
    {
        super._beforeTokenTransfer(from, to, amount);
    }
    
    function _afterTokenTransfer(address from, address to, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._afterTokenTransfer(from, to, amount);
    }
    
    function _mint(address to, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._mint(to, amount);
    }
    
    function _burn(address account, uint256 amount)
        internal
        override(ERC20, ERC20Votes)
    {
        super._burn(account, amount);
    }
} 