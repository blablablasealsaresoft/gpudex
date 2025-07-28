#!/bin/bash

echo "🔥 GPUDx Contracts Fix Script - BILL VS THE FINAL BOSS!"
echo "======================================================="

echo "🛑 Stopping existing contract services..."
docker compose stop contract_deployer hardhat_node

echo "🗑️ Removing old containers..."
docker compose rm -f contract_deployer hardhat_node

echo "🔨 Rebuilding contract services with Node.js 20 fixes..."
docker compose build --no-cache contract_deployer hardhat_node

echo "🚀 Starting Hardhat node first..."
docker compose up -d hardhat_node

echo "⏳ Waiting for Hardhat node to be ready..."
sleep 15

echo "🔍 Checking Hardhat node status..."
docker compose logs hardhat_node --tail 10

echo "🌐 Testing Hardhat node connectivity..."
curl -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545 || echo "❌ Hardhat node not responding"

echo "📊 Starting contract deployment..."
docker compose up contract_deployer

echo "🔍 Checking deployment logs..."
docker compose logs contract_deployer --tail 20

echo "📋 Final status check..."
echo "========================"
echo "🔗 Hardhat Node Status:"
docker compose ps hardhat_node

echo "📜 Contract Deployer Status:"  
docker compose ps contract_deployer

echo "📁 Checking artifacts directory..."
ls -la artifacts/ 2>/dev/null || echo "❌ No artifacts directory found"

echo "🔍 Checking generated files..."
if [ -f "frontend/contracts-config.js" ]; then
    echo "✅ Frontend config generated"
    head -10 frontend/contracts-config.js
else
    echo "❌ Frontend config not generated"
fi

if [ -f ".env.contracts" ]; then
    echo "✅ Contract environment file generated"
    cat .env.contracts
else
    echo "❌ Contract environment file not generated"
fi

echo ""
echo "🎯 Success Indicators:"
echo "======================"
echo "✅ Should see: 'Contract deployment completed!'"
echo "✅ Should see: Deployed contract addresses"
echo "✅ Should see: Updated docker-compose.yml"
echo "✅ Should see: Generated frontend/contracts-config.js"
echo ""

if docker compose logs contract_deployer | grep -q "Contract deployment completed!"; then
    echo "🎉 SUCCESS: Contract deployment completed!"
    echo "🔥 BILL HAS DEFEATED THE FINAL BOSS!"
else
    echo "⚠️  Check the logs above for any remaining issues"
    echo "💪 BILL NEVER GIVES UP!"
fi

echo ""
echo "🔧 If issues persist, run these debug commands:"
echo "docker compose logs hardhat_node"
echo "docker compose logs contract_deployer"
echo "docker exec -it gpudx_contracts sh"
echo "" 