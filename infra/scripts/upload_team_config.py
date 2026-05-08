import sys
import os
import uuid
import glob
import requests
import json

# Sentinel team_id that triggers auto-discovery of all content_packs/*/agent_teams/*.json
CONTENT_PACKS_SENTINEL = "content-packs"

# Stable UUID namespace for deriving deterministic team_ids from pack folder names.
# Changing this value will cause all auto-discovered packs to be re-created with new IDs.
_PACK_UUID_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000aaaa")


def derive_pack_team_id(pack_name: str) -> str:
    """Return a deterministic UUID for a content pack based on its folder name."""
    return str(uuid.uuid5(_PACK_UUID_NAMESPACE, pack_name))


def check_team_exists(backend_url, team_id, user_principal_id):
    """
    Check if a team already exists in the database.
    
    Args:
        backend_url: The backend endpoint URL
        team_id: The team ID to check
        user_principal_id: User principal ID for authentication
        
    Returns:
        exists: bool
    """
    check_endpoint = backend_url.rstrip('/') + f'/api/v4/team_configs/{team_id}'
    headers = {
        'x-ms-client-principal-id': user_principal_id
    }
    
    try:
        response = requests.get(check_endpoint, headers=headers)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            print(f"Error checking team {team_id}: Status {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Exception checking team {team_id}: {str(e)}")
        return False

if len(sys.argv) < 3:
    print("Usage: python upload_team_config.py <backend_endpoint> <directory_path> [<user_principal_id>] [<team_id_from_arg>]")
    print(f"  Pass team_id='{CONTENT_PACKS_SENTINEL}' to auto-discover and upload every pack under content_packs/*/agent_teams/*.json")
    sys.exit(1)

backend_url = sys.argv[1]
directory_path = sys.argv[2]
user_principal_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].strip() != "" else "00000000-0000-0000-0000-000000000000"
team_id_from_arg = sys.argv[4] if len(sys.argv) > 4 else "00000000-0000-0000-0000-000000000001"

upload_endpoint = backend_url.rstrip('/') + '/api/v4/upload_team_config'


def upload_one(file_path: str, team_id: str) -> bool:
    """Upload a single team config file. Returns True on success."""
    filename = os.path.basename(file_path)
    print(f"Uploading file:  {filename} (team_id={team_id})")

    if check_team_exists(backend_url, team_id, user_principal_id):
        print(f"Team (ID: {team_id}) already exists. Deleting to re-upload with latest config...")
        delete_endpoint = backend_url.rstrip('/') + f'/api/v4/team_configs/{team_id}'
        headers = {'x-ms-client-principal-id': user_principal_id}
        try:
            delete_response = requests.delete(delete_endpoint, headers=headers)
            if delete_response.status_code == 200:
                print(f"Successfully deleted existing team (ID: {team_id}).")
            else:
                print(f"Warning: Could not delete existing team (ID: {team_id}). Status: {delete_response.status_code}.")
        except Exception as e:
            print(f"Warning: Exception deleting team (ID: {team_id}): {str(e)}.")

    try:
        with open(file_path, 'rb') as file_data:
            files = {'file': (filename, file_data, 'application/json')}
            headers = {'x-ms-client-principal-id': user_principal_id}
            params = {'team_id': team_id}
            response = requests.post(upload_endpoint, files=files, headers=headers, params=params)
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("status") == "success":
                    print(f"Successfully uploaded team configuration: {resp_json.get('name')} (team_id: {resp_json.get('team_id')})")
                    return True
                print(f"Upload failed for {filename}. Response: {resp_json}")
                return False
            print(f"Failed to upload {filename}. Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return False


# --- Branch 1: auto-discover content packs ---
if team_id_from_arg == CONTENT_PACKS_SENTINEL:
    # Locate the repo root (this script lives at infra/scripts/upload_team_config.py)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    packs_root = os.path.join(repo_root, "content_packs")
    if not os.path.isdir(packs_root):
        print(f"No content_packs/ directory found at {packs_root}. Nothing to upload.")
        sys.exit(0)

    pattern = os.path.join(packs_root, "*", "agent_teams", "*.json")
    pack_files = sorted(glob.glob(pattern))
    if not pack_files:
        print(f"No team config JSONs found under {pattern}. Nothing to upload.")
        sys.exit(0)

    print(f"Discovered {len(pack_files)} content pack team config(s).")
    failed = 0
    for file_path in pack_files:
        # Pack name = parent-of-parent folder, e.g. content_packs/content_gen/agent_teams/foo.json -> "content_gen"
        pack_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
        # Prefer a team_id explicitly stamped in the JSON (if it is a valid UUID); otherwise derive deterministically.
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            json_team_id = cfg.get("team_id", "")
            uuid.UUID(json_team_id)  # raises if not a UUID
            team_id = json_team_id
        except (ValueError, json.JSONDecodeError, OSError):
            team_id = derive_pack_team_id(pack_name)

        if not upload_one(file_path, team_id):
            failed += 1

    if failed:
        print(f"Completed with {failed} failure(s).")
        sys.exit(1)
    print(f"Completed uploading {len(pack_files)} content pack team configuration(s).")
    sys.exit(0)


# --- Branch 2: legacy hardcoded list, for the original 6 teams under data/agent_teams ---
directory_path = os.path.abspath(directory_path)
print(f"Scanning directory: {directory_path}")

files_to_process = [
    ("hr.json", "00000000-0000-0000-0000-000000000001"),
    ("marketing.json", "00000000-0000-0000-0000-000000000002"),
    ("retail.json", "00000000-0000-0000-0000-000000000003"),
    ("rfp_analysis_team.json", "00000000-0000-0000-0000-000000000004"),
    ("contract_compliance_team.json", "00000000-0000-0000-0000-000000000005"),
    ("ad_copy_team.json", "00000000-0000-0000-0000-000000000006"),
]

uploaded_count = 0
for filename, team_id in files_to_process:
    if team_id == team_id_from_arg:
        file_path = os.path.join(directory_path, filename)
        if not os.path.isfile(file_path):
            print(f"File not found: {filename}")
            sys.exit(1)
        if not upload_one(file_path, team_id):
            sys.exit(1)
        uploaded_count += 1

print(f"Completed uploading team configurations")
