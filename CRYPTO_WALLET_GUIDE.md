# 🔗 GPUDex Crypto Wallet Payment Guide

**Connect Your Wallet & Pay with Crypto - No Registration Required!**

## 🎯 **Overview**

GPUDex now supports **Web3 crypto payments** through direct wallet connections. Users can connect MetaMask, Coinbase Wallet, or other Web3 wallets to pay for GPU rentals without creating accounts.

### **Key Benefits**
- ✅ **No registration required** - Connect wallet and pay instantly
- ✅ **1% crypto discount** on all payments
- ✅ **Secure & decentralized** payments via Coinbase Commerce
- ✅ **Multiple wallets supported** - MetaMask, Coinbase Wallet, WalletConnect
- ✅ **Real-time pricing** with crypto conversion

## 🚀 **How It Works**

### **1. Browse & Add to Cart**
- Browse real-time GPU prices from 15+ providers
- Add desired GPUs to shopping cart
- Select rental duration (1-168 hours)

### **2. Connect Your Wallet**
- Click **"Connect Wallet"** button
- Choose from supported wallets:
  - **MetaMask** (Most popular browser wallet)
  - **Coinbase Wallet** (Secure & easy to use)
  - **WalletConnect** (Connect mobile wallets)

### **3. Complete Payment**
- Review order with automatic 1% crypto discount
- Click **"Pay with Wallet & Save 1%"**
- Complete payment via Coinbase Commerce
- GPU rental begins immediately after confirmation

## 🔧 **Supported Wallets**

### **🦊 MetaMask**
- **Installation**: [metamask.io](https://metamask.io/download/)
- **Networks**: Ethereum mainnet
- **Best for**: Desktop users, DeFi enthusiasts

### **🔵 Coinbase Wallet**
- **Installation**: [coinbase.com/wallet](https://www.coinbase.com/wallet)
- **Networks**: Ethereum, Polygon, and more
- **Best for**: Beginners, Coinbase users

### **🔗 WalletConnect**
- **Usage**: Connect mobile wallets via QR code
- **Supported**: Trust Wallet, Rainbow, MetaMask Mobile
- **Best for**: Mobile wallet users

## 💰 **Payment Process**

### **Cart Summary**
```
Subtotal:           $12.50
Crypto Discount:    -$0.13 (1%)
Total:              $12.37
```

### **Crypto Payment Flow**
1. **Wallet Connection**: Connect your preferred crypto wallet
2. **Order Review**: Confirm GPU rental details with crypto discount
3. **Coinbase Commerce**: Secure payment processing
4. **Real-time Conversion**: USD amount converted to ETH/BTC
5. **Payment Confirmation**: GPU rental activated upon payment

### **Supported Cryptocurrencies**
- **Ethereum (ETH)** - Primary payment method
- **Bitcoin (BTC)** - Alternative option
- **USD Coin (USDC)** - Stablecoin payments
- **More cryptos** via Coinbase Commerce

## 🛠️ **Technical Implementation**

### **Frontend (Web3 Integration)**
```javascript
// Wallet connection
async function connectMetaMask() {
    await window.ethereum.request({ method: 'eth_requestAccounts' });
    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
    // Handle wallet connection
}

// Payment processing
async function processCryptoPayment(amount) {
    const response = await fetch('/api/v1/crypto/coinbase-payment', {
        method: 'POST',
        body: JSON.stringify({
            amount_usd: amount,
            wallet_address: walletAddress,
            wallet_type: connectedWallet
        })
    });
}
```

### **Backend (Coinbase Commerce)**
```python
# Coinbase Commerce integration
class CoinbaseCommerceService:
    async def create_charge(self, payment_request):
        charge_data = {
            "name": f"GPU Rental - {len(items)} items",
            "pricing_type": "fixed_price",
            "local_price": {"amount": str(amount_usd), "currency": "USD"}
        }
        # Create charge via Coinbase Commerce API
```

## 🔒 **Security Features**

### **Wallet Security**
- **Private keys** remain in your wallet (never shared)
- **Secure transactions** via Web3 standards
- **Wallet verification** through cryptographic signatures
- **No sensitive data** stored on GPUDex servers

### **Payment Security**
- **Coinbase Commerce** handles all crypto transactions
- **Webhook verification** for payment confirmation
- **Transaction monitoring** and fraud prevention
- **Secure communication** via HTTPS/WSS

## 🚨 **Troubleshooting**

### **Wallet Connection Issues**

**❌ "MetaMask not detected"**
```bash
Solution: Install MetaMask extension
URL: https://metamask.io/download/
```

**❌ "Transaction failed"**
```bash
Solution: Check wallet balance and gas fees
Ensure sufficient ETH for transaction + gas
```

**❌ "Network mismatch"**
```bash
Solution: Switch to Ethereum mainnet
MetaMask > Networks > Ethereum Mainnet
```

### **Payment Issues**

**❌ "Payment not confirming"**
```bash
Solution: Check transaction on blockchain
Use wallet's transaction history
Wait for network confirmation (1-3 blocks)
```

**❌ "Crypto discount not applied"**
```bash
Solution: Ensure wallet is connected
Refresh page and reconnect wallet
Discount applies automatically at checkout
```

## 📊 **Price Examples**

### **Real-Time Crypto Pricing**
| GPU Type | USD Price | ETH Price | BTC Price | Savings |
|----------|-----------|-----------|-----------|---------|
| RTX 4090 | $0.45/hr | 0.000225 ETH | 0.0000045 BTC | 1% |
| H100 | $1.49/hr | 0.000745 ETH | 0.0000149 BTC | 1% |
| A100 | $3.20/hr | 0.0016 ETH | 0.000032 BTC | 1% |

*Prices updated every 30 seconds with live crypto conversion*

## 🔮 **Roadmap**

### **Coming Soon**
- [ ] **Multi-chain support** (Polygon, BSC, Solana)
- [ ] **DeFi integrations** (Uniswap, 1inch)
- [ ] **NFT-based access tokens** for premium features
- [ ] **DAO governance** for platform decisions
- [ ] **Yield farming** with GPU rental rewards

### **Advanced Features**
- [ ] **Smart contract payments** for automated rentals
- [ ] **Subscription payments** via crypto streams
- [ ] **Escrow services** for long-term rentals
- [ ] **Cross-chain bridges** for seamless payments

## 🔗 **API Documentation**

### **Coinbase Commerce Endpoints**
```bash
POST /api/v1/crypto/coinbase-payment    # Create payment charge
GET  /api/v1/crypto/payment-status/{id} # Check payment status
POST /api/v1/crypto/coinbase-webhook    # Handle payment webhooks
```

### **Wallet Integration**
```javascript
// Check wallet connection
const isConnected = localStorage.getItem('walletAddress');

// Get wallet balance
const balance = await web3.eth.getBalance(walletAddress);

// Sign transaction
const signature = await web3.eth.personal.sign(message, walletAddress);
```

## 📞 **Support**

### **Need Help?**
- **Wallet Issues**: Check wallet documentation
- **Payment Problems**: Verify blockchain transaction
- **Technical Support**: Contact GPUDex team
- **Feature Requests**: Submit via GitHub issues

### **Resources**
- **MetaMask Guide**: [docs.metamask.io](https://docs.metamask.io)
- **Coinbase Wallet**: [wallet.coinbase.com/help](https://wallet.coinbase.com/help)
- **Ethereum Network**: [ethereum.org](https://ethereum.org)
- **Gas Tracker**: [ethgasstation.info](https://ethgasstation.info)

---

## 🎉 **Get Started Now**

**Ready to pay with crypto?**

1. **Connect your wallet** at http://localhost:3000
2. **Browse GPUs** and add to cart
3. **Pay with crypto** and save 1%
4. **Start your rental** immediately!

---

*GPUDex - Making AI/ML compute accessible through Web3 payments* 🚀 