#!/usr/bin/env python
"""
Route Verification Utility for AI Calendar Backend

This script tests various routes to ensure they're accessible on the deployment platform.
Run it after deploying to verify all routes are working properly.
"""

import requests
import sys
import json


def test_routes(base_url):
    """Test all available routes on the deployed backend."""
    print(f"Testing routes on: {base_url}")
    print("-" * 50)

    # All routes to test (with and without /api prefix)
    routes = [
        "/",
        "/api",
        "/health",
        "/api/health",
        "/healthcheck",
        "/events",
        "/api/events",
    ]

    for route in routes:
        full_url = f"{base_url.rstrip('/')}{route}"
        print(f"Testing: {full_url}")

        try:
            response = requests.get(full_url, timeout=5)
            status = response.status_code
            content_type = response.headers.get("Content-Type", "")

            print(f"  Status: {status}")
            print(f"  Content-Type: {content_type}")

            if "application/json" in content_type:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                except json.JSONDecodeError:
                    print(f"  Response: {response.text[:200]}...")
            else:
                print(f"  Response: {response.text[:200]}...")

        except requests.exceptions.RequestException as e:
            print(f"  Error: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_routes.py <base_url>")
        print(
            "Example: python verify_routes.py "
            "https://ai-calendar-backend-x1k0.onrender.com"
        )
        sys.exit(1)

    base_url = sys.argv[1]
    test_routes(base_url)
