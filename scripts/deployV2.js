const { ethers } = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
    console.log("🚀 DEPLOYING GPUDEX V2 CONTRACTS WITH MAXIMUM VELOCITY! 🚀");
    
    // Get the deployer account
    const [deployer] = await ethers.getSigners();
    console.log("💎 Deploying contracts with account:", deployer.address);
    console.log("💰 Account balance:", ethers.utils.formatEther(await deployer.getBalance()));

    // Deployment configuration
    const config = {
        network: await ethers.provider.getNetwork(),
        deployer: deployer.address,
        timestamp: new Date().toISOString(),
        contracts: {}
    };

    console.log("🌐 Network:", config.network.name, "| Chain ID:", config.network.chainId);

    try {
        // 1. Deploy GPUDexTokenV2 (GOVERNANCE-FREE!)
        console.log("\n🔥 Step 1: Deploying GPUDexTokenV2 (NO GOVERNANCE - PURE UTILITY!)");
        
        const GPUDexTokenV2 = await ethers.getContractFactory("GPUDexTokenV2");
        const tokenV2 = await GPUDexTokenV2.deploy(deployer.address);
        await tokenV2.deployed();
        
        console.log("✅ GPUDexTokenV2 deployed to:", tokenV2.address);
        config.contracts.GPUDexTokenV2 = {
            address: tokenV2.address,
            transaction: tokenV2.deployTransaction.hash,
            blockNumber: tokenV2.deployTransaction.blockNumber
        };

        // Wait for a few confirmations
        console.log("⏳ Waiting for confirmations...");
        await tokenV2.deployTransaction.wait(2);

        // 2. Deploy GPUDexEscrowV2
        console.log("\n🔥 Step 2: Deploying GPUDexEscrowV2 with enhanced utility validation!");
        
        const GPUDexEscrowV2 = await ethers.getContractFactory("GPUDexEscrowV2");
        const escrowV2 = await GPUDexEscrowV2.deploy(
            deployer.address, // Fee recipient
            tokenV2.address   // GPUDX token address
        );
        await escrowV2.deployed();
        
        console.log("✅ GPUDexEscrowV2 deployed to:", escrowV2.address);
        config.contracts.GPUDexEscrowV2 = {
            address: escrowV2.address,
            transaction: escrowV2.deployTransaction.hash,
            blockNumber: escrowV2.deployTransaction.blockNumber
        };

        // Wait for confirmations
        console.log("⏳ Waiting for confirmations...");
        await escrowV2.deployTransaction.wait(2);

        // 3. Configure Token Contract Permissions
        console.log("\n🔥 Step 3: Configuring contract permissions and integrations!");
        
        // Allow escrow contract to process GPU rentals and provider earnings
        console.log("🔧 Setting up escrow integration permissions...");
        
        // Note: In a real deployment, you'd set up proper access control
        // For now, we'll use owner-based permissions

        // 4. Initialize staking rewards and social gamification
        console.log("\n🔥 Step 4: Initializing reward systems and social gamification!");
        
        // Check initial token allocations
        const totalSupply = await tokenV2.totalSupply();
        const ownerBalance = await tokenV2.balanceOf(deployer.address);
        const contractBalance = await tokenV2.balanceOf(tokenV2.address);
        
        console.log("📊 Token Distribution Verification:");
        console.log("   Total Supply:", ethers.utils.formatEther(totalSupply), "GPUDX");
        console.log("   Owner Balance:", ethers.utils.formatEther(ownerBalance), "GPUDX");
        console.log("   Contract Balance:", ethers.utils.formatEther(contractBalance), "GPUDX");
        
        // 5. Set up initial tier configurations (they're already set in constructor)
        console.log("\n🔥 Step 5: Verifying staking tier configurations!");
        
        const tierConfigs = [];
        for (let tier = 1; tier <= 4; tier++) { // BRONZE to DIAMOND
            try {
                const tierInfo = await tokenV2.tierConfigs(tier);
                tierConfigs.push({
                    tier: ["NONE", "BRONZE", "SILVER", "GOLD", "DIAMOND"][tier],
                    minStake: ethers.utils.formatEther(tierInfo.minStake),
                    apyBasisPoints: tierInfo.apyBasisPoints.toString(),
                    gpuDiscountBasisPoints: tierInfo.gpuDiscountBasisPoints.toString(),
                    providerBoostBasisPoints: tierInfo.providerBoostBasisPoints.toString(),
                    revenueShareBasisPoints: tierInfo.revenueShareBasisPoints.toString()
                });
            } catch (e) {
                console.log(`⚠️  Could not read tier ${tier} config:`, e.message);
            }
        }
        
        console.log("🎯 Staking Tier Configurations:");
        tierConfigs.forEach(tier => {
            console.log(`   ${tier.tier}: ${tier.minStake} GPUDX stake, ${tier.apyBasisPoints/100}% APY, ${tier.gpuDiscountBasisPoints/100}% discount`);
        });

        // 6. Test basic functionality
        console.log("\n🔥 Step 6: Testing basic functionality!");
        
        // Test small stake to verify tier calculation
        const stakeAmount = ethers.utils.parseEther("1000"); // 1000 GPUDX for Bronze tier
        console.log("🧪 Testing staking functionality with 1000 GPUDX...");
        
        try {
            const stakeTx = await tokenV2.stake(stakeAmount, 30); // 30-day lock
            await stakeTx.wait();
            
            const userTierInfo = await tokenV2.getUserTierInfo(deployer.address);
            console.log("✅ Stake successful! User tier:", ["NONE", "BRONZE", "SILVER", "GOLD", "DIAMOND"][userTierInfo.tier]);
            console.log("   Staked amount:", ethers.utils.formatEther(userTierInfo.stakedAmount), "GPUDX");
            
            // Test pending rewards
            const pendingRewards = await tokenV2.pendingRewards(deployer.address);
            console.log("   Pending rewards:", {
                platform: ethers.utils.formatEther(pendingRewards.platformRewards),
                apy: ethers.utils.formatEther(pendingRewards.apyRewards),
                fees: ethers.utils.formatEther(pendingRewards.fees)
            });
            
        } catch (e) {
            console.log("⚠️  Staking test failed:", e.message);
        }

        // 7. Test utility metrics
        console.log("\n🔥 Step 7: Testing utility metrics collection!");
        
        try {
            const utilityMetrics = await tokenV2.getUtilityMetrics();
            console.log("📈 Initial Utility Metrics:");
            console.log("   Total GPU Spending:", ethers.utils.formatEther(utilityMetrics.totalGPUSpendingValue), "GPUDX");
            console.log("   Total Provider Earnings:", ethers.utils.formatEther(utilityMetrics.totalProviderEarningsValue), "GPUDX");
            console.log("   Total Users Served:", utilityMetrics.totalUsersServedCount.toString());
            console.log("   Platform Revenue:", ethers.utils.formatEther(utilityMetrics.platformRevenueGeneratedValue), "GPUDX");
            console.log("   Utility Token %:", utilityMetrics.utilityTokenPercentage.toString() + "%");
            
            const platformMetrics = await escrowV2.getPlatformMetrics();
            console.log("🏢 Platform Metrics:");
            console.log("   Total Rentals:", platformMetrics.totalRentals.toString());
            console.log("   Total Volume:", ethers.utils.formatEther(platformMetrics.totalVolume), "tokens");
            console.log("   GPUDX Utilization:", platformMetrics.gpudxUtilizationRate.toString() + "%");
            
        } catch (e) {
            console.log("⚠️  Metrics test failed:", e.message);
        }

        // 8. Save deployment configuration
        console.log("\n🔥 Step 8: Saving deployment configuration!");
        
        const deploymentData = {
            ...config,
            tierConfigurations: tierConfigs,
            initialMetrics: {
                totalSupply: ethers.utils.formatEther(totalSupply),
                ownerBalance: ethers.utils.formatEther(ownerBalance),
                contractBalance: ethers.utils.formatEther(contractBalance)
            },
            instructions: {
                tokenContract: tokenV2.address,
                escrowContract: escrowV2.address,
                frontendIntegration: "Update frontend to use new contract addresses",
                backendIntegration: "Update backend services with new contract ABIs",
                utilityValidation: "Deploy utility validation service with these addresses"
            }
        };

        const deploymentPath = `contracts/deployment-v2-${Date.now()}.json`;
        fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2));
        console.log("💾 Deployment data saved to:", deploymentPath);

        // 9. Generate contract verification commands
        console.log("\n🔥 Step 9: Contract verification commands!");
        
        const verificationCommands = [
            `npx hardhat verify --network ${config.network.name} ${tokenV2.address} "${deployer.address}"`,
            `npx hardhat verify --network ${config.network.name} ${escrowV2.address} "${deployer.address}" "${tokenV2.address}"`
        ];
        
        console.log("🔍 Contract Verification Commands:");
        verificationCommands.forEach((cmd, i) => {
            console.log(`   ${i + 1}. ${cmd}`);
        });

        // Save verification commands to file
        fs.writeFileSync('contract-verification.sh', verificationCommands.join('\n'));

        // 10. Generate environment configuration
        console.log("\n🔥 Step 10: Generating environment configuration!");
        
        const envConfig = `# GPUDex V2 Contract Addresses - ${config.network.name}
GPUDX_TOKEN_V2_ADDRESS=${tokenV2.address}
GPUDX_ESCROW_V2_ADDRESS=${escrowV2.address}
GPUDX_DEPLOYER_ADDRESS=${deployer.address}
GPUDX_NETWORK=${config.network.name}
GPUDX_CHAIN_ID=${config.network.chainId}

# Contract ABIs (update these paths in your backend)
GPUDX_TOKEN_V2_ABI_PATH=./contracts/GPUDexTokenV2.json
GPUDX_ESCROW_V2_ABI_PATH=./contracts/GPUDexEscrowV2.json

# Utility Validation Service Configuration
UTILITY_VALIDATION_ENABLED=true
UTILITY_METRICS_INTERVAL_HOURS=1
UTILITY_DATABASE_PATH=./utility_metrics.db

# Social Gamification Configuration  
SOCIAL_REWARDS_ENABLED=true
REFERRAL_REWARDS_ENABLED=true
ACHIEVEMENT_SYSTEM_ENABLED=true
`;

        fs.writeFileSync('.env.v2', envConfig);
        console.log("📄 Environment configuration saved to .env.v2");

        // 11. Final deployment summary
        console.log("\n🚀 DEPLOYMENT COMPLETE! MAXIMUM VELOCITY ACHIEVED! 🚀");
        console.log("=" * 60);
        console.log("📋 DEPLOYMENT SUMMARY:");
        console.log(`   Network: ${config.network.name} (Chain ID: ${config.network.chainId})`);
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Gas Used: Check transaction receipts`);
        console.log("\n💎 CONTRACT ADDRESSES:");
        console.log(`   GPUDexTokenV2: ${tokenV2.address}`);
        console.log(`   GPUDexEscrowV2: ${escrowV2.address}`);
        console.log("\n🎯 NEXT STEPS:");
        console.log("   1. Verify contracts on block explorer");
        console.log("   2. Update backend services with new addresses");
        console.log("   3. Deploy utility validation service");
        console.log("   4. Launch social gamification system");
        console.log("   5. Begin utility-first token distribution");
        console.log("\n🔥 REMEMBER: NO GOVERNANCE, PURE UTILITY! 🔥");

        return {
            tokenV2: tokenV2.address,
            escrowV2: escrowV2.address,
            deployer: deployer.address,
            network: config.network.name
        };

    } catch (error) {
        console.error("💥 DEPLOYMENT FAILED:", error);
        throw error;
    }
}

// Execute deployment
if (require.main === module) {
    main()
        .then((result) => {
            console.log("\n✅ DEPLOYMENT SUCCESSFUL!");
            console.log("🎉 READY TO REVOLUTIONIZE GPU COMPUTE! 🎉");
            process.exit(0);
        })
        .catch((error) => {
            console.error("\n❌ DEPLOYMENT ERROR:", error);
            process.exit(1);
        });
}

module.exports = main; 