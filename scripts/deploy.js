const { ethers, upgrades } = require("hardhat");

async function main() {
  // Get the deployer account
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());

  // Configuration for different networks
  const networkConfig = {
    // Removed zkSync networks - Using Polygon only
    // Polygon Mainnet (Alternative low-cost option)
    137: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || deployer.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token",
      tokenSymbol: "GPUDX",
      initialSupply: ethers.utils.parseEther("1000000000"), // 1B tokens
      description: "Polygon - Low fees sidechain"
    },
    // Ethereum Mainnet
    1: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || deployer.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token",
      tokenSymbol: "GPUDX", 
      initialSupply: ethers.utils.parseEther("1000000000"), // 1B tokens
      description: "Ethereum Mainnet - Maximum security, higher fees"
    },
    // Mumbai Testnet
    80001: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || deployer.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token (Testnet)",
      tokenSymbol: "GPUDX",
      initialSupply: ethers.utils.parseEther("1000000000"), // 1B tokens
      description: "Polygon Mumbai Testnet"
    },
    // Local/Hardhat
    31337: {
      feeRecipient: process.env.FEE_RECIPIENT_ADDRESS || deployer.address,
      platformFeePercent: 300, // 3%
      tokenName: "GPUDex Token (Local)",
      tokenSymbol: "GPUDX",
      initialSupply: ethers.utils.parseEther("1000000000"), // 1B tokens
      description: "Local Development"
    }
  };

  // Get network configuration
  const chainId = await hre.network.provider.send("eth_chainId");
  const config = networkConfig[parseInt(chainId, 16)] || networkConfig[31337];
  
  console.log("Network Chain ID:", parseInt(chainId, 16));
  console.log("Fee Recipient:", config.feeRecipient);
  console.log("Platform Fee:", config.platformFeePercent / 100, "%");

  // Deploy GPUDex Token first
  console.log("\n🪙 Deploying GPUDex Token...");
  const GPUDexToken = await ethers.getContractFactory("GPUDexToken");
  const token = await GPUDexToken.deploy(
    deployer.address // Initial owner only
  );
  await token.deployed();
  console.log("✅ GPUDex Token deployed to:", token.address);
  
  // Get actual total supply from contract
  const totalSupply = await token.totalSupply();
  console.log("   Total Supply:", ethers.utils.formatEther(totalSupply), "GPUDX");

  // Deploy GPUDex Escrow
  console.log("\n🔒 Deploying GPUDex Escrow...");
  const GPUDexEscrow = await ethers.getContractFactory("GPUDexEscrow");
  const escrow = await GPUDexEscrow.deploy(
    config.feeRecipient,    // Fee recipient (platform owner)
    token.address           // GPUDX token address for staking
    // Platform fee is hardcoded to 3% in contract
  );
  await escrow.deployed();
  console.log("✅ GPUDex Escrow deployed to:", escrow.address);
  console.log("   Platform Fee: 3% (hardcoded in contract)");

  // Verify deployment
  console.log("\n📋 Deployment Summary:");
  console.log("======================");
  console.log("Network:", hre.network.name);
  console.log("Chain ID:", parseInt(chainId, 16));
  console.log("Deployer:", deployer.address);
  console.log("Fee Recipient:", config.feeRecipient);
  console.log("");
  console.log("📦 Contract Addresses:");
  console.log("GPUDex Token (GPUDX):", token.address);
  console.log("GPUDex Escrow:", escrow.address);
  console.log("");
  console.log("⚙️ Configuration:");
  console.log("Platform Fee:", config.platformFeePercent / 100 + "%");
  console.log("Token Supply:", ethers.utils.formatEther(config.initialSupply), "GPUDX");
  console.log("Minimum Stake:", ethers.utils.formatEther(await escrow.minimumStake()), "GPUDX");

  // Save deployment addresses to file
  const fs = require('fs');
  const deploymentInfo = {
    network: hre.network.name,
    chainId: parseInt(chainId, 16),
    timestamp: new Date().toISOString(),
    deployer: deployer.address,
    feeRecipient: config.feeRecipient,
    contracts: {
      GPUDexToken: token.address,
      GPUDexEscrow: escrow.address
    },
    configuration: {
      platformFeePercent: config.platformFeePercent,
      tokenSupply: config.initialSupply.toString(),
      minimumStake: (await escrow.minimumStake()).toString()
    }
  };

  const fileName = `deployment-${hre.network.name}-${Date.now()}.json`;
  fs.writeFileSync(fileName, JSON.stringify(deploymentInfo, null, 2));
  console.log("\n💾 Deployment info saved to:", fileName);

  // Environment variables for backend
  console.log("\n🔧 Backend Environment Variables:");
  console.log("Add these to your .env file:");
  console.log("================================");
  console.log(`ESCROW_CONTRACT_ADDRESS=${escrow.address}`);
  console.log(`TOKEN_CONTRACT_ADDRESS=${token.address}`);
  console.log(`PLATFORM_FEE_RECIPIENT=${config.feeRecipient}`);
  console.log(`BLOCKCHAIN_NETWORK=${hre.network.name}`);
  console.log(`CHAIN_ID=${parseInt(chainId, 16)}`);

  // Contract verification instructions
  if (hre.network.name !== "localhost" && hre.network.name !== "hardhat") {
    console.log("\n🔍 Contract Verification:");
    console.log("Run these commands to verify on Etherscan/Polygonscan:");
    console.log("=======================================================");
    console.log(`npx hardhat verify --network ${hre.network.name} ${token.address} "${config.tokenName}" "${config.tokenSymbol}" "${config.initialSupply}" "${deployer.address}"`);
    console.log(`npx hardhat verify --network ${hre.network.name} ${escrow.address} "${config.feeRecipient}" "${token.address}" ${config.platformFeePercent}`);
  }

  console.log("\n🎉 Deployment Complete!");
  console.log("Your GPUDex platform is ready for production!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 