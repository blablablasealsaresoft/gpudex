import psutil
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import aiofiles
import os
import json
from sqlalchemy import create_engine, text
from redis import Redis
import socket

logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    service: str
    status: str  # healthy, warning, critical
    last_check: datetime
    response_time: float
    details: Dict[str, Any]
    error_message: Optional[str] = None

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    active_connections: int
    process_count: int

class MonitoringService:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.health_checks = {}
        self.metrics_history = []
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'response_time': 5.0,
            'error_rate': 10.0
        }
        
        # Prometheus metrics
        self.request_count = Counter(
            'gpudex_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'gpudex_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.system_cpu = Gauge(
            'gpudex_system_cpu_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory = Gauge(
            'gpudex_system_memory_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk = Gauge(
            'gpudex_system_disk_percent',
            'System disk usage percentage',
            registry=self.registry
        )
        
        self.active_alerts = Gauge(
            'gpudex_active_alerts',
            'Number of active alerts',
            registry=self.registry
        )
        
        self.api_calls_total = Counter(
            'gpudex_api_calls_total',
            'Total API calls',
            ['provider', 'status'],
            registry=self.registry
        )
        
        self.cache_hits = Counter(
            'gpudex_cache_hits_total',
            'Total cache hits',
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'gpudex_cache_misses_total',
            'Total cache misses',
            registry=self.registry
        )
        
        logger.info("Monitoring service initialized")

    async def check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
            engine = create_engine(database_url)
            
            with engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Test table access
                result = conn.execute(text("SELECT COUNT(*) FROM alerts"))
                alert_count = result.fetchone()[0]
                
                # Test performance with a simple query
                result = conn.execute(text("SELECT version()"))
                db_version = result.fetchone()[0]
                
            response_time = time.time() - start_time
            
            return HealthCheck(
                service="database",
                status="healthy" if response_time < 1.0 else "warning",
                last_check=datetime.now(),
                response_time=response_time,
                details={
                    "alert_count": alert_count,
                    "version": db_version,
                    "connection_time": response_time
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheck(
                service="database",
                status="critical",
                last_check=datetime.now(),
                response_time=response_time,
                details={},
                error_message=str(e)
            )

    async def check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            redis_client = Redis.from_url(redis_url)
            
            # Test basic connectivity
            pong = redis_client.ping()
            
            # Test read/write operations
            test_key = "health_check_test"
            redis_client.set(test_key, "test_value", ex=60)
            retrieved_value = redis_client.get(test_key)
            redis_client.delete(test_key)
            
            # Get Redis info
            info = redis_client.info()
            
            response_time = time.time() - start_time
            
            return HealthCheck(
                service="redis",
                status="healthy" if response_time < 0.5 else "warning",
                last_check=datetime.now(),
                response_time=response_time,
                details={
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "ping_successful": pong
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheck(
                service="redis",
                status="critical",
                last_check=datetime.now(),
                response_time=response_time,
                details={},
                error_message=str(e)
            )

    async def check_external_apis_health(self) -> List[HealthCheck]:
        """Check external API endpoints health"""
        checks = []
        
        # Test endpoints for various providers
        test_endpoints = [
            ("vast_api", "https://vast.ai/api/v0/instances", {"timeout": 10}),
            ("runpod_api", "https://api.runpod.io/graphql", {"timeout": 10}),
            ("lambda_api", "https://cloud.lambdalabs.com/api/v1/instance-types", {"timeout": 10})
        ]
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for name, url, options in test_endpoints:
                start_time = time.time()
                
                try:
                    timeout = aiohttp.ClientTimeout(total=options.get("timeout", 10))
                    async with session.get(url, timeout=timeout) as response:
                        response_time = time.time() - start_time
                        
                        checks.append(HealthCheck(
                            service=name,
                            status="healthy" if response.status == 200 and response_time < 5.0 else "warning",
                            last_check=datetime.now(),
                            response_time=response_time,
                            details={
                                "status_code": response.status,
                                "url": url
                            }
                        ))
                        
                except Exception as e:
                    response_time = time.time() - start_time
                    checks.append(HealthCheck(
                        service=name,
                        status="critical",
                        last_check=datetime.now(),
                        response_time=response_time,
                        details={"url": url},
                        error_message=str(e)
                    ))
        
        return checks

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Network stats
        network = psutil.net_io_counters()
        network_sent = network.bytes_sent
        network_recv = network.bytes_recv
        
        # Process count
        process_count = len(psutil.pids())
        
        # Active connections
        try:
            connections = psutil.net_connections()
            active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
        except (psutil.AccessDenied, AttributeError):
            active_connections = 0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            network_sent=network_sent,
            network_recv=network_recv,
            active_connections=active_connections,
            process_count=process_count
        )

    def update_prometheus_metrics(self, metrics: SystemMetrics):
        """Update Prometheus metrics with current system state"""
        self.system_cpu.set(metrics.cpu_percent)
        self.system_memory.set(metrics.memory_percent)
        self.system_disk.set(metrics.disk_percent)

    def _serialize_datetime_dict(self, data: dict) -> dict:
        """Convert datetime objects to ISO format strings in a dictionary"""
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_datetime_dict(value)
            elif isinstance(value, list):
                result[key] = [self._serialize_datetime_dict(item) if isinstance(item, dict) 
                             else item.isoformat() if isinstance(item, datetime) 
                             else item for item in value]
            else:
                result[key] = value
        return result

    async def perform_health_checks(self) -> Dict[str, Any]:
        """Perform all health checks and return comprehensive status"""
        health_checks = {}
        
        # System health
        system_metrics = self.collect_system_metrics()
        self.update_prometheus_metrics(system_metrics)
        
        health_checks["system"] = {
            "status": "healthy",
            "metrics": self._serialize_datetime_dict(asdict(system_metrics))
        }
        
        # Check for system alerts
        alerts = []
        if system_metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {system_metrics.cpu_percent:.1f}%")
        
        if system_metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append(f"High memory usage: {system_metrics.memory_percent:.1f}%")
        
        if system_metrics.disk_percent > self.alert_thresholds['disk_percent']:
            alerts.append(f"High disk usage: {system_metrics.disk_percent:.1f}%")
        
        if alerts:
            health_checks["system"]["status"] = "warning"
            health_checks["system"]["alerts"] = alerts
        
        # Database health
        db_check = await self.check_database_health()
        health_checks["database"] = self._serialize_datetime_dict(asdict(db_check))
        
        # Redis health
        redis_check = await self.check_redis_health()
        health_checks["redis"] = self._serialize_datetime_dict(asdict(redis_check))
        
        # External APIs health
        api_checks = await self.check_external_apis_health()
        health_checks["external_apis"] = [self._serialize_datetime_dict(asdict(check)) for check in api_checks]
        
        # Overall status
        all_statuses = [health_checks["system"]["status"], db_check.status, redis_check.status]
        all_statuses.extend([check.status for check in api_checks])
        
        if "critical" in all_statuses:
            overall_status = "critical"
        elif "warning" in all_statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        # Update active alerts count
        active_alert_count = len(alerts) + len([s for s in all_statuses if s in ["warning", "critical"]])
        self.active_alerts.set(active_alert_count)
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": health_checks,
            "active_alerts": active_alert_count
        }

    def record_api_call(self, provider: str, status: str):
        """Record API call metrics"""
        self.api_calls_total.labels(provider=provider, status=status).inc()

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        self.request_count.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits.inc()

    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses.inc()

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest(self.registry).decode('utf-8')

    async def save_metrics_history(self, metrics: SystemMetrics, max_history: int = 1000):
        """Save metrics to history and maintain size limit"""
        self.metrics_history.append(asdict(metrics))
        
        # Keep only the most recent metrics
        if len(self.metrics_history) > max_history:
            self.metrics_history = self.metrics_history[-max_history:]
        
        # Optionally save to file for persistence
        metrics_file = "metrics_history.json"
        try:
            async with aiofiles.open(metrics_file, 'w') as f:
                await f.write(json.dumps(self.metrics_history, default=str, indent=2))
        except Exception as e:
            logger.error(f"Failed to save metrics history: {e}")

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time period"""
        if not self.metrics_history:
            return {"error": "No metrics history available"}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": f"No metrics available for the last {hours} hours"}
        
        # Calculate averages and peaks
        cpu_values = [m['cpu_percent'] for m in recent_metrics]
        memory_values = [m['memory_percent'] for m in recent_metrics]
        
        return {
            "time_period_hours": hours,
            "total_measurements": len(recent_metrics),
            "cpu": {
                "average": sum(cpu_values) / len(cpu_values),
                "peak": max(cpu_values),
                "current": cpu_values[-1] if cpu_values else 0
            },
            "memory": {
                "average": sum(memory_values) / len(memory_values),
                "peak": max(memory_values),
                "current": memory_values[-1] if memory_values else 0
            },
            "last_updated": recent_metrics[-1]['timestamp'] if recent_metrics else None
        }

    async def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        disk_usage = psutil.disk_usage('/')
        
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        used_percent = (disk_usage.used / disk_usage.total) * 100
        
        status = "healthy"
        if used_percent > 90:
            status = "critical"
        elif used_percent > 80:
            status = "warning"
        
        return {
            "status": status,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 2),
            "warning_threshold": 80,
            "critical_threshold": 90
        }

    async def check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity to key services"""
        connectivity_results = {}
        
        test_hosts = [
            ("google_dns", "8.8.8.8", 53),
            ("cloudflare_dns", "1.1.1.1", 53),
            ("vast_ai", "vast.ai", 443),
            ("runpod", "runpod.io", 443)
        ]
        
        for name, host, port in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                connectivity_results[name] = {
                    "status": "connected" if result == 0 else "failed",
                    "host": host,
                    "port": port
                }
            except Exception as e:
                connectivity_results[name] = {
                    "status": "error",
                    "host": host,
                    "port": port,
                    "error": str(e)
                }
        
        # Overall connectivity status
        all_connected = all(
            result["status"] == "connected" 
            for result in connectivity_results.values()
        )
        
        return {
            "overall_status": "healthy" if all_connected else "warning",
            "tests": connectivity_results
        }

# Global monitoring service instance
monitoring_service = MonitoringService()

# Background task to collect metrics
async def collect_metrics_task():
    """Background task to collect and store metrics"""
    while True:
        try:
            metrics = monitoring_service.collect_system_metrics()
            await monitoring_service.save_metrics_history(metrics)
            monitoring_service.update_prometheus_metrics(metrics)
            
            # Log system status periodically
            if metrics.cpu_percent > 80 or metrics.memory_percent > 80:
                logger.warning(
                    f"High resource usage - CPU: {metrics.cpu_percent:.1f}%, "
                    f"Memory: {metrics.memory_percent:.1f}%"
                )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        # Wait 30 seconds before next collection
        await asyncio.sleep(30)

# Start the metrics collection task
def start_monitoring():
    """Start the monitoring background task"""
    asyncio.create_task(collect_metrics_task())
    logger.info("Monitoring service started") 