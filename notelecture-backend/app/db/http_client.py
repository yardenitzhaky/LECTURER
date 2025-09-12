# app/db/http_client.py
"""
HTTP-based database client using Supabase REST API to bypass network connection issues in Vercel
"""
import json
import uuid
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any
from app.core.config import settings

class SupabaseHTTPClient:
    def __init__(self):
        self.base_url = "https://caefcrwnmtuybgqeynim.supabase.co"
        self.anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhZWZjcndubXR1eWJncWV5bmltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU2MDE5MjEsImV4cCI6MjA3MTE3NzkyMX0.zQBJUXYZTYsjO8L0FMfuhhZDaIoLHQsIqorhhCrSk40"
        
        # Get service role key from settings if available
        self.service_key = getattr(settings, 'supabase_service_key', None)
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, use_service_key: bool = False) -> Dict[Any, Any]:
        """Make HTTP request to Supabase REST API"""
        url = f"{self.base_url}/rest/v1/{endpoint}"
        
        # Use service key for admin operations, anon key otherwise
        api_key = self.service_key if (use_service_key and self.service_key) else self.anon_key
        
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Prepare request data
        request_data = None
        if data:
            request_data = json.dumps(data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        try:
            endpoint = f"users?email=eq.{urllib.parse.quote(email)}&select=*"
            result = self._make_request("GET", endpoint)
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    async def create_user(self, email: str) -> Dict:
        """Create a new user for OAuth"""
        try:
            user_id = str(uuid.uuid4())
            
            # Create a simple hash for OAuth users  
            simple_hash = hashlib.sha256(f"oauth_{email}".encode()).hexdigest()
            
            user_data = {
                "id": user_id,
                "email": email,
                "hashed_password": simple_hash,
                "is_active": True,
                "is_verified": True,
                "created_at": "now()"
            }
            
            result = self._make_request("POST", "users", user_data, use_service_key=True)
            return result[0] if isinstance(result, list) else result
            
        except Exception as e:
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def test_connection(self) -> Dict:
        """Test the HTTP connection to Supabase"""
        try:
            # Simple test query
            result = self._make_request("GET", "users?limit=1&select=count")
            return {"status": "connected", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global instance
supabase_http = SupabaseHTTPClient()