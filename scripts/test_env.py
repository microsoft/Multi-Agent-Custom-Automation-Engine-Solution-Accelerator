#!/usr/bin/env python3
"""Test environment configuration"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "backend"))

from dotenv import load_dotenv
import os

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent / "src" / "backend"
env_file = backend_dir / ".env"

print("=" * 70)
print("🔍 Testing Environment Configuration")
print("=" * 70)

if not env_file.exists():
    print(f"❌ .env file not found at: {env_file}")
    sys.exit(1)

print(f"✅ .env file found at: {env_file}\n")

# Load environment
load_dotenv(env_file)

# Check critical variables
required_vars = {
    "AZURE_OPENAI_ENDPOINT": "Azure OpenAI Endpoint",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI API Key",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "Deployment Name",
    "COSMOS_DB_ENDPOINT": "Cosmos DB Endpoint",
    "COSMOS_DB_KEY": "Cosmos DB Key",
}

print("📋 Environment Variables:")
print("-" * 70)

all_ok = True
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "KEY" in var or "SECRET" in var:
            display_value = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
        else:
            display_value = value
        print(f"✅ {description:30} {display_value}")
    else:
        print(f"❌ {description:30} NOT SET")
        all_ok = False

print("-" * 70)

if all_ok:
    print("\n✅ All required environment variables are set!")
    print("\n🚀 You can now start the backend:")
    print("   cd src/backend")
    print("   uvicorn app_kernel:app --reload --port 8000")
else:
    print("\n⚠️  Some environment variables are missing.")
    print("   Check your .env file configuration.")
    sys.exit(1)

