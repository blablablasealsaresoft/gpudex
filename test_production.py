#!/usr/bin/env python3
"""
GPUDex Production Testing Script
Comprehensive validation of all enterprise features, performance, and security.
"""

import asyncio
import aiohttp
import json
import time
import random
import sys
from typing import Dict, List, Any
from datetime import datetime
import subprocess
import os

class ProductionTester:
    """Comprehensive production testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        
    async def setup(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        print("🔧 Setting up production test environment...")
        
    async def cleanup(self):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details and not passed:
            print(f"    └─ {details}")
        
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
    
    async def test_health_check(self):
        """Test basic health check endpoint."""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                data = await response.json()
                passed = response.status == 200 and data.get("status") == "healthy"
                self.log_result("Health Check", passed, 
                              f"Status: {response.status}, Response: {data}")
        except Exception as e:
            self.log_result("Health Check", False, str(e))
    
    async def test_security_headers(self):
        """Test security headers are present."""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                headers = response.headers
                
                required_headers = [
                    "X-Content-Type-Options",
                    "X-Frame-Options", 
                    "X-XSS-Protection",
                    "Strict-Transport-Security",
                    "Referrer-Policy"
                ]
                
                missing_headers = [h for h in required_headers if h not in headers]
                passed = len(missing_headers) == 0
                
                details = f"Missing headers: {missing_headers}" if missing_headers else "All security headers present"
                self.log_result("Security Headers", passed, details)
                
        except Exception as e:
            self.log_result("Security Headers", False, str(e))
    
    async def test_cors_policy(self):
        """Test CORS policy."""
        try:
            headers = {"Origin": "https://malicious-site.com"}
            async with self.session.options(f"{self.base_url}/api/v1/prices", headers=headers) as response:
                cors_header = response.headers.get("Access-Control-Allow-Origin")
                # Should not allow arbitrary origins
                passed = cors_header != "*" and cors_header != "https://malicious-site.com"
                self.log_result("CORS Policy", passed, 
                              f"CORS header: {cors_header}")
        except Exception as e:
            self.log_result("CORS Policy", False, str(e))
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(15):  # Exceed burst limit
                async with self.session.get(f"{self.base_url}/") as response:
                    responses.append(response.status)
            
            # Should get rate limited
            rate_limited = any(status == 429 for status in responses)
            self.log_result("Rate Limiting", rate_limited,
                          f"Responses: {responses}")
            
        except Exception as e:
            self.log_result("Rate Limiting", False, str(e))
    
    async def test_input_validation(self):
        """Test input validation and sanitization."""
        try:
            # Test SQL injection attempt
            malicious_gpu = "'; DROP TABLE users; --"
            async with self.session.get(f"{self.base_url}/api/v1/prices", 
                                      params={"gpu": malicious_gpu}) as response:
                # Should reject malicious input
                passed = response.status in [400, 422]
                self.log_result("SQL Injection Protection", passed,
                              f"Status: {response.status}")
            
            # Test XSS attempt
            malicious_region = "<script>alert('xss')</script>"
            async with self.session.get(f"{self.base_url}/api/v1/prices",
                                      params={"region": malicious_region}) as response:
                passed = response.status in [400, 422]
                self.log_result("XSS Protection", passed,
                              f"Status: {response.status}")
                
        except Exception as e:
            self.log_result("Input Validation", False, str(e))
    
    async def test_api_endpoints(self):
        """Test all API endpoints functionality."""
        endpoints = [
            ("/api/v1/prices", "GET", {"gpu": "4090", "region": "us-east"}),
            ("/api/v1/providers", "GET", {}),
            ("/api/v1/analytics", "GET", {}),
            ("/api/v1/pricing", "GET", {}),
        ]
        
        for endpoint, method, params in endpoints:
            try:
                async with self.session.request(method, f"{self.base_url}{endpoint}", 
                                              params=params) as response:
                    passed = response.status == 200
                    data = await response.text()
                    self.log_result(f"API {method} {endpoint}", passed,
                                  f"Status: {response.status}")
            except Exception as e:
                self.log_result(f"API {method} {endpoint}", False, str(e))
    
    async def test_authentication_endpoints(self):
        """Test authentication system."""
        try:
            # Test registration
            user_data = {
                "email": f"test{random.randint(1000,9999)}@example.com",
                "username": f"testuser{random.randint(1000,9999)}",
                "password": "TestPassword123!",
                "full_name": "Test User"
            }
            
            async with self.session.post(f"{self.base_url}/auth/register", 
                                       json=user_data) as response:
                passed = response.status == 201
                self.log_result("User Registration", passed,
                              f"Status: {response.status}")
                
                if passed:
                    data = await response.json()
                    access_token = data.get("access_token")
                    
                    # Test protected endpoint
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with self.session.get(f"{self.base_url}/auth/profile",
                                              headers=headers) as auth_response:
                        auth_passed = auth_response.status == 200
                        self.log_result("Protected Endpoint Access", auth_passed,
                                      f"Status: {auth_response.status}")
                
        except Exception as e:
            self.log_result("Authentication System", False, str(e))
    
    async def test_performance(self):
        """Test performance benchmarks."""
        try:
            # Test response times
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/api/v1/prices") as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                passed = response_time < 2000  # Under 2 seconds
                self.log_result("Response Time", passed,
                              f"Response time: {response_time:.2f}ms")
            
            # Test concurrent requests
            async def make_request():
                async with self.session.get(f"{self.base_url}/api/v1/prices") as response:
                    return response.status == 200
            
            start_time = time.time()
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            concurrent_time = (end_time - start_time) * 1000
            success_rate = sum(results) / len(results)
            
            passed = concurrent_time < 5000 and success_rate > 0.8
            self.log_result("Concurrent Performance", passed,
                          f"Time: {concurrent_time:.2f}ms, Success rate: {success_rate:.2%}")
            
        except Exception as e:
            self.log_result("Performance Tests", False, str(e))
    
    async def test_caching(self):
        """Test caching functionality."""
        try:
            # First request (should cache)
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/api/v1/prices") as response1:
                first_time = time.time() - start_time
                data1 = await response1.json()
            
            # Second request (should be cached)
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/api/v1/prices") as response2:
                second_time = time.time() - start_time
                data2 = await response2.json()
            
            # Cached response should be faster
            passed = second_time < first_time and data1 == data2
            self.log_result("Caching Performance", passed,
                          f"First: {first_time:.3f}s, Second: {second_time:.3f}s")
            
        except Exception as e:
            self.log_result("Caching Tests", False, str(e))
    
    async def test_database_connection(self):
        """Test database connectivity."""
        try:
            # Test endpoint that requires database
            async with self.session.get(f"{self.base_url}/api/v1/analytics") as response:
                passed = response.status == 200
                data = await response.json()
                
                # Should have real data structure
                has_data = isinstance(data, dict) and len(data) > 0
                self.log_result("Database Connection", passed and has_data,
                              f"Status: {response.status}, Has data: {has_data}")
                
        except Exception as e:
            self.log_result("Database Tests", False, str(e))
    
    async def test_error_handling(self):
        """Test error handling and recovery."""
        try:
            # Test 404 handling
            async with self.session.get(f"{self.base_url}/nonexistent") as response:
                passed = response.status == 404
                self.log_result("404 Error Handling", passed,
                              f"Status: {response.status}")
            
            # Test malformed request
            async with self.session.post(f"{self.base_url}/api/v1/alerts",
                                       data="invalid json") as response:
                passed = response.status in [400, 422]
                self.log_result("Malformed Request Handling", passed,
                              f"Status: {response.status}")
                
        except Exception as e:
            self.log_result("Error Handling", False, str(e))
    
    def test_docker_health(self):
        """Test Docker container health."""
        try:
            # Check if containers are running
            result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}"],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                containers_running = "gpudex" in output and "Up" in output
                self.log_result("Docker Container Health", containers_running,
                              f"Docker output: {output.strip()}")
            else:
                self.log_result("Docker Container Health", False,
                              f"Docker command failed: {result.stderr}")
                
        except Exception as e:
            self.log_result("Docker Health Check", False, str(e))
    
    async def run_all_tests(self):
        """Run all production tests."""
        print("🚀 Starting GPUDex Production Test Suite")
        print("=" * 50)
        
        await self.setup()
        
        # Core functionality tests
        await self.test_health_check()
        await self.test_api_endpoints()
        
        # Security tests
        await self.test_security_headers()
        await self.test_cors_policy()
        await self.test_rate_limiting()
        await self.test_input_validation()
        
        # Performance tests
        await self.test_performance()
        await self.test_caching()
        
        # Infrastructure tests
        await self.test_database_connection()
        await self.test_error_handling()
        self.test_docker_health()
        
        # Authentication tests (if enabled)
        # await self.test_authentication_endpoints()
        
        await self.cleanup()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['failed'] > 0:
            print("\n⚠️  Failed Tests:")
            for test in self.results['tests']:
                if not test['passed']:
                    print(f"   • {test['name']}: {test['details']}")
        
        return self.results['failed'] == 0

async def main():
    """Main test runner."""
    # Check if backend is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backend_running = sock.connect_ex(('localhost', 8000)) == 0
    sock.close()
    
    if not backend_running:
        print("❌ Backend not running on localhost:8000")
        print("🔧 Start with: docker-compose up -d")
        sys.exit(1)
    
    tester = ProductionTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Production system is ready.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please review and fix issues.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 