# GPUDex Beta - Decentralized GPU Marketplace 🚀

![GPUDex Beta](https://img.shields.io/badge/Status-Beta-blue)
![Platform](https://img.shields.io/badge/Platform-Web3-green)
![Blockchain](https://img.shields.io/badge/Blockchain-Polygon-purple)

**GPUDex** is a decentralized GPU marketplace that aggregates compute resources from multiple providers, allowing users to rent GPUs with cryptocurrency payments at competitive rates.

## 🌟 Current Status: **Production Ready & Live**

### ✅ **Fully Working Components**
- **Frontend**: Complete Uniswap-style interface with navigation, marketplace, analytics
- **Backend API**: All endpoints live with 93+ GPUs from real providers  
- **GPU Marketplace**: Real-time pricing from Vast.ai, Lambda Labs, GCP, Azure, etc.
- **Analytics Dashboard**: Live charts and statistics
- **Wallet Integration**: MetaMask, Coinbase Wallet, WalletConnect
- **Enterprise API**: Key management and usage tracking
- **Monitoring**: Grafana + Prometheus dashboards
- **Database**: PostgreSQL with Redis caching

### 🚧 **In Development** 
- **Smart Contracts**: Ready for deployment (written and tested)
- **Cross-Chain Payments**: ETH L1 → Polygon bridge (coming soon)


## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js (for smart contracts)
- Web3 wallet (MetaMask, Coinbase Wallet)

### 1. Clone Repository
```bash
git clone https://github.com/your-username/gpudex
cd gpudex
```

### 2. Environment Setup
```bash
cp production.env.template docker-quickstart.env
# Edit docker-quickstart.env with your API keys and wallet address
```

### 3. Launch Platform
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Access Platform
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/docs
- **Monitoring**: http://localhost:3001 (Grafana)

## 🏗️ Architecture

### **Frontend** (React + Web3)
- Uniswap-inspired UI/UX
- Multi-wallet support (MetaMask, Coinbase, WalletConnect)
- Real-time GPU pricing and availability
- Smart contract integration

### **Backend** (Python FastAPI)
- GPU provider integrations (10+ services)
- Enterprise API management
- Real-time monitoring and alerts
- Payment processing

### **Blockchain** (Polygon)
- **Escrow Contract**: `0xE0107C4227A38Aae3E5163D691EFb0dc0Eb7598C`
- **GPUDX Token**: `0x386FF386B396ca139E5D2dB6d0b61a0FDd5b4b47`
- **Platform Fee**: 3% automatic collection
- **Security**: OpenZeppelin standards

### **Infrastructure**
- **Database**: PostgreSQL with comprehensive schema
- **Cache**: Redis for performance
- **Monitoring**: Prometheus + Grafana
- **Proxy**: Nginx with load balancing

## 💼 Supported GPU Providers

| Provider | Status | Features |
|----------|--------|----------|
| Vast.ai | ✅ Live | Competitive pricing, global availability |
| RunPod | ✅ Live | High-performance instances |
| Lambda Labs | ✅ Live | ML-optimized GPUs |
| AWS EC2 | ✅ Live | Enterprise-grade reliability |
| Google Cloud | ✅ Live | TPU and GPU options |
| Paperspace | ✅ Live | Developer-friendly |
| Genesis Cloud | ✅ Live | European infrastructure |
| And more... | ✅ Live | Expanding network |

## 🔐 Security Features

- **Smart Contract Security**: OpenZeppelin standards
- **API Security**: Rate limiting, authentication
- **Key Management**: Hashed storage, scoped access
- **Network Security**: SSL/TLS, firewall configuration
- **Monitoring**: Real-time alerts and logging

## 📊 Business Model

### **Revenue Streams**
1. **Platform Fee**: 3% on all GPU rentals (automatic via smart contract)
2. **Enterprise API**: Subscription-based access
3. **Premium Features**: Advanced analytics, priority support

### **Fee Distribution**
- **Platform**: 3% (to fee recipient wallet)
- **Provider**: 97% (direct payment)
- **User**: Transparent pricing with no hidden fees

## 🚀 Deployment

### **Production Deployment** (Docker)
```bash
# 1. Configure environment
cp production.env.template .env
# Edit .env with production values

# 2. Deploy smart contracts
cd contracts
npm install
npm run deploy:polygon

# 3. Start production services
docker-compose -f docker-compose.prod.yml up -d

# 4. Monitor health
docker ps
curl http://localhost:3000  # Frontend
curl http://localhost:8000/health  # Backend
```

### **Smart Contract Deployment**
```bash
cd contracts
npm install
npm run compile
npm run deploy:polygon
npm run verify:polygon
```

## 🔧 Configuration

### **Environment Variables**
Key configuration in `docker-quickstart.env`:
```bash
# Blockchain
PRIVATE_KEY=your_wallet_private_key
FEE_RECIPIENT_ADDRESS=your_fee_collection_wallet
POLYGON_RPC_URL=https://polygon-rpc.com/

# API Keys
VAST_API_KEY=your_vast_api_key
LAMBDA_API_KEY=your_lambda_api_key
RUNPOD_API_KEY=your_runpod_api_key

# Platform
DOMAIN=your-domain.com
ENVIRONMENT=production
```

## 📈 Monitoring & Analytics

### **Grafana Dashboards**
- GPU utilization and pricing trends
- Platform transaction volume
- Provider performance metrics
- User engagement analytics

### **Prometheus Metrics**
- API response times
- Database performance
- Container health
- Network traffic

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Development Setup**
```bash
# Frontend development
cd frontend
npm install
npm start

# Backend development
cd backend
pip install -r requirements.txt
python -m uvicorn api:app --reload

# Smart contract development
cd contracts
npm install
npx hardhat compile
npx hardhat test
```

## 📚 Documentation

- **[Production Deployment Guide](docs/production_deployment.md)**
- **[Smart Contract Documentation](contracts/README.md)**
- **[API Documentation](http://localhost:8000/docs)** (when running)
- **[Enterprise API Setup](ENTERPRISE_API.md)**

## 🛣️ Roadmap

### **Phase 1: Beta Launch** ✅
- [x] Core marketplace functionality
- [x] Polygon smart contracts
- [x] Multi-provider integration
- [x] Basic monitoring

### **Phase 2: Cross-Chain** 🚧
- [ ] ETH L1 → Polygon bridge

- [ ] Multi-chain support

### **Phase 3: Enterprise** 🔄
- [ ] Advanced analytics
- [ ] Custom dashboards
- [ ] White-label solutions
- [ ] API marketplace

### **Phase 4: Scale** 📈
- [ ] Additional blockchains
- [ ] Mobile applications
- [ ] Global expansion
- [ ] Governance token

## 📞 Support

- **Email**: support@gpudex.ai
- **Discord**: [Join our community](https://discord.gg/gpudex)
- **Documentation**: [docs.gpudex.ai](https://docs.gpudex.ai)
- **Status Page**: [status.gpudex.ai](https://status.gpudex.ai)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ by the GPUDex Team** | [Website](https://gpudex.ai) | [Twitter](https://twitter.com/gpudex) | [GitHub](https://github.com/gpudex)