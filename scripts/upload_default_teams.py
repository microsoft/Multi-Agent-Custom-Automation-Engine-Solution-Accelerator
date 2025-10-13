#!/usr/bin/env python3
"""
Upload default agent teams to the database with specific IDs.
This script uploads the default teams (HR, Marketing, Retail, Finance) with predefined GUIDs
so they can be accessed by the frontend.
"""

import sys
import json
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment first
env_file = backend_dir / ".env"
load_dotenv(env_file)

# Now import after adding to path
from common.database.database_factory import DatabaseFactory

# Default team IDs (matching what the frontend expects)
DEFAULT_TEAMS = {
    "hr.json": "00000000-0000-0000-0000-000000000001",
    "marketing.json": "00000000-0000-0000-0000-000000000002",
    "retail.json": "00000000-0000-0000-0000-000000000003",
    "finance_forecasting.json": "00000000-0000-0000-0000-000000000004",
}

# Additional teams (will get auto-generated GUIDs)
ADDITIONAL_TEAMS = [
    "forecasting.json",
    "customer_intelligence.json",
    "marketing_intelligence.json",
    "retail_operations.json",
    "revenue_optimization.json",
]


async def upload_team_config(team_file: Path, team_id: str = None, user_id: str = "system"):
    """Upload a team configuration file to the database."""
    
    print(f"\n{'='*70}")
    print(f"Uploading: {team_file.name}")
    print(f"{'='*70}")
    
    try:
        # Read team configuration
        with open(team_file, 'r', encoding='utf-8') as f:
            team_config = json.load(f)
        
        print(f"  Team Name: {team_config.get('name', 'Unknown')}")
        print(f"  Description: {team_config.get('description', 'No description')[:60]}...")
        print(f"  Agents: {len(team_config.get('agents', []))}")
        
        # Get database instance
        memory_store = await DatabaseFactory.get_database(user_id=user_id)
        
        # Import TeamService
        from v3.common.services.team_service import TeamService
        team_service = TeamService(memory_store)
        
        # If team_id is provided, modify the JSON to include it
        if team_id:
            team_config['id'] = team_id
            team_config['team_id'] = team_id
            print(f"  Using fixed Team ID: {team_id}")
        
        # Validate and parse the team configuration
        team_configuration = await team_service.validate_and_parse_team_config(
            team_config, user_id
        )
        
        # Store in database
        await memory_store.add_team(team_configuration)
        
        print(f"  [OK] Successfully uploaded!")
        print(f"  Team ID: {team_configuration.team_id}")
        
        return team_configuration
        
    except Exception as e:
        print(f"  [ERROR] Error uploading {team_file.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main function to upload all default teams."""
    
    print("\n" + "="*70)
    print("  DEFAULT AGENT TEAMS UPLOADER")
    print("="*70)
    print()
    print("This script uploads the default agent teams to the database.")
    print("The first 4 teams will use fixed GUIDs that the frontend expects.")
    print()
    
    # Get team files directory
    teams_dir = Path(__file__).parent.parent / "data" / "agent_teams"
    
    if not teams_dir.exists():
        print(f"[ERROR] Team directory not found: {teams_dir}")
        return
    
    print(f"[INFO] Team directory: {teams_dir}")
    print()
    
    uploaded_count = 0
    failed_count = 0
    
    # Upload default teams with fixed IDs
    print("="*70)
    print("UPLOADING DEFAULT TEAMS (Fixed IDs)")
    print("="*70)
    
    for team_file, team_id in DEFAULT_TEAMS.items():
        team_path = teams_dir / team_file
        if team_path.exists():
            result = await upload_team_config(team_path, team_id=team_id)
            if result:
                uploaded_count += 1
            else:
                failed_count += 1
        else:
            print(f"\n[WARN]  Team file not found: {team_file}")
            failed_count += 1
    
    # Upload additional teams (auto-generated IDs)
    print("\n" + "="*70)
    print("UPLOADING ADDITIONAL TEAMS (Auto-generated IDs)")
    print("="*70)
    
    for team_file in ADDITIONAL_TEAMS:
        team_path = teams_dir / team_file
        if team_path.exists():
            result = await upload_team_config(team_path)
            if result:
                uploaded_count += 1
            else:
                failed_count += 1
        else:
            print(f"\n[WARN]  Team file not found: {team_file}")
    
    # Summary
    print("\n" + "="*70)
    print("UPLOAD SUMMARY")
    print("="*70)
    print(f"  [OK] Successfully uploaded: {uploaded_count}")
    if failed_count > 0:
        print(f"  [ERROR] Failed: {failed_count}")
    print("="*70)
    print()
    
    if uploaded_count > 0:
        print("[OK] Default teams are now available in the database!")
        print()
        print("You can now:")
        print("  1. Refresh your frontend at http://localhost:3001")
        print("  2. The team initialization should work")
        print("  3. Test with: python scripts/testing/test_analytics_api.py")
        print()
    else:
        print("[WARN]  No teams were uploaded. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())

