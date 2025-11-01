#!/usr/bin/env python3
"""
Test script for file upload functionality
"""
import requests
import sys
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8000/api/upload"


def test_upload(file_path):
    """Test uploading a file to the API"""

    file_path = Path(file_path)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False

    print(f"Testing upload of: {file_path.name}")
    print(f"File size: {file_path.stat().st_size} bytes")

    # Prepare the file for upload
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/octet-stream")}

        print(f"\nSending POST request to {API_URL}...")

        try:
            response = requests.post(API_URL, files=files)

            print(f"Status code: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response body: {response.text}")

            if response.status_code == 200:
                print("\n✅ Upload successful!")
                data = response.json()
                print(f"Project ID: {data.get('project_id')}")
                print(f"Filename: {data.get('filename')}")
                print(f"Short Link: {data.get('short_link')}")
                return True
            else:
                print(f"\n❌ Upload failed with status {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"\n❌ Connection error: Cannot connect to {API_URL}")
            print("Make sure the backend server is running!")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_upload.py <path_to_esx_file>")
        print("\nExample:")
        print('  python test_upload.py "projects/wine office.esx"')
        sys.exit(1)

    file_path = sys.argv[1]
    success = test_upload(file_path)
    sys.exit(0 if success else 1)
