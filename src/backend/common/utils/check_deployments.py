import asyncio
import os
import sys
import traceback

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, backend_path)

try:
    from v3.common.services.foundry_service import FoundryService
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def check_deployments():
    try:
        print("🔍 Checking Azure AI Foundry model deployments...")
        foundry_service = FoundryService()
        deployments = await foundry_service.list_model_deployments()

        # Filter successful deployments
        successful_deployments = [
            d for d in deployments if d.get("status") == "Succeeded"
        ]

        print(
            f"✅ Total deployments: {len(deployments)} (Successful: {len(successful_deployments)})"
        )

        available_models = [d.get("name", "").lower() for d in successful_deployments]

        # Check what we're looking for
        required_models = ["gpt-4o", "o3", "gpt-4", "gpt-35-turbo"]

        print(f"\n🔍 Checking required models: {required_models}")
        for model in required_models:
            if model.lower() in available_models:
                print(f"✅ {model} is available")
            else:
                print(f"❌ {model} is NOT available")

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_deployments())
