#!/usr/bin/env python3
"""Check Supabase Storage directly using REST API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
import requests

def check_storage():
    """Check storage using direct REST API."""

    # Supabase Storage API endpoint
    url = f"{settings.SUPABASE_URL}/storage/v1/object/list/{settings.SUPABASE_BUCKET}"

    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    }

    # List files with prefix
    for prefix in ['', 'uploads', 'samples']:
        print(f"\n📁 Checking '{prefix}' folder...")

        payload = {
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"}
        }

        if prefix:
            payload["prefix"] = prefix

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            files = response.json()
            print(f"   Found {len(files)} items")

            # Group by type
            folders = [f for f in files if f.get('id') is None]
            files_list = [f for f in files if f.get('id') is not None]

            print(f"   - Folders: {len(folders)}")
            print(f"   - Files: {len(files_list)}")

            if files_list:
                print(f"\n   First 5 files:")
                for f in files_list[:5]:
                    name = f.get('name', 'unknown')
                    size = f.get('metadata', {}).get('size', 0)
                    print(f"     - {name} ({size} bytes)")

                if len(files_list) > 5:
                    print(f"     ... and {len(files_list) - 5} more")

        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    check_storage()
