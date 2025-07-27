require("@nomiclabs/hardhat-ethers");
require("@nomiclabs/hardhat-waffle");
require("@openzeppelin/hardhat-upgrades");
require("@matterlabs/hardhat-zksync-deploy");
require("@matterlabs/hardhat-zksync-solc");
require("@matterlabs/hardhat-zksync-verify");
require("dotenv").config();

// This is a sample Hardhat task. To learn how to create your own go to
// https://hardhat.org/guides/create-task.html
task("accounts", "Prints the list of accounts", async (taskArgs, hre) => {
  const accounts = await hre.ethers.getSigners();

  for (const account of accounts) {
    console.log(account.address);
  }
});

// You need to export an object to set up your config
// Go to https://hardhat.org/config/ to learn more

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  // zkSync Era configuration
  zksolc: {
    version: "1.3.14",
    compilerSource: "binary",
    settings: {},
  },
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true, // Fixes "Stack too deep" errors
    },
  },
  // Enable zkSync Era by default for compatible networks
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337,
      zksync: false, // Disable zkSync for local development
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
      zksync: false,
    },
    // zkSync Era Networks
    zkSyncEra: {
      url: process.env.ZKSYNC_RPC_URL || "https://mainnet.era.zksync.io",
      ethNetwork: "mainnet",
      chainId: 324,
      zksync: true,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      verifyURL: "https://zksync2-mainnet-explorer.zksync.io/contract_verification",
    },
    zkSyncGoerli: {
      url: process.env.ZKSYNC_GOERLI_RPC_URL || "https://testnet.era.zksync.dev",
      ethNetwork: "goerli",
      chainId: 280,
      zksync: true,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      verifyURL: "https://zksync2-testnet-explorer.zksync.dev/contract_verification",
    },
    mumbai: {
      url: process.env.MUMBAI_RPC_URL || "https://polygon-mumbai-bor.publicnode.com",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 80001,
    },
    polygon: {
      url: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com/",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 137,
      gasPrice: 35000000000, // 35 gwei
    },
    mainnet: {
      url: process.env.MAINNET_RPC_URL || "https://mainnet.infura.io/v3/YOUR_INFURA_KEY",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 1,
      gasPrice: 20000000000, // 20 gwei
    },
    arbitrum: {
      url: process.env.ARBITRUM_RPC_URL || "https://arb1.arbitrum.io/rpc",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 42161,
    },
    optimism: {
      url: process.env.OPTIMISM_RPC_URL || "https://mainnet.optimism.io",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 10,
    },
  },
  etherscan: {
    // Etherscan v2 - Single API key for all chains
    apiKey: process.env.ETHERSCAN_API_KEY,
    customChains: [
      {
        network: "polygon",
        chainId: 137,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=137",
          browserURL: "https://polygonscan.com"
        }
      },
      {
        network: "mumbai", 
        chainId: 80001,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=80001",
          browserURL: "https://mumbai.polygonscan.com"
        }
      },
      {
        network: "arbitrum",
        chainId: 42161, 
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=42161",
          browserURL: "https://arbiscan.io"
        }
      },
      {
        network: "optimism",
        chainId: 10,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=10", 
          browserURL: "https://optimistic.etherscan.io"
        }
      },
      {
        network: "zkSyncEra",
        chainId: 324,
        urls: {
          apiURL: "https://zksync2-mainnet-explorer.zksync.io/contract_verification",
          browserURL: "https://explorer.zksync.io"
        }
      }
    ]
  },
  mocha: {
    timeout: 20000,
  },
}; 