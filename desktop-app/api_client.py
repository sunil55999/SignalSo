#!/usr/bin/env python3
"""
API Client for SignalOS Desktop Application
"""

import aiohttp
import json
import logging
from typing import Dict, Any, Optional

class APIClient:
    """Main API client for server communication"""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url
        self.session = None
        self.logger = logging.getLogger('APIClient')
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def get(self, endpoint: str) -> Dict[str, Any]:
        """GET request"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            url = f"{self.server_url}{endpoint}"
            async with self.session.get(url) as response:
                return await response.json()
        except Exception as e:
            self.logger.error(f"GET {endpoint} failed: {e}")
            return {"error": str(e)}
            
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            url = f"{self.server_url}{endpoint}"
            async with self.session.post(url, json=data) as response:
                return await response.json()
        except Exception as e:
            self.logger.error(f"POST {endpoint} failed: {e}")
            return {"error": str(e)}