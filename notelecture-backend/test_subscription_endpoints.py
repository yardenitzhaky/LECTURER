#!/usr/bin/env python3
"""
Test script for subscription endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_endpoints():
    """Test subscription endpoints"""
    
    print("Testing subscription endpoints...\n")
    
    # Test 1: Get subscription plans (no auth required)
    print("1. Testing GET /subscriptions/plans")
    try:
        response = requests.get(f"{BASE_URL}/subscriptions/plans")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            plans = response.json()["plans"]
            print(f"   Found {len(plans)} subscription plans")
            for plan in plans:
                print(f"   - {plan['name']}: ${plan['price']} for {plan['duration_days']} days ({plan['lecture_limit']} lectures)")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*60)
    print("Note: Other endpoints require authentication.")
    print("To test with authentication, you would need a valid JWT token.")
    print("="*60)

if __name__ == "__main__":
    test_endpoints()