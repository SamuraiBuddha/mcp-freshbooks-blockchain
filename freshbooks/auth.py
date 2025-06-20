"""OAuth2 authentication for Freshbooks API."""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import web
import aiofiles
from pathlib import Path
import webbrowser
import secrets
import base64
from urllib.parse import urlencode


class FreshbooksAuth:
    """Handle OAuth2 authentication for Freshbooks."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file = Path.home() / ".freshbooks_token.json"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.account_id: Optional[str] = None
        
        # OAuth2 endpoints
        self.auth_url = "https://auth.freshbooks.com/oauth/authorize"
        self.token_url = "https://api.freshbooks.com/auth/oauth/token"
        self.api_base = "https://api.freshbooks.com"
    
    async def authenticate(self) -> bool:
        """Authenticate with Freshbooks."""
        # Try to load existing token
        if await self.load_token():
            if await self.is_token_valid():
                return True
            elif self.refresh_token:
                return await self.refresh_access_token()
        
        # Need new authentication
        return await self.authorize()
    
    async def load_token(self) -> bool:
        """Load token from file."""
        if not self.token_file.exists():
            return False
        
        try:
            async with aiofiles.open(self.token_file, 'r') as f:
                token_data = json.loads(await f.read())
            
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            self.account_id = token_data.get("account_id")
            
            if token_data.get("expires_at"):
                self.token_expires = datetime.fromisoformat(token_data["expires_at"])
            
            return bool(self.access_token)
        except Exception:
            return False
    
    async def save_token(self) -> None:
        """Save token to file."""
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "account_id": self.account_id,
            "expires_at": self.token_expires.isoformat() if self.token_expires else None
        }
        
        async with aiofiles.open(self.token_file, 'w') as f:
            await f.write(json.dumps(token_data, indent=2))
        
        # Set restrictive permissions
        os.chmod(self.token_file, 0o600)
    
    async def is_token_valid(self) -> bool:
        """Check if current token is valid."""
        if not self.access_token:
            return False
        
        if self.token_expires and datetime.now() >= self.token_expires:
            return False
        
        # Test token with a simple API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                async with session.get(f"{self.api_base}/auth/api/v1/users/me", headers=headers) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def authorize(self) -> bool:
        """Start OAuth2 authorization flow."""
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        # Start local server to handle callback
        auth_code = None
        auth_state = None
        
        async def handle_callback(request):
            nonlocal auth_code, auth_state
            auth_code = request.query.get("code")
            auth_state = request.query.get("state")
            
            html = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to Claude.</p>
                <script>window.close();</script>
            </body>
            </html>
            """
            return web.Response(text=html, content_type="text/html")
        
        app = web.Application()
        app.router.add_get("/callback", handle_callback)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 8080)
        await site.start()
        
        print(f"\nPlease visit this URL to authorize: {auth_url}\n")
        webbrowser.open(auth_url)
        
        # Wait for callback
        timeout = 300  # 5 minutes
        start_time = datetime.now()
        
        while not auth_code and (datetime.now() - start_time).seconds < timeout:
            await asyncio.sleep(1)
        
        await runner.cleanup()
        
        if not auth_code or auth_state != state:
            return False
        
        # Exchange code for token
        return await self.exchange_code_for_token(auth_code)
    
    async def exchange_code_for_token(self, code: str) -> bool:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as resp:
                if resp.status != 200:
                    return False
                
                token_data = await resp.json()
                
                self.access_token = token_data["access_token"]
                self.refresh_token = token_data.get("refresh_token")
                self.account_id = token_data.get("account_id")
                
                # Calculate expiration
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                
                await self.save_token()
                return True
    
    async def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            return False
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as resp:
                if resp.status != 200:
                    return False
                
                token_data = await resp.json()
                
                self.access_token = token_data["access_token"]
                if "refresh_token" in token_data:
                    self.refresh_token = token_data["refresh_token"]
                
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                
                await self.save_token()
                return True
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }