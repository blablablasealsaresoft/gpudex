# GPUDex - GPU Price Aggregator

Real-time GPU price aggregation across 15+ providers. Find the best GPU prices instantly and save up to 70% on compute costs.

## 🚀 Live Demo

- **Frontend**: https://gpudex.vercel.app/
- **Backend API**: https://gpudex.onrender.com/
- **GitHub**: https://github.com/blablablasealsaresoft/gpudex

## 🎯 What is GPUDex?

GPUDex is the "1inch of Compute" - aggregating fragmented GPU compute providers to find optimal allocation paths. Just as 1inch aggregates DEX liquidity, we aggregate GPU compute to find the best prices across multiple providers.

### Key Features

- **Real-time Price Aggregation**: Live prices from 5+ major GPU providers
- **Smart Routing**: Find the optimal GPU allocation for your workload
- **Price History**: Track price trends and identify the best times to deploy
- **Arbitrage Detection**: Automatically detect price differences between providers
- **Price Alerts**: Get notified when prices drop below your target
- **Developer API**: Integrate GPU price aggregation into your applications

## 🏗️ Architecture

```
Frontend (Vercel) ←→ Backend API (Render) ←→ GPU Providers
     ↓                    ↓                        ↓
  React/HTML         FastAPI/Python         Vast.ai, RunPod,
                     PostgreSQL             TensorDock, etc.
```

## 🛠️ Local Development Setup

### Prerequisites

- Python 3.8+
- Node.js (for frontend development)
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/blablablasealsaresoft/gpudex.git
   cd gpudex/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   echo "DATABASE_URL=sqlite:///./gpudex.db" > .env
   echo "ENVIRONMENT=development" >> .env
   ```

4. **Run the backend**
   ```bash
   python start.py
   ```

5. **Test the API**
   ```bash
   python test_api.py
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../frontend
   ```

2. **Open index.html in your browser**
   - Or serve with a local server: `python -m http.server 3000`

## 📊 API Endpoints

### Core Endpoints

- `GET /` - Health check
- `GET /api/v1/prices?gpu={type}&region={region}` - Get aggregated prices
- `GET /api/v1/providers` - List all providers
- `GET /api/v1/analytics` - Market analytics

### Advanced Endpoints

- `GET /api/v1/history/{gpu_type}` - Price history
- `GET /api/v1/providers/{provider}/stats` - Provider statistics
- `POST /api/v1/alerts` - Create price alerts

### Example API Usage

```bash
# Get RTX 4090 prices
curl "https://gpudex.onrender.com/api/v1/prices?gpu=4090&region=us-east"

# Get price history
curl "https://gpudex.onrender.com/api/v1/history/4090?hours=24"

# Create price alert
curl -X POST "https://gpudex.onrender.com/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","gpu_type":"4090","target_price":0.30}'
```

## 🚀 Deployment

### Backend (Render)

1. **Connect your GitHub repository to Render**
2. **Create a new Web Service**
3. **Configure the service:**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python start.py`
   - **Environment Variables**:
     - `DATABASE_URL`: Your PostgreSQL connection string
     - `ENVIRONMENT`: `production`

### Frontend (Vercel)

1. **Connect your GitHub repository to Vercel**
2. **Configure the build:**
   - **Framework Preset**: Other
   - **Build Command**: (leave empty)
   - **Output Directory**: `frontend`
   - **Install Command**: (leave empty)

## 📈 Supported Providers

Currently integrated:
- **Vast.ai** - Spot instances with real-time pricing
- **RunPod** - On-demand GPU instances
- **TensorDock** - Interruptible instances
- **Lambda Labs** - Reserved instances
- **Paperspace** - On-demand instances

Coming soon:
- AWS EC2 GPU instances
- Google Cloud GPU instances
- Azure GPU instances
- And 10+ more providers

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Basic price aggregation
- ✅ Real-time API
- ✅ Price history tracking
- ✅ Alert system

### Phase 2 (Next 2 weeks)
- [ ] Add 10+ more providers
- [ ] Advanced routing algorithms
- [ ] Mobile app
- [ ] API key management

### Phase 3 (Next month)
- [ ] One-click deployment
- [ ] Cost optimization recommendations
- [ ] Provider reliability scoring
- [ ] Enterprise features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

- **Email**: hello@gpudex.io
- **Website**: https://gpudex.vercel.app/
- **GitHub**: https://github.com/blablablasealsaresoft/gpudex

## 🙏 Acknowledgments

- Inspired by 1inch's DEX aggregation model
- Built with FastAPI, React, and modern web technologies
- Special thanks to the GPU provider APIs that make this possible

---

**Aggregate. Compare. Deploy. Save 70% on GPU costs.**

*"In 2025, every AI company will need GPUs. In 2026, they'll all use GPUDex to find them."*