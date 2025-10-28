import sys
import os
import requests

if len(sys.argv) < 2:
    print("Usage: python upload_team_config.py <backend_endpoint> <directory_path> [<user_principal_id>]")
    sys.exit(1)

backend_url = sys.argv[1]
directory_path = sys.argv[2]
user_principal_id = sys.argv[3] if len(sys.argv) > 3 else "00000000-0000-0000-0000-000000000000"

# Convert to absolute path if provided as relative
directory_path = os.path.abspath(directory_path)
print(f"Scanning directory: {directory_path}")

files_to_process = [
    ("hr.json", "00000000-0000-0000-0000-000000000001"),
    ("marketing.json", "00000000-0000-0000-0000-000000000002"),
    ("retail.json", "00000000-0000-0000-0000-000000000003"),
]

upload_endpoint = backend_url.rstrip('/') + '/api/v4/upload_team_config'

# Process each JSON file in the directory
uploaded_count = 0
for filename, team_id in files_to_process:
    file_path = os.path.join(directory_path, filename)
    if os.path.isfile(file_path):
        print(f"Uploading file: {filename}")
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