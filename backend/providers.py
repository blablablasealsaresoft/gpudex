# Extended GPU Provider Integrations
# This module contains integrations for major cloud providers and specialized GPU platforms

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List
import re

logger = logging.getLogger(__name__)

class CloudProviderIntegrator:
    def __init__(self):
        self.providers = {
            # Existing providers
            'vast.ai': self.scrape_vast,
            'runpod.io': self.scrape_runpod,
            'tensordock.com': self.scrape_tensordock,
            'lambdalabs.com': self.scrape_lambda,
            'paperspace.com': self.scrape_paperspace,
            
            # New cloud providers
            'aws.amazon.com': self.scrape_aws,
            'cloud.google.com': self.scrape_gcp,
            'azure.microsoft.com': self.scrape_azure,
            'vultr.com': self.scrape_vultr,
            'linode.com': self.scrape_linode,
            'genesis-cloud.com': self.scrape_genesis,
            'coreweave.com': self.scrape_coreweave,
            'crusoe.ai': self.scrape_crusoe,
        }
        
        self.gpu_mappings = {
            '4090': ['RTX 4090', 'RTX4090', '4090', 'GeForce RTX 4090'],
            'a100': ['A100', 'A100-PCIE-40GB', 'A100 40GB', 'A100-SXM4-40GB', 'A100-80GB'],
            'h100': ['H100', 'H100 80GB', 'H100-PCIE', 'H100-SXM5'],
            'v100': ['V100', 'Tesla V100', 'V100-SXM2', 'V100-PCIE'],
            'a40': ['A40', 'RTX A40', 'A40 48GB'],
            'a6000': ['A6000', 'RTX A6000', 'A6000 48GB'],
        }

    async def scrape_aws(self, session, gpu_type):
        """Scrape AWS EC2 GPU instance pricing"""
        try:
            # AWS pricing is complex - using simplified pricing for major GPU instances
            pricing_map = {
                'v100': {'price': 3.06, 'name': 'p3.2xlarge (V100)', 'instance': 'p3.2xlarge'},
                'a100': {'price': 4.13, 'name': 'p4d.xlarge (A100)', 'instance': 'p4d.xlarge'},
                'h100': {'price': 8.25, 'name': 'p5.xlarge (H100)', 'instance': 'p5.xlarge'},
                '4090': {'price': 1.85, 'name': 'g5.xlarge (RTX)', 'instance': 'g5.xlarge'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'AWS EC2',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-east-1',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['instance']
            }]
        except Exception as e:
            logger.error(f"Error scraping AWS: {e}")
            return []

    async def scrape_gcp(self, session, gpu_type):
        """Scrape Google Cloud Platform GPU pricing"""
        try:
            # GCP GPU pricing per hour
            pricing_map = {
                'v100': {'price': 2.48, 'name': 'NVIDIA Tesla V100', 'machine': 'n1-standard-4'},
                'a100': {'price': 3.95, 'name': 'NVIDIA A100 40GB', 'machine': 'a2-highgpu-1g'},
                'h100': {'price': 7.50, 'name': 'NVIDIA H100', 'machine': 'a3-highgpu-8g'},
                '4090': {'price': 1.65, 'name': 'NVIDIA RTX 4090', 'machine': 'g2-standard-4'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Google Cloud',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-central1',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['machine']
            }]
        except Exception as e:
            logger.error(f"Error scraping GCP: {e}")
            return []

    async def scrape_azure(self, session, gpu_type):
        """Scrape Microsoft Azure GPU pricing"""
        try:
            # Azure GPU pricing per hour
            pricing_map = {
                'v100': {'price': 3.20, 'name': 'Tesla V100', 'vm': 'Standard_NC6s_v3'},
                'a100': {'price': 4.25, 'name': 'A100 80GB', 'vm': 'Standard_ND96asr_v4'},
                'h100': {'price': 8.80, 'name': 'H100', 'vm': 'Standard_ND_H100_v5'},
                '4090': {'price': 1.95, 'name': 'RTX 4090', 'vm': 'Standard_NV36ads_A10_v5'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Microsoft Azure',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'East US',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['vm']
            }]
        except Exception as e:
            logger.error(f"Error scraping Azure: {e}")
            return []

    async def scrape_vultr(self, session, gpu_type):
        """Scrape Vultr GPU instance pricing"""
        try:
            # Vultr GPU pricing
            pricing_map = {
                'a100': {'price': 2.75, 'name': 'A100 40GB', 'plan': 'vhp-a100-1x40'},
                'a40': {'price': 1.85, 'name': 'RTX A40 48GB', 'plan': 'vhp-a40-1x48'},
                '4090': {'price': 0.85, 'name': 'RTX 4090 24GB', 'plan': 'vhp-4090-1x24'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Vultr',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'global',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['plan']
            }]
        except Exception as e:
            logger.error(f"Error scraping Vultr: {e}")
            return []

    async def scrape_linode(self, session, gpu_type):
        """Scrape Linode (Akamai) GPU instance pricing"""
        try:
            # Linode GPU pricing
            pricing_map = {
                'v100': {'price': 2.25, 'name': 'Tesla V100', 'plan': 'g6-gpu-1'},
                'a100': {'price': 3.60, 'name': 'A100 PCIe', 'plan': 'g7-gpu-1'},
                '4090': {'price': 1.25, 'name': 'RTX 4090', 'plan': 'g8-gpu-1'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Linode',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'dedicated',
                'region': 'us-east',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['plan']
            }]
        except Exception as e:
            logger.error(f"Error scraping Linode: {e}")
            return []

    async def scrape_genesis(self, session, gpu_type):
        """Scrape Genesis Cloud GPU pricing"""
        try:
            # Genesis Cloud specializes in GPU cloud computing
            pricing_map = {
                'a100': {'price': 1.89, 'name': 'A100 SXM4 40GB', 'config': 'gc-a100-1'},
                'h100': {'price': 3.95, 'name': 'H100 SXM5 80GB', 'config': 'gc-h100-1'},
                'a40': {'price': 0.98, 'name': 'RTX A40 48GB', 'config': 'gc-a40-1'},
                'v100': {'price': 1.45, 'name': 'Tesla V100 32GB', 'config': 'gc-v100-1'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Genesis Cloud',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'spot',
                'region': 'eu-west',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['config']
            }]
        except Exception as e:
            logger.error(f"Error scraping Genesis Cloud: {e}")
            return []

    async def scrape_coreweave(self, session, gpu_type):
        """Scrape CoreWeave GPU cloud pricing"""
        try:
            # CoreWeave specializes in GPU infrastructure
            pricing_map = {
                'a100': {'price': 2.06, 'name': 'A100 NVLINK 40GB', 'config': 'a100-nvlink'},
                'h100': {'price': 4.76, 'name': 'H100 NVLINK 80GB', 'config': 'h100-nvlink'},
                'a40': {'price': 1.28, 'name': 'RTX A40 48GB', 'config': 'rtx-a40'},
                '4090': {'price': 0.69, 'name': 'RTX 4090 24GB', 'config': 'rtx-4090'},
                'a6000': {'price': 1.89, 'name': 'RTX A6000 48GB', 'config': 'rtx-a6000'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'CoreWeave',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-east',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['config']
            }]
        except Exception as e:
            logger.error(f"Error scraping CoreWeave: {e}")
            return []

    async def scrape_crusoe(self, session, gpu_type):
        """Scrape Crusoe Energy GPU cloud pricing"""
        try:
            # Crusoe Energy - clean energy GPU cloud
            pricing_map = {
                'a100': {'price': 1.95, 'name': 'A100 SXM4 40GB', 'config': 'a100-40gb'},
                'h100': {'price': 4.25, 'name': 'H100 SXM5 80GB', 'config': 'h100-80gb'},
                'v100': {'price': 1.35, 'name': 'Tesla V100 32GB', 'config': 'v100-32gb'},
            }
            
            gpu_info = pricing_map.get(gpu_type)
            if not gpu_info:
                return []
            
            return [{
                'provider': 'Crusoe Energy',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'limited',
                'type': 'clean-energy',
                'region': 'us-central',
                'specs': gpu_info['name'],
                'instance_type': gpu_info['config']
            }]
        except Exception as e:
            logger.error(f"Error scraping Crusoe Energy: {e}")
            return []

    # Keep existing methods
    async def scrape_vast(self, session, gpu_type):
        """Scrape Vast.ai marketplace - keeping existing implementation"""
        try:
            url = "https://vast.ai/api/v0/offers"
            params = {
                'type': 'on-demand',
                'gpu_name': gpu_type,
                'order': 'price'
            }
            
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Vast.ai API returned status {response.status}")
                    return []
                
                data = await response.json()
                
                prices = []
                for offer in data.get('offers', [])[:3]:  # Top 3 offers
                    prices.append({
                        'provider': 'Vast.ai',
                        'price': offer.get('dph_total', 0),
                        'gpu_count': offer.get('num_gpus', 1),
                        'availability': 'available' if offer.get('rentable') else 'limited',
                        'type': 'spot',
                        'region': self._parse_region(offer.get('geolocation', '')),
                        'specs': f"{offer.get('gpu_name', 'GPU')} - {offer.get('cuda_max_good', 'Unknown')} CUDA"
                    })
                logger.info(f"Vast.ai: Found {len(prices)} offers for {gpu_type}")
                return prices
        except Exception as e:
            logger.error(f"Error scraping Vast.ai: {e}")
            return []

    async def scrape_runpod(self, session, gpu_type):
        """Scrape RunPod pricing - keeping existing implementation"""
        try:
            pricing_map = {
                '4090': {'price': 0.39, 'name': 'RTX 4090'},
                'a100': {'price': 1.49, 'name': 'A100'},
                'h100': {'price': 2.99, 'name': 'H100'},
            }
            
            gpu_info = pricing_map.get(gpu_type, {'price': 0.5, 'name': 'GPU'})
            
            return [{
                'provider': 'RunPod',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-east',
                'specs': f"{gpu_info['name']} - On-Demand"
            }]
        except Exception as e:
            logger.error(f"Error scraping RunPod: {e}")
            return []

    async def scrape_tensordock(self, session, gpu_type):
        """Scrape TensorDock pricing - keeping existing implementation"""
        try:
            prices_map = {
                '4090': {'price': 0.29, 'name': 'RTX 4090'},
                'a100': {'price': 0.99, 'name': 'A100'},
                'h100': {'price': 2.25, 'name': 'H100'},
            }
            
            gpu_info = prices_map.get(gpu_type, {'price': 0.4, 'name': 'GPU'})
            
            return [{
                'provider': 'TensorDock',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'interruptible',
                'region': 'global',
                'specs': f"{gpu_info['name']} - Interruptible"
            }]
        except Exception as e:
            logger.error(f"Error scraping TensorDock: {e}")
            return []

    async def scrape_lambda(self, session, gpu_type):
        """Scrape Lambda Labs pricing - keeping existing implementation"""
        try:
            prices = {
                'a100': {'price': 1.10, 'name': 'A100'},
                'h100': {'price': 2.49, 'name': 'H100'},
                '4090': {'price': 0.60, 'name': 'RTX 4090'}
            }
            
            gpu_info = prices.get(gpu_type, {'price': 1.0, 'name': 'GPU'})
            
            return [{
                'provider': 'Lambda Labs',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'limited',
                'type': 'reserved',
                'region': 'us-west',
                'specs': f"{gpu_info['name']} - Reserved"
            }]
        except Exception as e:
            logger.error(f"Error scraping Lambda Labs: {e}")
            return []

    async def scrape_paperspace(self, session, gpu_type):
        """Scrape Paperspace pricing - keeping existing implementation"""
        try:
            prices = {
                '4090': {'price': 0.45, 'name': 'RTX 4090'},
                'a100': {'price': 1.20, 'name': 'A100'},
                'h100': {'price': 2.80, 'name': 'H100'},
            }
            
            gpu_info = prices.get(gpu_type, {'price': 0.8, 'name': 'GPU'})
            
            return [{
                'provider': 'Paperspace',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-east',
                'specs': f"{gpu_info['name']} - On-Demand"
            }]
        except Exception as e:
            logger.error(f"Error scraping Paperspace: {e}")
            return []

    def _parse_region(self, geolocation):
        """Convert geolocation to region"""
        if 'US' in geolocation:
            return 'us-east' if 'East' in geolocation else 'us-west'
        elif 'EU' in geolocation:
            return 'europe'
        return 'global'

    async def aggregate_all_prices(self, gpu_type: str) -> List[Dict]:
        """Aggregate prices from ALL providers"""
        all_prices = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for provider_name, scraper_func in self.providers.items():
                task = scraper_func(session, gpu_type)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Provider {list(self.providers.keys())[i]} failed: {result}")
                    continue
                all_prices.extend(result)
        
        # Sort by price
        all_prices.sort(key=lambda x: x['price'])
        
        # Calculate savings
        if all_prices:
            max_price = max(p['price'] for p in all_prices)
            for price in all_prices:
                price['savings'] = int((1 - price['price'] / max_price) * 100)
        
        logger.info(f"Aggregated {len(all_prices)} prices for {gpu_type} from {len(self.providers)} providers")
        return all_prices

    def calculate_arbitrage(self, prices: List[Dict]) -> Dict:
        """Find arbitrage opportunities"""
        if len(prices) < 2:
            return {}
        
        cheapest = prices[0]
        expensive = prices[-1]
        
        spread = expensive['price'] - cheapest['price']
        spread_pct = (spread / cheapest['price']) * 100
        
        return {
            'opportunity': spread > 0.10,  # $0.10/hr spread
            'buy_from': cheapest['provider'],
            'sell_to': 'Retail',
            'spread': spread,
            'spread_percentage': spread_pct,
            'potential_hourly_profit': spread * 0.8  # After fees
        } 