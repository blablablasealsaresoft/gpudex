// GPUDex V2 Frontend Contract Configuration
// Updated for localhost development environment

window.GPUDEX_V2_CONTRACTS = {
    network: 'localhost',
    chainId: 31337, // Hardhat localhost chain ID
    
    // Contract Addresses (localhost deployment)
    token: '0x5FbDB2315678afecb367f032d93F642f64180aa3',
    escrow: '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
    enterprise: '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0',
    advancedTokenomics: '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9',
    
    // RPC Configuration for localhost
    rpcUrl: 'http://localhost:8545',
    
    // Fallback to environment variables for production
    getAddress: function(contractName) {
        const envVar = `${contractName.toUpperCase()}_CONTRACT_ADDRESS`;
        return window.ENV && window.ENV[envVar] ? window.ENV[envVar] : this[contractName];
    }
};

// Staking Tier Constants
window.STAKING_TIERS = {
    BRONZE: { minStake: '10000', discountBps: 500, apyRange: [800, 1500] },
    SILVER: { minStake: '100000', discountBps: 1000, apyRange: [1000, 2000] },
    GOLD: { minStake: '500000', discountBps: 1500, apyRange: [1200, 2500] },
    DIAMOND: { minStake: '2000000', discountBps: 2500, apyRange: [1500, 5000] }
};

// Enterprise Tier Constants
window.ENTERPRISE_TIERS = {
    STARTUP: { minMonthly: 1000, discount: 5 },
    GROWTH: { minMonthly: 5000, discount: 10 },
    PROFESSIONAL: { minMonthly: 25000, discount: 15 },
    ENTERPRISE: { minMonthly: 100000, discount: 20 },
    PLATINUM: { minMonthly: 500000, discount: 30 }
};

// Network detection helper
window.getNetworkConfig = function() {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    if (isLocalhost) {
        return {
            chainId: 31337,
            rpcUrl: 'http://localhost:8545',
            name: 'Localhost'
        };
    } else {
        return {
            chainId: 137,
            rpcUrl: 'https://polygon-rpc.com',
            name: 'Polygon'
        };
    }
};

// Initialize configuration
console.log('GPUDx Contract Configuration Loaded:', window.GPUDEX_V2_CONTRACTS);
