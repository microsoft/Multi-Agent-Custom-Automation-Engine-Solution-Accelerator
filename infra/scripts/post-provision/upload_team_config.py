import sys
import os
import time
import requests
import json

HTTP_TIMEOUT = 120  # seconds per request
MAX_RETRIES = 5
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def request_with_retry(method, url, **kwargs):
    """Wrap requests with timeout + retry/backoff for transient backend cold starts."""
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                wait = min(2 ** attempt, 30)
                print(f"  [retry {attempt}/{MAX_RETRIES}] {method} {url} -> {response.status_code}; sleeping {wait}s")
                time.sleep(wait)
                continue
            return response
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                wait = min(2 ** attempt, 30)
                print(f"  [retry {attempt}/{MAX_RETRIES}] {method} {url} -> {type(e).__name__}: {e}; sleeping {wait}s")
                time.sleep(wait)
                continue
            raise
    if last_exc:
        raise last_exc
    return response


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
        response = request_with_retry("GET", check_endpoint, headers=headers)
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
    sys.exit(1)

backend_url = sys.argv[1]
directory_path = sys.argv[2]
user_principal_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].strip() != "" else "00000000-0000-0000-0000-000000000000"
team_id_from_arg = sys.argv[4] if len(sys.argv) > 4 else "00000000-0000-0000-0000-000000000001"

# Convert to absolute path if provided as relative
directory_path = os.path.abspath(directory_path)
print(f"Scanning directory: {directory_path}")

files_to_process = [
    ("hr.json", "00000000-0000-0000-0000-000000000001"),
    ("marketing.json", "00000000-0000-0000-0000-000000000002"),
    ("retail.json", "00000000-0000-0000-0000-000000000003"),
    ("rfp_analysis_team.json", "00000000-0000-0000-0000-000000000004"),
    ("contract_compliance_team.json", "00000000-0000-0000-0000-000000000005"),
    ("ad_copy_team.json", "00000000-0000-0000-0000-000000000006"),
    ("content_gen.json", "00000000-0000-0000-0000-000000000007"),
]

# Build lookup maps so we can resolve filename<->team_id either direction.
filename_to_team_id = {f: tid for f, tid in files_to_process}
team_id_to_filename = {tid: f for f, tid in files_to_process}

# Resolve which JSON file(s) inside `directory_path` to upload. Prefer the
# explicit team_id passed on the CLI; fall back to whatever *.json files exist
# in the content-pack directory (each pack ships one).
candidate_files = []
expected_name = team_id_to_filename.get(team_id_from_arg)
if expected_name and os.path.isfile(os.path.join(directory_path, expected_name)):
    candidate_files.append((expected_name, team_id_from_arg))
elif os.path.isdir(directory_path):
    for entry in sorted(os.listdir(directory_path)):
        if entry.lower().endswith(".json"):
            tid = filename_to_team_id.get(entry, team_id_from_arg)
            candidate_files.append((entry, tid))

if not candidate_files:
    print(f"No team configuration JSON files found in {directory_path}")
    sys.exit(1)

upload_endpoint = backend_url.rstrip('/') + '/api/v4/upload_team_config'

# Process each JSON file in the directory
uploaded_count = 0
for filename, team_id in candidate_files:
    file_path = os.path.join(directory_path, filename)
    print(f"Uploading file:  {filename}")
    team_exists = check_team_exists(backend_url, team_id, user_principal_id)
    if team_exists:
        # Delete existing team to allow re-upload with updated config
        print(f"Team (ID: {team_id}) already exists. Deleting to re-upload with latest config...")
        delete_endpoint = backend_url.rstrip('/') + f'/api/v4/team_configs/{team_id}'
        headers = {
            'x-ms-client-principal-id': user_principal_id
        }
        try:
            delete_response = request_with_retry("DELETE", delete_endpoint, headers=headers)
            if delete_response.status_code == 200:
                print(f"Successfully deleted existing team (ID: {team_id}).")
            else:
                print(f"Warning: Could not delete existing team (ID: {team_id}). Status: {delete_response.status_code}. Will attempt upload anyway.")
        except Exception as e:
            print(f"Warning: Exception deleting team (ID: {team_id}): {str(e)}. Will attempt upload anyway.")

    try:
        with open(file_path, 'rb') as file_data:
            files = {
                'file': (filename, file_data, 'application/json')
            }
            headers = {
                'x-ms-client-principal-id': user_principal_id
            }
            params = {
                'team_id': team_id
            }
            response = request_with_retry(
                "POST",
                upload_endpoint,
                files=files,
                headers=headers,
                params=params,
            )
            if response.status_code == 200:
                try:
                    resp_json = response.json()
                    if resp_json.get("status") == "success":
                        print(f"Successfully uploaded team configuration: {resp_json.get('name')} (team_id: {resp_json.get('team_id')})")
                        uploaded_count += 1
                    else:
                        print(f"Upload failed for {filename}. Response: {resp_json}")
                        sys.exit(1)
                except Exception as e:
                    print(f"Error parsing response for {filename}: {str(e)}")
                    sys.exit(1)
            else:
                print(f"Failed to upload {filename}. Status code: {response.status_code}, Response: {response.text}")
                sys.exit(1)
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        sys.exit(1)

print(f"Completed uploading team configurations")