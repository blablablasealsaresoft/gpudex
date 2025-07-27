"""
GPUDex Real GPU Provisioning Service
Handles actual GPU instance creation, management, and SSH key generation
"""

import asyncio
import logging
import os
import json
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import asyncssh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SSHKeyPair:
    """SSH key pair for instance access"""
    private_key: str
    public_key: str
    fingerprint: str

@dataclass
class GPUInstance:
    """GPU instance details"""
    instance_id: str
    provider: str
    gpu_type: str
    status: str
    ssh_host: str
    ssh_port: int
    ssh_username: str
    ssh_private_key: str
    jupyter_url: Optional[str] = None
    vscode_url: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    cost_per_hour: Optional[float] = None

class GPUProvisioningService:
    """Real GPU provisioning service"""
    
    def __init__(self):
        self.vast_api_key = os.getenv("VAST_API_KEY")
        self.runpod_api_key = os.getenv("RUNPOD_API_KEY")
        self.lambda_api_key = os.getenv("LAMBDA_API_KEY")
        self.paperspace_api_key = os.getenv("PAPERSPACE_API_KEY")
        
        # SSH keys storage
        self.ssh_keys_path = Path("ssh_keys")
        self.ssh_keys_path.mkdir(exist_ok=True)
        
        # Instance tracking
        self.active_instances: Dict[str, GPUInstance] = {}
        
    def generate_ssh_keypair(self, key_name: str) -> SSHKeyPair:
        """Generate SSH key pair for instance access"""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Get private key in PEM format
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Get public key in OpenSSH format
            public_key = private_key.public_key()
            public_ssh = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            ).decode('utf-8')
            
            # Generate fingerprint
            fingerprint = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            ).hex()[:16]
            
            # Save keys to files
            private_key_path = self.ssh_keys_path / f"{key_name}_private.pem"
            public_key_path = self.ssh_keys_path / f"{key_name}_public.pub"
            
            with open(private_key_path, 'w') as f:
                f.write(private_pem)
            os.chmod(private_key_path, 0o600)
            
            with open(public_key_path, 'w') as f:
                f.write(public_ssh)
            
            logger.info(f"Generated SSH key pair: {key_name}")
            
            return SSHKeyPair(
                private_key=private_pem,
                public_key=public_ssh,
                fingerprint=fingerprint
            )
            
        except Exception as e:
            logger.error(f"Error generating SSH key pair: {e}")
            raise

    async def create_vast_instance(self, gpu_type: str, hours: int, rental_id: str) -> GPUInstance:
        """Create GPU instance on Vast.ai"""
        try:
            if not self.vast_api_key:
                raise ValueError("VAST_API_KEY not configured")
            
            # Generate SSH key for this instance
            ssh_keys = self.generate_ssh_keypair(f"vast_{rental_id}")
            
            # Get available offers for this GPU type
            async with aiohttp.ClientSession() as session:
                # Search for instances
                search_url = f"https://console.vast.ai/api/v0/bundles/?q={{\"verified\":{{\"eq\":true}},\"external\":{{\"eq\":false}},\"rentable\":{{\"eq\":true}}}}"
                headers = {"Authorization": f"Bearer {self.vast_api_key}"}
                
                async with session.get(search_url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to search Vast.ai instances: {response.status}")
                    
                    offers = await response.json()
                    
                    # Find matching offer
                    suitable_offer = None
                    for offer in offers.get("offers", []):
                        if gpu_type.lower() in offer.get("gpu_name", "").lower():
                            suitable_offer = offer
                            break
                    
                    if not suitable_offer:
                        raise Exception(f"No suitable {gpu_type} found on Vast.ai")
                    
                    # Create instance
                    create_data = {
                        "client_id": "vastai",
                        "image": "pytorch/pytorch:latest",
                        "ssh_key": ssh_keys.public_key,
                        "onstart": "service ssh start",
                        "disk": 20,  # 20GB disk
                        "label": f"gpudex-{rental_id}",
                        "duration": hours,
                    }
                    
                    create_url = f"https://console.vast.ai/api/v0/asks/{suitable_offer['id']}/?api_key={self.vast_api_key}"
                    
                    async with session.put(create_url, json=create_data) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to create Vast.ai instance: {response.status}")
                        
                        result = await response.json()
                        instance_id = str(result.get("new_contract"))
                        
                        # Wait for instance to be ready
                        await self._wait_for_vast_instance(session, instance_id, headers)
                        
                        # Get instance details
                        details_url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={self.vast_api_key}"
                        async with session.get(details_url, headers=headers) as response:
                            instance_data = await response.json()
                            
                            ssh_host = instance_data.get("ssh_host")
                            ssh_port = instance_data.get("ssh_port", 22)
                            
                            instance = GPUInstance(
                                instance_id=instance_id,
                                provider="vast",
                                gpu_type=gpu_type,
                                status="running",
                                ssh_host=ssh_host,
                                ssh_port=ssh_port,
                                ssh_username="root",
                                ssh_private_key=ssh_keys.private_key,
                                jupyter_url=f"http://{ssh_host}:8888",
                                vscode_url=f"http://{ssh_host}:8080",
                                created_at=datetime.now(),
                                expires_at=datetime.now() + timedelta(hours=hours),
                                cost_per_hour=suitable_offer.get("dph_total", 0)
                            )
                            
                            # Setup instance with Jupyter and VS Code
                            await self._setup_instance_services(instance)
                            
                            self.active_instances[rental_id] = instance
                            logger.info(f"Created Vast.ai instance: {instance_id} for rental {rental_id}")
                            
                            return instance
                            
        except Exception as e:
            logger.error(f"Error creating Vast.ai instance: {e}")
            raise

    async def create_lambda_instance(self, gpu_type: str, hours: int, rental_id: str) -> GPUInstance:
        """Create GPU instance on Lambda Labs"""
        try:
            if not self.lambda_api_key:
                raise ValueError("LAMBDA_API_KEY not configured")
            
            # Generate SSH key for this instance
            ssh_keys = self.generate_ssh_keypair(f"lambda_{rental_id}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.lambda_api_key}",
                    "Content-Type": "application/json"
                }
                
                # Get instance types
                types_url = "https://cloud.lambdalabs.com/api/v1/instance-types"
                async with session.get(types_url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get Lambda instance types: {response.status}")
                    
                    types_data = await response.json()
                    
                    # Find matching instance type
                    instance_type = None
                    for type_id, type_data in types_data.get("data", {}).items():
                        if gpu_type.lower() in type_data.get("instance_type", {}).get("description", "").lower():
                            instance_type = type_id
                            break
                    
                    if not instance_type:
                        raise Exception(f"No suitable {gpu_type} found on Lambda Labs")
                    
                    # Create instance
                    create_data = {
                        "region_name": "us-east-1",
                        "instance_type_name": instance_type,
                        "ssh_key_names": [],  # Lambda handles SSH keys differently
                        "file_system_names": [],
                        "quantity": 1,
                        "name": f"gpudex-{rental_id}"
                    }
                    
                    create_url = "https://cloud.lambdalabs.com/api/v1/instance-operations/launch"
                    
                    async with session.post(create_url, json=create_data, headers=headers) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to create Lambda instance: {response.status}")
                        
                        result = await response.json()
                        instance_id = result.get("data", {}).get("instance_ids", [])[0]
                        
                        # Wait for instance to be ready
                        await self._wait_for_lambda_instance(session, instance_id, headers)
                        
                        # Get instance details
                        details_url = f"https://cloud.lambdalabs.com/api/v1/instances/{instance_id}"
                        async with session.get(details_url, headers=headers) as response:
                            instance_data = await response.json()
                            data = instance_data.get("data", {})
                            
                            ssh_host = data.get("ip")
                            
                            instance = GPUInstance(
                                instance_id=instance_id,
                                provider="lambda",
                                gpu_type=gpu_type,
                                status="running",
                                ssh_host=ssh_host,
                                ssh_port=22,
                                ssh_username="ubuntu",
                                ssh_private_key=ssh_keys.private_key,
                                jupyter_url=f"http://{ssh_host}:8888",
                                vscode_url=f"http://{ssh_host}:8080",
                                created_at=datetime.now(),
                                expires_at=datetime.now() + timedelta(hours=hours),
                                cost_per_hour=data.get("instance_type", {}).get("price_cents_per_hour", 0) / 100
                            )
                            
                            # Setup instance with Jupyter and VS Code
                            await self._setup_instance_services(instance)
                            
                            self.active_instances[rental_id] = instance
                            logger.info(f"Created Lambda instance: {instance_id} for rental {rental_id}")
                            
                            return instance
                            
        except Exception as e:
            logger.error(f"Error creating Lambda instance: {e}")
            raise

    async def create_runpod_instance(self, gpu_type: str, hours: int, rental_id: str) -> GPUInstance:
        """Create GPU instance on RunPod"""
        try:
            if not self.runpod_api_key:
                raise ValueError("RUNPOD_API_KEY not configured")
            
            # Generate SSH key for this instance
            ssh_keys = self.generate_ssh_keypair(f"runpod_{rental_id}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.runpod_api_key}",
                    "Content-Type": "application/json"
                }
                
                # RunPod GraphQL API for creating pods
                graphql_url = "https://api.runpod.io/graphql"
                
                # Query available GPU types
                gpu_query = {
                    "query": """
                    query {
                        gpuTypes {
                            id
                            displayName
                            memoryInGb
                            secureCloud
                            communityCloud
                            lowestPrice {
                                minimumBidPrice
                                uninterruptablePrice
                            }
                        }
                    }
                    """
                }
                
                async with session.post(graphql_url, json=gpu_query, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get RunPod GPU types: {response.status}")
                    
                    result = await response.json()
                    gpu_types = result.get("data", {}).get("gpuTypes", [])
                    
                    # Find matching GPU type
                    gpu_type_id = None
                    for gpu in gpu_types:
                        if gpu_type.lower() in gpu.get("displayName", "").lower():
                            gpu_type_id = gpu.get("id")
                            break
                    
                    if not gpu_type_id:
                        raise Exception(f"No suitable {gpu_type} found on RunPod")
                    
                    # Create pod
                    create_mutation = {
                        "query": f"""
                        mutation {{
                            podFindAndDeployOnDemand(
                                input: {{
                                    cloudType: SECURE
                                    gpuCount: 1
                                    volumeInGb: 20
                                    containerDiskInGb: 20
                                    minVcpuCount: 4
                                    minMemoryInGb: 8
                                    gpuTypeId: "{gpu_type_id}"
                                    name: "gpudex-{rental_id}"
                                    imageName: "runpod/pytorch:1.13.1-py3.9-cuda11.7.1-devel-ubuntu20.04"
                                    dockerArgs: ""
                                    ports: "8888/http,8080/http,22/tcp"
                                    volumeMountPath: "/workspace"
                                    env: [
                                        {{key: "JUPYTER_PASSWORD", value: "gpudex123"}}
                                    ]
                                }}
                            ) {{
                                id
                                imageName
                                env
                                machineId
                                machine {{
                                    podHostId
                                }}
                            }}
                        }}
                        """
                    }
                    
                    async with session.post(graphql_url, json=create_mutation, headers=headers) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to create RunPod instance: {response.status}")
                        
                        result = await response.json()
                        pod_data = result.get("data", {}).get("podFindAndDeployOnDemand")
                        
                        if not pod_data:
                            raise Exception("Failed to create RunPod pod")
                        
                        instance_id = pod_data.get("id")
                        
                        # Wait for pod to be ready
                        await self._wait_for_runpod_instance(session, instance_id, headers)
                        
                        # Get pod details including IP
                        pod_query = {
                            "query": f"""
                            query {{
                                pod(input: {{podId: "{instance_id}"}}) {{
                                    id
                                    name
                                    runtime {{
                                        uptimeInSeconds
                                        ports {{
                                            ip
                                            isIpPublic
                                            privatePort
                                            publicPort
                                            type
                                        }}
                                        gpus {{
                                            id
                                            gpuUtilPercent
                                            memoryUtilPercent
                                        }}
                                    }}
                                }}
                            }}
                            """
                        }
                        
                        async with session.post(graphql_url, json=pod_query, headers=headers) as response:
                            pod_details = await response.json()
                            pod_info = pod_details.get("data", {}).get("pod", {})
                            runtime = pod_info.get("runtime", {})
                            ports = runtime.get("ports", [])
                            
                            # Find SSH port
                            ssh_host = None
                            ssh_port = 22
                            jupyter_port = 8888
                            vscode_port = 8080
                            
                            for port in ports:
                                if port.get("privatePort") == 22:
                                    ssh_host = port.get("ip")
                                    ssh_port = port.get("publicPort", 22)
                                elif port.get("privatePort") == 8888:
                                    jupyter_port = port.get("publicPort", 8888)
                                elif port.get("privatePort") == 8080:
                                    vscode_port = port.get("publicPort", 8080)
                            
                            instance = GPUInstance(
                                instance_id=instance_id,
                                provider="runpod",
                                gpu_type=gpu_type,
                                status="running",
                                ssh_host=ssh_host,
                                ssh_port=ssh_port,
                                ssh_username="root",
                                ssh_private_key=ssh_keys.private_key,
                                jupyter_url=f"http://{ssh_host}:{jupyter_port}",
                                vscode_url=f"http://{ssh_host}:{vscode_port}",
                                created_at=datetime.now(),
                                expires_at=datetime.now() + timedelta(hours=hours),
                                cost_per_hour=0.5  # Placeholder - get from actual pricing
                            )
                            
                            self.active_instances[rental_id] = instance
                            logger.info(f"Created RunPod instance: {instance_id} for rental {rental_id}")
                            
                            return instance
                            
        except Exception as e:
            logger.error(f"Error creating RunPod instance: {e}")
            raise

    async def _setup_instance_services(self, instance: GPUInstance) -> None:
        """Setup Jupyter and VS Code on the instance"""
        try:
            # Wait a bit for SSH to be ready
            await asyncio.sleep(30)
            
            # Connect via SSH and setup services
            setup_commands = [
                "apt-get update -y",
                "apt-get install -y python3-pip nodejs npm",
                "pip3 install jupyter jupyterlab",
                "npm install -g code-server",
                
                # Start Jupyter
                "nohup jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --token=gpudex123 > /var/log/jupyter.log 2>&1 &",
                
                # Start VS Code Server
                "nohup code-server --bind-addr 0.0.0.0:8080 --auth password --password gpudex123 > /var/log/vscode.log 2>&1 &",
                
                # Install common ML libraries
                "pip3 install torch torchvision transformers datasets accelerate",
                "pip3 install tensorflow numpy pandas matplotlib seaborn scikit-learn",
            ]
            
            # Write private key to temporary file
            key_file = f"/tmp/{instance.instance_id}_key"
            with open(key_file, 'w') as f:
                f.write(instance.ssh_private_key)
            os.chmod(key_file, 0o600)
            
            # Execute setup commands
            async with asyncssh.connect(
                instance.ssh_host,
                port=instance.ssh_port,
                username=instance.ssh_username,
                client_keys=[key_file]
            ) as conn:
                for cmd in setup_commands:
                    try:
                        result = await conn.run(cmd, check=False)
                        logger.debug(f"Command '{cmd}': {result.stdout}")
                    except Exception as e:
                        logger.warning(f"Setup command failed '{cmd}': {e}")
            
            # Clean up temporary key file
            os.remove(key_file)
            
            logger.info(f"Configured services for instance {instance.instance_id}")
            
        except Exception as e:
            logger.error(f"Error setting up instance services: {e}")

    async def _wait_for_vast_instance(self, session: aiohttp.ClientSession, instance_id: str, headers: Dict) -> None:
        """Wait for Vast.ai instance to be ready"""
        for _ in range(30):  # Wait up to 5 minutes
            try:
                url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("actual_status") == "running":
                            return
                await asyncio.sleep(10)
            except Exception:
                await asyncio.sleep(10)
        raise Exception("Vast.ai instance failed to start within timeout")

    async def _wait_for_lambda_instance(self, session: aiohttp.ClientSession, instance_id: str, headers: Dict) -> None:
        """Wait for Lambda Labs instance to be ready"""
        for _ in range(30):  # Wait up to 5 minutes
            try:
                url = f"https://cloud.lambdalabs.com/api/v1/instances/{instance_id}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data", {}).get("status") == "running":
                            return
                await asyncio.sleep(10)
            except Exception:
                await asyncio.sleep(10)
        raise Exception("Lambda instance failed to start within timeout")

    async def _wait_for_runpod_instance(self, session: aiohttp.ClientSession, instance_id: str, headers: Dict) -> None:
        """Wait for RunPod instance to be ready"""
        for _ in range(30):  # Wait up to 5 minutes
            try:
                query = {
                    "query": f"""
                    query {{
                        pod(input: {{podId: "{instance_id}"}}) {{
                            id
                            desiredStatus
                            lastStatusChange
                            runtime {{
                                uptimeInSeconds
                            }}
                        }}
                    }}
                    """
                }
                
                async with session.post("https://api.runpod.io/graphql", json=query, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        pod = data.get("data", {}).get("pod", {})
                        if pod.get("runtime", {}).get("uptimeInSeconds", 0) > 0:
                            return
                await asyncio.sleep(10)
            except Exception:
                await asyncio.sleep(10)
        raise Exception("RunPod instance failed to start within timeout")

    async def provision_gpu(self, provider: str, gpu_type: str, hours: int, rental_id: str) -> GPUInstance:
        """Provision GPU instance based on provider"""
        try:
            provider = provider.lower()
            
            if provider == "vast":
                return await self.create_vast_instance(gpu_type, hours, rental_id)
            elif provider == "lambda":
                return await self.create_lambda_instance(gpu_type, hours, rental_id)
            elif provider == "runpod":
                return await self.create_runpod_instance(gpu_type, hours, rental_id)
            else:
                raise ValueError(f"Provider {provider} not supported for provisioning")
                
        except Exception as e:
            logger.error(f"Error provisioning GPU {gpu_type} on {provider}: {e}")
            raise

    async def terminate_instance(self, rental_id: str) -> bool:
        """Terminate GPU instance"""
        try:
            if rental_id not in self.active_instances:
                logger.warning(f"Instance {rental_id} not found in active instances")
                return False
            
            instance = self.active_instances[rental_id]
            
            if instance.provider == "vast":
                await self._terminate_vast_instance(instance.instance_id)
            elif instance.provider == "lambda":
                await self._terminate_lambda_instance(instance.instance_id)
            elif instance.provider == "runpod":
                await self._terminate_runpod_instance(instance.instance_id)
            
            # Remove from active instances
            del self.active_instances[rental_id]
            
            # Clean up SSH keys
            key_files = [
                self.ssh_keys_path / f"{instance.provider}_{rental_id}_private.pem",
                self.ssh_keys_path / f"{instance.provider}_{rental_id}_public.pub"
            ]
            for key_file in key_files:
                if key_file.exists():
                    key_file.unlink()
            
            logger.info(f"Terminated instance {instance.instance_id} for rental {rental_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating instance for rental {rental_id}: {e}")
            return False

    async def _terminate_vast_instance(self, instance_id: str) -> None:
        """Terminate Vast.ai instance"""
        if not self.vast_api_key:
            return
        
        async with aiohttp.ClientSession() as session:
            url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={self.vast_api_key}"
            headers = {"Authorization": f"Bearer {self.vast_api_key}"}
            
            async with session.delete(url, headers=headers) as response:
                if response.status in [200, 404]:
                    logger.info(f"Terminated Vast.ai instance: {instance_id}")
                else:
                    logger.error(f"Failed to terminate Vast.ai instance {instance_id}: {response.status}")

    async def _terminate_lambda_instance(self, instance_id: str) -> None:
        """Terminate Lambda Labs instance"""
        if not self.lambda_api_key:
            return
        
        async with aiohttp.ClientSession() as session:
            url = f"https://cloud.lambdalabs.com/api/v1/instance-operations/terminate"
            headers = {
                "Authorization": f"Bearer {self.lambda_api_key}",
                "Content-Type": "application/json"
            }
            data = {"instance_ids": [instance_id]}
            
            async with session.post(url, json=data, headers=headers) as response:
                if response.status in [200, 404]:
                    logger.info(f"Terminated Lambda instance: {instance_id}")
                else:
                    logger.error(f"Failed to terminate Lambda instance {instance_id}: {response.status}")

    async def _terminate_runpod_instance(self, instance_id: str) -> None:
        """Terminate RunPod instance"""
        if not self.runpod_api_key:
            return
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.runpod_api_key}",
                "Content-Type": "application/json"
            }
            
            mutation = {
                "query": f"""
                mutation {{
                    podTerminate(input: {{podId: "{instance_id}"}}) {{
                        id
                    }}
                }}
                """
            }
            
            async with session.post("https://api.runpod.io/graphql", json=mutation, headers=headers) as response:
                if response.status in [200, 404]:
                    logger.info(f"Terminated RunPod instance: {instance_id}")
                else:
                    logger.error(f"Failed to terminate RunPod instance {instance_id}: {response.status}")

    def get_instance_status(self, rental_id: str) -> Optional[GPUInstance]:
        """Get current instance status"""
        return self.active_instances.get(rental_id)

    async def monitor_instances(self) -> None:
        """Monitor all active instances and handle expiration"""
        try:
            current_time = datetime.now()
            expired_instances = []
            
            for rental_id, instance in self.active_instances.items():
                if instance.expires_at and current_time > instance.expires_at:
                    expired_instances.append(rental_id)
            
            # Terminate expired instances
            for rental_id in expired_instances:
                logger.info(f"Auto-terminating expired instance: {rental_id}")
                await self.terminate_instance(rental_id)
                
        except Exception as e:
            logger.error(f"Error monitoring instances: {e}")

# Global instance
gpu_provisioning_service = GPUProvisioningService()

async def start_instance_monitoring():
    """Start background instance monitoring"""
    while True:
        try:
            await gpu_provisioning_service.monitor_instances()
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logger.error(f"Instance monitoring error: {e}")
            await asyncio.sleep(60) 