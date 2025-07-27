const { utils, Wallet } = require("zksync-web3");
const { HardhatRuntimeEnvironment } = require("hardhat/types");
const { Deployer } = require("@matterlabs/hardhat-zksync-deploy");

async function main() {
  console.log(`🚀 Starting zkSync Era Deployment for GPUDex`);
  
  // Get private key from environment
  const privateKey = process.env.PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("Private key not found in environment variables");
  }

  // Initialize the wallet
  const wallet = new Wallet(privateKey);
  
  // Create deployer object and load the artifact of the contract we want to deploy
  const deployer = new Deployer(hre, wallet);
  
  console.log("Deploying with wallet:", wallet.address);
  console.log("Wallet balance:", await wallet.getBalance());

  // Configuration for zkSync Era networks
  const networkConfig = {
    // zkSync Era Mainnet
    324: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || wallet.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token",
      tokenSymbol: "GPUDX",
      initialSupply: utils.parseEther("1000000000"), // 1B tokens
      description: "zkSync Era Mainnet - Ultra low fees with Ethereum security"
    },
    // zkSync Era Goerli Testnet
    280: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || wallet.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token (zkSync Testnet)",
      tokenSymbol: "GPUDX",
      initialSupply: utils.parseEther("1000000000"), // 1B tokens
      description: "zkSync Era Testnet"
    }
  };

  // Get network info
  const network = await hre.network.provider.send("eth_chainId");
  const chainId = parseInt(network, 16);
  const config = networkConfig[chainId];
  
  if (!config) {
    throw new Error(`No configuration found for chain ID: ${chainId}`);
  }

  console.log("Network Chain ID:", chainId);
  console.log("Network:", config.description);
  console.log("Fee Recipient:", config.feeRecipient);

  // Load contract artifacts
  const tokenArtifact = await deployer.loadArtifact("GPUDexToken");
  const escrowArtifact = await deployer.loadArtifact("GPUDexEscrow");

  console.log("\n🪙 Deploying GPUDex Token...");
  
  // Deploy GPUDex Token
  const token = await deployer.deploy(tokenArtifact, [
    config.feeRecipient // Initial owner only
  ]);

  await token.deployed();
  console.log("✅ GPUDex Token deployed to:", token.address);
  console.log("   Token Name:", config.tokenName);
  console.log("   Token Symbol:", config.tokenSymbol);
  console.log("   Initial Owner:", config.feeRecipient);

  console.log("\n🔒 Deploying GPUDex Escrow...");
  
  // Deploy GPUDex Escrow
  const escrow = await deployer.deploy(escrowArtifact, [
    config.feeRecipient,    // Fee recipient (platform owner)
    token.address           // GPUDX token address for staking
    // Platform fee is hardcoded to 3% in contract
  ]);

  await escrow.deployed();
  console.log("✅ GPUDex Escrow deployed to:", escrow.address);
  console.log("   Platform Fee: 3% (hardcoded in contract)");
  console.log("   Fee Recipient:", config.feeRecipient);
  console.log("   Staking Token:", token.address);

  // Output deployment info
  console.log("\n📋 Deployment Summary");
  console.log("========================");
  console.log(`Network: ${config.description}`);
  console.log(`Chain ID: ${chainId}`);
  console.log(`Token: ${token.address}`);
  console.log(`Escrow: ${escrow.address}`);
  console.log(`Fee Recipient: ${config.feeRecipient}`);
  
  // Environment variables for backend
  console.log("\n🔧 Backend Environment Variables:");
  console.log("=================================");
  console.log(`ESCROW_CONTRACT_ADDRESS=${escrow.address}`);
  console.log(`TOKEN_CONTRACT_ADDRESS=${token.address}`);
  console.log(`PLATFORM_FEE_RECIPIENT=${config.feeRecipient}`);
  console.log(`BLOCKCHAIN_NETWORK=zkSync`);
  console.log(`CHAIN_ID=${chainId}`);
  
  // Next steps
  console.log("\n🎯 Next Steps:");
  console.log("==============");
  console.log("1. Update your .env file with the contract addresses above");
  console.log("2. Restart your Docker containers:");
  console.log("   docker-compose -f docker-compose.prod.yml down");
  console.log("   docker-compose -f docker-compose.prod.yml up -d");
  console.log("3. Test GPU rental with ultra-low zkSync Era fees!");
  
  // Explorer links
  console.log("\n🔍 View on zkSync Era Explorer:");
  console.log("==============================");
  if (chainId === 324) {
    console.log(`Token: https://explorer.zksync.io/address/${token.address}`);
    console.log(`Escrow: https://explorer.zksync.io/address/${escrow.address}`);
  } else if (chainId === 280) {
    console.log(`Token: https://goerli.explorer.zksync.io/address/${token.address}`);
    console.log(`Escrow: https://goerli.explorer.zksync.io/address/${escrow.address}`);
  }

  console.log("\n✨ zkSync Era deployment completed successfully!");
  
  return {
    token: token.address,
    escrow: escrow.address,
    chainId,
    feeRecipient: config.feeRecipient
  };
}

// Handle both direct execution and hardhat tasks
if (require.main === module) {
  main()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error("❌ Deployment failed:", error);
      process.exit(1);
    });
}

module.exports = main; 