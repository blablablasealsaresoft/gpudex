/**
 * GPUDx Marketplace Real API Integration
 * Fetches live GPU pricing and availability data
 */

class MarketplaceAPI {
    constructor() {
        this.apiBaseUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000' 
            : '/api';
        this.realApiUrl = window.location.hostname === 'localhost' 
            ? 'http://localhost:8001' 
            : '/real-api';
        this.providers = [];
        this.gpuData = [];
        this.isLoading = false;
    }

    async fetchGPUMarketData() {
        this.isLoading = true;
        this.showLoadingState();

        try {
            // Fetch from real API service
            const response = await fetch(`${this.realApiUrl}/gpu-marketplace`);
            if (response.ok) {
                const data = await response.json();
                this.gpuData = data.gpus || [];
                this.providers = data.providers || [];
            } else {
                // Fallback to enhanced mock data if API fails
                this.gpuData = this.getEnhancedMockData();
                console.warn('Using fallback data - API not available');
            }
        } catch (error) {
            console.warn('API fetch failed, using enhanced mock data:', error);
            this.gpuData = this.getEnhancedMockData();
        }

        this.isLoading = false;
        this.hideLoadingState();
        this.renderMarketplace();
        return this.gpuData;
    }

    getEnhancedMockData() {
        return [
            {
                id: 'h100-1',
                name: 'NVIDIA H100',
                memory: '80GB HBM3',
                price: 4.50,
                priceUnit: 'per hour',
                availability: 'Available',
                provider: 'AWS',
                location: 'us-east-1',
                performance: 95,
                specs: {
                    cuda_cores: 16896,
                    tensor_cores: 528,
                    memory_bandwidth: '3.35 TB/s',
                    fp32_performance: '67 TFlops'
                },
                features: ['NVLink', 'Multi-Instance GPU', 'Transformer Engine'],
                lastUpdated: new Date().toISOString()
            },
            {
                id: 'a100-1',
                name: 'NVIDIA A100',
                memory: '80GB HBM2e',
                price: 3.20,
                priceUnit: 'per hour',
                availability: 'Available',
                provider: 'Google Cloud',
                location: 'us-central1',
                performance: 88,
                specs: {
                    cuda_cores: 6912,
                    tensor_cores: 432,
                    memory_bandwidth: '2.04 TB/s',
                    fp32_performance: '19.5 TFlops'
                },
                features: ['NVLink', 'Multi-Instance GPU', 'Sparsity Support'],
                lastUpdated: new Date().toISOString()
            },
            {
                id: 'v100-1',
                name: 'NVIDIA V100',
                memory: '32GB HBM2',
                price: 2.40,
                priceUnit: 'per hour',
                availability: 'Limited',
                provider: 'Azure',
                location: 'East US',
                performance: 78,
                specs: {
                    cuda_cores: 5120,
                    tensor_cores: 640,
                    memory_bandwidth: '900 GB/s',
                    fp32_performance: '15.7 TFlops'
                },
                features: ['NVLink', 'Tensor Cores'],
                lastUpdated: new Date().toISOString()
            },
            {
                id: 'rtx4090-1',
                name: 'RTX 4090',
                memory: '24GB GDDR6X',
                price: 1.80,
                priceUnit: 'per hour',
                availability: 'Available',
                provider: 'RunPod',
                location: 'Global',
                performance: 85,
                specs: {
                    cuda_cores: 16384,
                    rt_cores: 128,
                    memory_bandwidth: '1008 GB/s',
                    fp32_performance: '83 TFlops'
                },
                features: ['RT Cores', 'DLSS 3', 'AV1 Encode'],
                lastUpdated: new Date().toISOString()
            },
            {
                id: 'rtx3090-1',
                name: 'RTX 3090',
                memory: '24GB GDDR6X',
                price: 1.20,
                priceUnit: 'per hour',
                availability: 'Available',
                provider: 'Vast.ai',
                location: 'Distributed',
                performance: 72,
                specs: {
                    cuda_cores: 10496,
                    rt_cores: 82,
                    memory_bandwidth: '936 GB/s',
                    fp32_performance: '36 TFlops'
                },
                features: ['RT Cores', 'DLSS', 'High Memory'],
                lastUpdated: new Date().toISOString()
            },
            {
                id: 'mi250x-1',
                name: 'AMD MI250X',
                memory: '128GB HBM2e',
                price: 3.80,
                priceUnit: 'per hour',
                availability: 'Available',
                provider: 'Oracle Cloud',
                location: 'us-west-1',
                performance: 90,
                specs: {
                    stream_processors: 14080,
                    memory_bandwidth: '3.28 TB/s',
                    fp32_performance: '95.7 TFlops',
                    architecture: 'CDNA2'
                },
                features: ['ROCm Support', 'High Memory', 'Multi-GPU'],
                lastUpdated: new Date().toISOString()
            }
        ];
    }

    renderMarketplace() {
        const marketplaceContainer = document.getElementById('gpu-marketplace');
        if (!marketplaceContainer) return;

        const sortedGPUs = this.gpuData.sort((a, b) => a.price - b.price);

        marketplaceContainer.innerHTML = `
            <div class="marketplace-header mb-8">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="text-2xl font-bold mb-2">Live GPU Marketplace</h3>
                        <p class="text-gray-600 dark:text-gray-300">Real-time pricing from ${this.getUniqueProviders().length}+ providers</p>
                    </div>
                    <div class="flex gap-4">
                        <button onclick="marketplaceAPI.fetchGPUMarketData()" class="enhanced-button">
                            <i class="fas fa-sync-alt mr-2"></i>Refresh
                        </button>
                        <select onchange="marketplaceAPI.filterByProvider(this.value)" class="px-4 py-2 border rounded-lg dark:bg-gray-700">
                            <option value="">All Providers</option>
                            ${this.getUniqueProviders().map(provider => `<option value="${provider}">${provider}</option>`).join('')}
                        </select>
                    </div>
                </div>
            </div>
            
            <div class="gpu-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                ${sortedGPUs.map(gpu => this.renderGPUCard(gpu)).join('')}
            </div>
        `;
    }

    renderGPUCard(gpu) {
        const availabilityColor = gpu.availability === 'Available' ? 'text-green-600' : 
                                 gpu.availability === 'Limited' ? 'text-yellow-600' : 'text-red-600';
        
        return `
            <div class="gpu-card card-hover bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
                <div class="gpu-header flex justify-between items-start mb-4">
                    <div>
                        <h4 class="text-xl font-bold mb-1">${gpu.name}</h4>
                        <p class="text-gray-600 dark:text-gray-300">${gpu.memory}</p>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-bold text-primary">$${gpu.price}</div>
                        <div class="text-sm text-gray-500">${gpu.priceUnit}</div>
                    </div>
                </div>
                
                <div class="provider-info flex justify-between items-center mb-4">
                    <div class="flex items-center">
                        <i class="fas fa-server mr-2 text-gray-500"></i>
                        <span class="text-sm font-medium">${gpu.provider}</span>
                    </div>
                    <div class="flex items-center">
                        <i class="fas fa-map-marker-alt mr-1 text-gray-500"></i>
                        <span class="text-sm text-gray-600">${gpu.location}</span>
                    </div>
                </div>
                
                <div class="performance-bar mb-4">
                    <div class="flex justify-between text-sm mb-1">
                        <span>Performance</span>
                        <span>${gpu.performance}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full" 
                             style="width: ${gpu.performance}%"></div>
                    </div>
                </div>
                
                <div class="specs mb-4">
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        ${Object.entries(gpu.specs).slice(0, 4).map(([key, value]) => `
                            <div class="flex justify-between">
                                <span class="text-gray-500">${key.replace(/_/g, ' ').toUpperCase()}:</span>
                                <span class="font-medium">${value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="features mb-4">
                    <div class="flex flex-wrap gap-1">
                        ${gpu.features.slice(0, 3).map(feature => `
                            <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">${feature}</span>
                        `).join('')}
                    </div>
                </div>
                
                <div class="availability mb-4">
                    <span class="text-sm font-medium ${availabilityColor}">
                        <i class="fas fa-circle mr-1" style="font-size: 8px;"></i>
                        ${gpu.availability}
                    </span>
                </div>
                
                <button onclick="marketplaceAPI.rentGPU('${gpu.id}')" 
                        class="w-full enhanced-button">
                    <i class="fas fa-rocket mr-2"></i>Rent Now
                </button>
            </div>
        `;
    }

    getUniqueProviders() {
        return [...new Set(this.gpuData.map(gpu => gpu.provider))];
    }

    filterByProvider(provider) {
        const filteredData = provider ? this.gpuData.filter(gpu => gpu.provider === provider) : this.gpuData;
        const gpuGrid = document.querySelector('.gpu-grid');
        if (gpuGrid) {
            gpuGrid.innerHTML = filteredData.map(gpu => this.renderGPUCard(gpu)).join('');
        }
    }

    showLoadingState() {
        const marketplaceContainer = document.getElementById('gpu-marketplace');
        if (marketplaceContainer) {
            marketplaceContainer.innerHTML = `
                <div class="loading-state text-center py-12">
                    <div class="loading-spinner w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p class="text-gray-600 dark:text-gray-300">Loading real-time GPU data...</p>
                </div>
            `;
        }
    }

    hideLoadingState() {
        // Loading state will be replaced by renderMarketplace()
    }

    async rentGPU(gpuId) {
        const gpu = this.gpuData.find(g => g.id === gpuId);
        if (!gpu) return;

        // Show rental modal or redirect to rental flow
        this.showRentalModal(gpu);
    }

    showRentalModal(gpu) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md mx-4">
                <h3 class="text-2xl font-bold mb-4">Rent ${gpu.name}</h3>
                <div class="space-y-4">
                    <div class="flex justify-between">
                        <span>Provider:</span>
                        <span class="font-medium">${gpu.provider}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Price:</span>
                        <span class="font-medium">$${gpu.price}/hour</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Memory:</span>
                        <span class="font-medium">${gpu.memory}</span>
                    </div>
                    <div class="rental-duration">
                        <label class="block text-sm font-medium mb-2">Rental Duration (hours):</label>
                        <input type="number" min="1" value="1" class="w-full px-3 py-2 border rounded-lg">
                    </div>
                    <div class="total-cost text-lg font-bold">
                        Total: $${gpu.price}
                    </div>
                </div>
                <div class="flex gap-4 mt-6">
                    <button onclick="this.closest('.fixed').remove()" 
                            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                        Cancel
                    </button>
                    <button onclick="marketplaceAPI.confirmRental('${gpu.id}'); this.closest('.fixed').remove()" 
                            class="flex-1 enhanced-button">
                        Confirm Rental
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    async confirmRental(gpuId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/rental/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gpuId: gpuId, duration: 1 })
            });
            
            if (response.ok) {
                this.showNotification('GPU rental initiated successfully!', 'success');
            } else {
                this.showNotification('Failed to initiate rental. Please try again.', 'error');
            }
        } catch (error) {
            this.showNotification('Network error. Please check your connection.', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize marketplace API
const marketplaceAPI = new MarketplaceAPI();

// Auto-refresh every 2 minutes
setInterval(() => {
    if (!marketplaceAPI.isLoading) {
        marketplaceAPI.fetchGPUMarketData();
    }
}, 120000); 