import sys
import os
import requests
import json

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
    check_endpoint = backend_url.rstrip('/') + f'/api/v3/team_configs/{team_id}'
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

if len(sys.argv) < 2:
    print("Usage: python upload_team_config.py <backend_endpoint> <directory_path> [<user_principal_id>]")
    sys.exit(1)

backend_url = sys.argv[1]
directory_path = sys.argv[2]
user_principal_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].strip() != "" else "00000000-0000-0000-0000-000000000000"

# Convert to absolute path if provided as relative
directory_path = os.path.abspath(directory_path)
print(f"Scanning directory: {directory_path}")

files_to_process = [
    ("hr.json", "00000000-0000-0000-0000-000000000001"),
    ("marketing.json", "00000000-0000-0000-0000-000000000002"),
    ("retail.json", "00000000-0000-0000-0000-000000000003"),
]

upload_endpoint = backend_url.rstrip('/') + '/api/v3/upload_team_config'

# Process each JSON file in the directory
uploaded_count = 0
for filename, team_id in files_to_process:
    file_path = os.path.join(directory_path, filename)
    if os.path.isfile(file_path):
        print(f"Uploading file: {filename}")
        # Check if team already exists
        team_exists = check_team_exists(backend_url, team_id, user_principal_id)            
        if team_exists:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    team_data = json.load(f)
                    team_name = team_data.get('name', 'Unknown')
                    print(f"Team '{team_name}' (ID: {team_id}) already exists!")
                    continue
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
                continue

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
                response = requests.post(
                    upload_endpoint,
                    files=files,
                    headers=headers,
                    params=params
                )
                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                        if resp_json.get("status") == "success":
                            print(f"Successfully uploaded team configuration: {resp_json.get('name')} (team_id: {resp_json.get('team_id')})")
                            uploaded_count += 1
                        else:
                            print(f"Upload failed for {filename}. Response: {resp_json}")
                    except Exception as e:
                        print(f"Error parsing response for {filename}: {str(e)}")
                else:
                    print(f"Failed to upload {filename}. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    else:
        print(f"File not found: {filename}")

print(f"Completed uploading {uploaded_count} team configurations")