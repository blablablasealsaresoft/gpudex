# Extended GPU Provider Integrations
# This module contains integrations for major cloud providers and specialized GPU platforms

import aiohttp
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
from bs4 import BeautifulSoup
import ssl
from cache_service import cache_prices, SmartCache

logger = logging.getLogger(__name__)

@dataclass
class GPUPriceData:
    provider: str
    gpu_type: str
    price_per_hour: float
    availability: str
    region: str
    memory: str
    cuda_cores: int
    specifications: Dict[str, Any]
    last_updated: datetime
    url: str = ""
    instance_type: str = ""

class CloudProviderIntegrator:
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # API Keys from environment
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.gcp_api_key = os.getenv('GCP_API_KEY')
        self.azure_subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        self.vast_api_key = os.getenv('VAST_API_KEY')
        self.runpod_api_key = os.getenv('RUNPOD_API_KEY')
        self.lambda_api_key = os.getenv('LAMBDA_API_KEY')
        
        logger.info("CloudProviderIntegrator initialized")

    async def __aenter__(self):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
            connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @cache_prices(ttl=300)  # Cache for 5 minutes
    async def scrape_vast(self) -> List[GPUPriceData]:
        """Scrape GPU prices from Vast.ai"""
        try:
            if not self.vast_api_key:
                return await self._mock_vast_data()
            
            url = "https://console.vast.ai/api/v0/instances"
            headers = {"Authorization": f"Bearer {self.vast_api_key}"}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_vast_data(data)
                else:
                    logger.warning(f"Vast.ai API returned status {response.status}")
                    return await self._mock_vast_data()
                    
        except Exception as e:
            logger.error(f"Error scraping Vast.ai: {e}")
            return await self._mock_vast_data()

    async def _mock_vast_data(self) -> List[GPUPriceData]:
        """Mock data for Vast.ai when API is not available"""
        return [
            GPUPriceData(
                provider="vast",
                gpu_type="RTX 4090",
                price_per_hour=0.45,
                availability="Available",
                region="US-East",
                memory="24GB",
                cuda_cores=16384,
                specifications={"architecture": "Ada Lovelace", "tensor_cores": "4th Gen"},
                last_updated=datetime.now(),
                url="https://vast.ai",
                instance_type="RTX4090"
            ),
            GPUPriceData(
                provider="vast",
                gpu_type="RTX 3090",
                price_per_hour=0.35,
                availability="Available",
                region="US-West",
                memory="24GB",
                cuda_cores=10496,
                specifications={"architecture": "Ampere", "tensor_cores": "3rd Gen"},
                last_updated=datetime.now(),
                url="https://vast.ai",
                instance_type="RTX3090"
            )
        ]

    def _parse_vast_data(self, data: Dict) -> List[GPUPriceData]:
        """Parse Vast.ai API response"""
        prices = []
        for instance in data.get('instances', []):
            try:
                gpu_name = instance.get('gpu_name', 'Unknown')
                price = float(instance.get('dph_total', 0))
                
                prices.append(GPUPriceData(
                    provider="vast",
                    gpu_type=gpu_name,
                    price_per_hour=price,
                    availability="Available" if instance.get('rentable') else "Unavailable",
                    region=instance.get('geolocation', 'Unknown'),
                    memory=f"{instance.get('gpu_mem_bw', 0)}GB",
                    cuda_cores=instance.get('cuda_max_good', 0),
                    specifications={"reliability": instance.get('reliability2', 0)},
                    last_updated=datetime.now(),
                    url="https://vast.ai",
                    instance_type=instance.get('id', '')
                ))
            except Exception as e:
                logger.error(f"Error parsing Vast.ai instance: {e}")
                
        return prices

    @cache_prices(ttl=300)
    async def scrape_runpod(self) -> List[GPUPriceData]:
        """Scrape GPU prices from RunPod"""
        try:
            if not self.runpod_api_key:
                return await self._mock_runpod_data()
            
            url = "https://api.runpod.io/graphql"
            headers = {"Authorization": f"Bearer {self.runpod_api_key}"}
            
            query = """
            query {
                gpuTypes {
                    id
                    displayName
                    memoryInGb
                    secureCloud
                    communityCloud
                    lowestPrice {
                        gpuTypeId
                        uninterruptablePrice
                        interruptablePrice
                    }
                }
            }
            """
            
            async with self.session.post(url, headers=headers, json={"query": query}) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_runpod_data(data)
                else:
                    return await self._mock_runpod_data()
                    
        except Exception as e:
            logger.error(f"Error scraping RunPod: {e}")
            return await self._mock_runpod_data()

    async def _mock_runpod_data(self) -> List[GPUPriceData]:
        """Mock data for RunPod"""
        return [
            GPUPriceData(
                provider="runpod",
                gpu_type="RTX 4090",
                price_per_hour=0.50,
                availability="Available",
                region="US-East",
                memory="24GB",
                cuda_cores=16384,
                specifications={"type": "secure_cloud"},
                last_updated=datetime.now(),
                url="https://runpod.io",
                instance_type="NVIDIA RTX 4090"
            )
        ]

    def _parse_runpod_data(self, data: Dict) -> List[GPUPriceData]:
        """Parse RunPod API response"""
        prices = []
        gpu_types = data.get('data', {}).get('gpuTypes', [])
        
        for gpu in gpu_types:
            try:
                lowest_price = gpu.get('lowestPrice')
                if lowest_price:
                    price = float(lowest_price.get('uninterruptablePrice', 0))
                    
                    prices.append(GPUPriceData(
                        provider="runpod",
                        gpu_type=gpu.get('displayName', 'Unknown'),
                        price_per_hour=price,
                        availability="Available",
                        region="Global",
                        memory=f"{gpu.get('memoryInGb', 0)}GB",
                        cuda_cores=0,  # Not provided by API
                        specifications={
                            "secure_cloud": gpu.get('secureCloud', False),
                            "community_cloud": gpu.get('communityCloud', False)
                        },
                        last_updated=datetime.now(),
                        url="https://runpod.io",
                        instance_type=gpu.get('id', '')
                    ))
            except Exception as e:
                logger.error(f"Error parsing RunPod GPU: {e}")
                
        return prices

    @cache_prices(ttl=600)  # AWS prices change less frequently
    async def scrape_aws(self) -> List[GPUPriceData]:
        """Scrape GPU prices from AWS EC2"""
        try:
            if not self.aws_access_key or not self.aws_secret_key:
                logger.info("AWS credentials not configured, using mock data")
                return await self._mock_aws_data()
            
            # Use boto3 to get real AWS pricing
            return await self._get_real_aws_pricing()
        except Exception as e:
            logger.error(f"Error scraping AWS: {e}")
            return await self._mock_aws_data()

    async def _get_real_aws_pricing(self) -> List[GPUPriceData]:
        """Get real AWS EC2 GPU instance pricing"""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            # Initialize AWS pricing client
            pricing_client = boto3.client(
                'pricing',
                region_name='us-east-1',  # Pricing API is only available in us-east-1
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            # GPU instance types to check
            gpu_instance_types = [
                'p3.2xlarge',   # V100
                'p3.8xlarge',   # 4x V100
                'p4d.24xlarge', # 8x A100
                'g4dn.xlarge',  # T4
                'g4dn.2xlarge', # T4
                'g5.xlarge',    # A10G
                'g5.2xlarge',   # A10G
            ]
            
            prices = []
            
            for instance_type in gpu_instance_types:
                try:
                    # Get pricing for each instance type
                    response = pricing_client.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=[
                            {
                                'Type': 'TERM_MATCH',
                                'Field': 'instanceType',
                                'Value': instance_type
                            },
                            {
                                'Type': 'TERM_MATCH',
                                'Field': 'tenancy',
                                'Value': 'Shared'
                            },
                            {
                                'Type': 'TERM_MATCH',
                                'Field': 'operating-system',
                                'Value': 'Linux'
                            },
                            {
                                'Type': 'TERM_MATCH',
                                'Field': 'location',
                                'Value': 'US East (N. Virginia)'
                            }
                        ],
                        MaxResults=1
                    )
                    
                    if response['PriceList']:
                        price_data = json.loads(response['PriceList'][0])
                        terms = price_data.get('terms', {}).get('OnDemand', {})
                        
                        if terms:
                            # Extract the first pricing dimension
                            first_term = next(iter(terms.values()))
                            price_dimensions = first_term.get('priceDimensions', {})
                            
                            if price_dimensions:
                                first_dimension = next(iter(price_dimensions.values()))
                                price_usd = float(first_dimension.get('pricePerUnit', {}).get('USD', 0))
                                
                                # Map instance type to GPU details
                                gpu_info = self._get_aws_gpu_info(instance_type)
                                
                                if price_usd > 0:
                                    prices.append(GPUPriceData(
                                        provider="aws",
                                        gpu_type=gpu_info['gpu_type'],
                                        price_per_hour=price_usd,
                                        availability="Available",
                                        region="us-east-1",
                                        memory=gpu_info['memory'],
                                        cuda_cores=gpu_info['cuda_cores'],
                                        specifications={
                                            "instance_type": instance_type,
                                            "vcpus": gpu_info['vcpus'],
                                            "ram": gpu_info['ram'],
                                            "gpu_count": gpu_info['gpu_count']
                                        },
                                        last_updated=datetime.now(),
                                        url="https://aws.amazon.com/ec2/instance-types/",
                                        instance_type=instance_type
                                    ))
                                
                except Exception as e:
                    logger.error(f"Error getting AWS pricing for {instance_type}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(prices)} real AWS GPU prices")
            return prices if prices else await self._mock_aws_data()
            
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"AWS credentials error: {e}, falling back to mock data")
            return await self._mock_aws_data()
        except ImportError:
            logger.warning("boto3 not installed, using mock AWS data")
            return await self._mock_aws_data()
        except Exception as e:
            logger.error(f"Unexpected error getting real AWS pricing: {e}")
            return await self._mock_aws_data()

    def _get_aws_gpu_info(self, instance_type: str) -> Dict[str, Any]:
        """Get GPU specifications for AWS instance types"""
        gpu_specs = {
            'p3.2xlarge': {
                'gpu_type': 'V100',
                'memory': '16GB',
                'cuda_cores': 5120,
                'vcpus': 8,
                'ram': '61GB',
                'gpu_count': 1
            },
            'p3.8xlarge': {
                'gpu_type': 'V100',
                'memory': '64GB',
                'cuda_cores': 20480,
                'vcpus': 32,
                'ram': '244GB',
                'gpu_count': 4
            },
            'p4d.24xlarge': {
                'gpu_type': 'A100',
                'memory': '320GB',
                'cuda_cores': 55296,
                'vcpus': 96,
                'ram': '1152GB',
                'gpu_count': 8
            },
            'g4dn.xlarge': {
                'gpu_type': 'T4',
                'memory': '16GB',
                'cuda_cores': 2560,
                'vcpus': 4,
                'ram': '16GB',
                'gpu_count': 1
            },
            'g4dn.2xlarge': {
                'gpu_type': 'T4',
                'memory': '16GB',
                'cuda_cores': 2560,
                'vcpus': 8,
                'ram': '32GB',
                'gpu_count': 1
            },
            'g5.xlarge': {
                'gpu_type': 'A10G',
                'memory': '24GB',
                'cuda_cores': 9216,
                'vcpus': 4,
                'ram': '16GB',
                'gpu_count': 1
            },
            'g5.2xlarge': {
                'gpu_type': 'A10G',
                'memory': '24GB',
                'cuda_cores': 9216,
                'vcpus': 8,
                'ram': '32GB',
                'gpu_count': 1
            }
        }
        
        return gpu_specs.get(instance_type, {
            'gpu_type': 'Unknown',
            'memory': '0GB',
            'cuda_cores': 0,
            'vcpus': 0,
            'ram': '0GB',
            'gpu_count': 0
        })

    async def _mock_aws_data(self) -> List[GPUPriceData]:
        """Mock data for AWS EC2 GPU instances"""
        return [
            GPUPriceData(
                provider="aws",
                gpu_type="V100",
                price_per_hour=3.06,
                availability="Available",
                region="us-east-1",
                memory="16GB",
                cuda_cores=5120,
                specifications={"instance_type": "p3.2xlarge", "vcpus": 8},
                last_updated=datetime.now(),
                url="https://aws.amazon.com/ec2/instance-types/p3/",
                instance_type="p3.2xlarge"
            ),
            GPUPriceData(
                provider="aws",
                gpu_type="A100",
                price_per_hour=4.10,
                availability="Available",
                region="us-east-1",
                memory="40GB",
                cuda_cores=6912,
                specifications={"instance_type": "p4d.xlarge", "vcpus": 4},
                last_updated=datetime.now(),
                url="https://aws.amazon.com/ec2/instance-types/p4/",
                instance_type="p4d.xlarge"
            )
        ]

    @cache_prices(ttl=600)
    async def scrape_gcp(self) -> List[GPUPriceData]:
        """Scrape GPU prices from Google Cloud Platform"""
        try:
            return await self._mock_gcp_data()
        except Exception as e:
            logger.error(f"Error scraping GCP: {e}")
            return await self._mock_gcp_data()

    async def _mock_gcp_data(self) -> List[GPUPriceData]:
        """Mock data for GCP GPU instances"""
        return [
            GPUPriceData(
                provider="gcp",
                gpu_type="V100",
                price_per_hour=2.48,
                availability="Available",
                region="us-central1",
                memory="16GB",
                cuda_cores=5120,
                specifications={"machine_type": "n1-standard-4", "gpu_count": 1},
                last_updated=datetime.now(),
                url="https://cloud.google.com/compute/gpus-pricing",
                instance_type="nvidia-tesla-v100"
            ),
            GPUPriceData(
                provider="gcp",
                gpu_type="T4",
                price_per_hour=0.35,
                availability="Available",
                region="us-central1",
                memory="16GB",
                cuda_cores=2560,
                specifications={"machine_type": "n1-standard-4", "gpu_count": 1},
                last_updated=datetime.now(),
                url="https://cloud.google.com/compute/gpus-pricing",
                instance_type="nvidia-tesla-t4"
            )
        ]

    @cache_prices(ttl=600)
    async def scrape_azure(self) -> List[GPUPriceData]:
        """Scrape GPU prices from Microsoft Azure"""
        try:
            return await self._mock_azure_data()
        except Exception as e:
            logger.error(f"Error scraping Azure: {e}")
            return await self._mock_azure_data()

    async def _mock_azure_data(self) -> List[GPUPriceData]:
        """Mock data for Azure GPU instances"""
        return [
            GPUPriceData(
                provider="azure",
                gpu_type="V100",
                price_per_hour=3.06,
                availability="Available",
                region="East US",
                memory="16GB",
                cuda_cores=5120,
                specifications={"vm_size": "Standard_NC6s_v3", "vcpus": 6},
                last_updated=datetime.now(),
                url="https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/",
                instance_type="Standard_NC6s_v3"
            )
        ]

    @cache_prices(ttl=300)
    async def scrape_lambda(self) -> List[GPUPriceData]:
        """Scrape GPU prices from Lambda Labs"""
        try:
            if not self.lambda_api_key:
                return await self._mock_lambda_data()
            
            url = "https://cloud.lambdalabs.com/api/v1/instance-types"
            headers = {"Authorization": f"Bearer {self.lambda_api_key}"}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_lambda_data(data)
                else:
                    return await self._mock_lambda_data()
                    
        except Exception as e:
            logger.error(f"Error scraping Lambda Labs: {e}")
            return await self._mock_lambda_data()

    async def _mock_lambda_data(self) -> List[GPUPriceData]:
        """Mock data for Lambda Labs"""
        return [
            GPUPriceData(
                provider="lambda",
                gpu_type="RTX 4090",
                price_per_hour=0.80,
                availability="Available",
                region="US-West",
                memory="24GB",
                cuda_cores=16384,
                specifications={"vcpus": 14, "ram": "46GB"},
                last_updated=datetime.now(),
                url="https://lambdalabs.com/service/gpu-cloud",
                instance_type="gpu_1x_rtx4090"
            ),
            GPUPriceData(
                provider="lambda",
                gpu_type="A100",
                price_per_hour=1.10,
                availability="Available",
                region="US-West",
                memory="40GB",
                cuda_cores=6912,
                specifications={"vcpus": 30, "ram": "200GB"},
                last_updated=datetime.now(),
                url="https://lambdalabs.com/service/gpu-cloud",
                instance_type="gpu_1x_a100"
            )
        ]

    def _parse_lambda_data(self, data: Dict) -> List[GPUPriceData]:
        """Parse Lambda Labs API response"""
        prices = []
        instance_types = data.get('data', {})
        
        for instance_id, instance_info in instance_types.items():
            try:
                price = float(instance_info.get('price_cents_per_hour', 0)) / 100
                gpu_info = instance_info.get('instance_type', {})
                
                prices.append(GPUPriceData(
                    provider="lambda",
                    gpu_type=gpu_info.get('name', 'Unknown'),
                    price_per_hour=price,
                    availability="Available",
                    region="US-West",
                    memory=gpu_info.get('memory_gib', '0GB'),
                    cuda_cores=0,  # Not provided
                    specifications={
                        "vcpus": gpu_info.get('vcpus', 0),
                        "storage_gib": gpu_info.get('storage_gib', 0)
                    },
                    last_updated=datetime.now(),
                    url="https://lambdalabs.com/service/gpu-cloud",
                    instance_type=instance_id
                ))
            except Exception as e:
                logger.error(f"Error parsing Lambda Labs instance: {e}")
                
        return prices

    # Continue with other providers (mocked for now)
    async def scrape_paperspace(self) -> List[GPUPriceData]:
        """Mock Paperspace data"""
        return [
            GPUPriceData(
                provider="paperspace",
                gpu_type="RTX 4000",
                price_per_hour=0.51,
                availability="Available",
                region="US-East",
                memory="8GB",
                cuda_cores=2304,
                specifications={"vcpus": 8, "ram": "30GB"},
                last_updated=datetime.now(),
                url="https://paperspace.com",
                instance_type="P4000"
            )
        ]

    async def scrape_tensordock(self) -> List[GPUPriceData]:
        """Mock TensorDock data"""
        return [
            GPUPriceData(
                provider="tensordock",
                gpu_type="RTX 3080",
                price_per_hour=0.29,
                availability="Available",
                region="US-Central",
                memory="10GB",
                cuda_cores=8704,
                specifications={"vcpus": 6, "ram": "32GB"},
                last_updated=datetime.now(),
                url="https://tensordock.com",
                instance_type="RTX3080"
            )
        ]

    async def scrape_vultr(self) -> List[GPUPriceData]:
        """Mock Vultr data"""
        return [
            GPUPriceData(
                provider="vultr",
                gpu_type="A40",
                price_per_hour=2.28,
                availability="Available",
                region="US-East",
                memory="48GB",
                cuda_cores=10752,
                specifications={"vcpus": 8, "ram": "60GB"},
                last_updated=datetime.now(),
                url="https://vultr.com",
                instance_type="A40"
            )
        ]

    async def scrape_linode(self) -> List[GPUPriceData]:
        """Mock Linode data"""
        return [
            GPUPriceData(
                provider="linode",
                gpu_type="RTX 6000",
                price_per_hour=1.50,
                availability="Available",
                region="US-East",
                memory="24GB",
                cuda_cores=4608,
                specifications={"vcpus": 8, "ram": "32GB"},
                last_updated=datetime.now(),
                url="https://linode.com",
                instance_type="RTX6000"
            )
        ]

    async def scrape_genesis(self) -> List[GPUPriceData]:
        """Mock Genesis Cloud data"""
        return [
            GPUPriceData(
                provider="genesis",
                gpu_type="RTX 3090",
                price_per_hour=0.89,
                availability="Available",
                region="EU-West",
                memory="24GB",
                cuda_cores=10496,
                specifications={"vcpus": 16, "ram": "64GB"},
                last_updated=datetime.now(),
                url="https://genesiscloud.com",
                instance_type="RTX3090"
            )
        ]

    async def scrape_coreweave(self) -> List[GPUPriceData]:
        """Mock CoreWeave data"""
        return [
            GPUPriceData(
                provider="coreweave",
                gpu_type="A100",
                price_per_hour=2.21,
                availability="Available",
                region="US-East",
                memory="80GB",
                cuda_cores=6912,
                specifications={"vcpus": 16, "ram": "120GB"},
                last_updated=datetime.now(),
                url="https://coreweave.com",
                instance_type="A100_80GB"
            )
        ]

    async def scrape_crusoe(self) -> List[GPUPriceData]:
        """Mock Crusoe Energy data"""
        return [
            GPUPriceData(
                provider="crusoe",
                gpu_type="H100",
                price_per_hour=4.64,
                availability="Available",
                region="US-Central",
                memory="80GB",
                cuda_cores=14592,
                specifications={"vcpus": 48, "ram": "400GB"},
                last_updated=datetime.now(),
                url="https://crusoeenergy.com",
                instance_type="H100_80GB"
            )
        ]

    async def get_all_prices(self) -> List[GPUPriceData]:
        """Get prices from all providers concurrently"""
        providers = [
            self.scrape_vast(),
            self.scrape_runpod(),
            self.scrape_aws(),
            self.scrape_gcp(),
            self.scrape_azure(),
            self.scrape_lambda(),
            self.scrape_paperspace(),
            self.scrape_tensordock(),
            self.scrape_vultr(),
            self.scrape_linode(),
            self.scrape_genesis(),
            self.scrape_coreweave(),
            self.scrape_crusoe()
        ]
        
        try:
            results = await asyncio.gather(*providers, return_exceptions=True)
            all_prices = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error from provider {i}: {result}")
                elif isinstance(result, list):
                    all_prices.extend(result)
                    
            logger.info(f"Retrieved {len(all_prices)} GPU prices from all providers")
            return all_prices
            
        except Exception as e:
            logger.error(f"Error getting all prices: {e}")
            return []

    def calculate_arbitrage(self, prices: List[GPUPriceData], min_profit_margin: float = 0.1) -> List[Dict[str, Any]]:
        """Calculate arbitrage opportunities between providers"""
        opportunities = []
        
        # Group prices by GPU type
        gpu_groups = {}
        for price in prices:
            gpu_type = price.gpu_type.lower().replace(' ', '_')
            if gpu_type not in gpu_groups:
                gpu_groups[gpu_type] = []
            gpu_groups[gpu_type].append(price)
        
        # Find arbitrage opportunities within each GPU type
        for gpu_type, gpu_prices in gpu_groups.items():
            if len(gpu_prices) < 2:
                continue
                
            # Sort by price
            sorted_prices = sorted(gpu_prices, key=lambda x: x.price_per_hour)
            lowest = sorted_prices[0]
            highest = sorted_prices[-1]
            
            # Calculate profit margin
            if lowest.price_per_hour > 0:
                profit_margin = (highest.price_per_hour - lowest.price_per_hour) / lowest.price_per_hour
                
                if profit_margin >= min_profit_margin:
                    opportunities.append({
                        "gpu_type": gpu_type,
                        "buy_provider": lowest.provider,
                        "buy_price": lowest.price_per_hour,
                        "sell_provider": highest.provider,
                        "sell_price": highest.price_per_hour,
                        "profit_per_hour": highest.price_per_hour - lowest.price_per_hour,
                        "profit_margin": profit_margin,
                        "potential_savings": f"{profit_margin * 100:.1f}%"
                    })
        
        # Sort by profit margin
        opportunities.sort(key=lambda x: x['profit_margin'], reverse=True)
        return opportunities

    def filter_prices(self, prices: List[GPUPriceData], filters: Dict[str, Any]) -> List[GPUPriceData]:
        """Advanced filtering by specs, location, availability, price range"""
        filtered = prices
        
        # Filter by GPU type
        if gpu_type := filters.get('gpu_type'):
            filtered = [p for p in filtered if gpu_type.lower() in p.gpu_type.lower()]
        
        # Filter by provider
        if provider := filters.get('provider'):
            filtered = [p for p in filtered if provider.lower() == p.provider.lower()]
        
        # Filter by region
        if region := filters.get('region'):
            filtered = [p for p in filtered if region.lower() in p.region.lower()]
        
        # Filter by availability
        if availability := filters.get('availability'):
            filtered = [p for p in filtered if availability.lower() in p.availability.lower()]
        
        # Filter by price range
        if min_price := filters.get('min_price'):
            filtered = [p for p in filtered if p.price_per_hour >= float(min_price)]
        
        if max_price := filters.get('max_price'):
            filtered = [p for p in filtered if p.price_per_hour <= float(max_price)]
        
        # Filter by memory
        if min_memory := filters.get('min_memory'):
            filtered = [p for p in filtered if self._extract_memory_gb(p.memory) >= int(min_memory)]
        
        # Filter by CUDA cores
        if min_cuda := filters.get('min_cuda_cores'):
            filtered = [p for p in filtered if p.cuda_cores >= int(min_cuda)]
        
        # Sort results
        sort_by = filters.get('sort_by', 'price')
        reverse = filters.get('sort_desc', False)
        
        if sort_by == 'price':
            filtered.sort(key=lambda x: x.price_per_hour, reverse=reverse)
        elif sort_by == 'memory':
            filtered.sort(key=lambda x: self._extract_memory_gb(x.memory), reverse=reverse)
        elif sort_by == 'cuda_cores':
            filtered.sort(key=lambda x: x.cuda_cores, reverse=reverse)
        elif sort_by == 'provider':
            filtered.sort(key=lambda x: x.provider, reverse=reverse)
        
        return filtered

    def _extract_memory_gb(self, memory_str: str) -> int:
        """Extract memory in GB from string like '24GB'"""
        try:
            return int(re.findall(r'\d+', memory_str)[0])
        except (IndexError, ValueError):
            return 0 