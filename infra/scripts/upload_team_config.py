"""Upload team configuration JSON files to the MACAE backend.

Usage:
    python upload_team_config.py <backend_endpoint> <directory_path> [<user_principal_id>] [<team_id_from_arg>]

Pass team_id='content-packs' to auto-discover and upload every pack under
content_packs/*/agent_teams/*.json.

Content packs may include a top-level "brand" block whose values are
substituted into agent system_messages (and any other string field) wherever
{{brand.X}} placeholders appear. The "brand" block is stripped before upload.
"""

import sys
import os
import re
import io
import uuid
import glob
import requests
import json


# Sentinel team_id that triggers auto-discovery of all content_packs/*/agent_teams/*.json
CONTENT_PACKS_SENTINEL = "content-packs"

# Stable UUID namespace for deriving deterministic team_ids from pack folder names.
_PACK_UUID_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000aaaa")

# Pattern for {{brand.key}} placeholders in agent system_messages.
_BRAND_PLACEHOLDER_RE = re.compile(r"\{\{\s*brand\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def derive_pack_team_id(pack_name: str) -> str:
    """Return a deterministic UUID for a content pack based on its folder name."""
    return str(uuid.uuid5(_PACK_UUID_NAMESPACE, pack_name))


def _format_brand_value(value):
    """Render a brand value as a string suitable for embedding in a system_message."""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else ""
    if value is None:
        return ""
    return str(value)


def render_pack_payload(file_path: str) -> bytes:
    """Load a content pack team config, expand any {{brand.X}} placeholders using the
    pack's top-level "brand" block (if present), strip the brand block, and return
    the rendered JSON as bytes ready to upload.

    If the pack has no "brand" block, the file is returned unchanged.
    """
    with open(file_path, "rb") as f:
        raw = f.read()
    try:
        cfg = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw

    brand = cfg.pop("brand", None)
    if not isinstance(brand, dict) or not brand:
        return raw

    def _sub(match):
        key = match.group(1)
        if key not in brand:
            print(f"Warning: {{{{brand.{key}}}}} placeholder in {os.path.basename(file_path)} has no value in brand block; leaving empty.")
            return ""
        return _format_brand_value(brand[key])

    def _walk(node):
        if isinstance(node, str):
            return _BRAND_PLACEHOLDER_RE.sub(_sub, node)
        if isinstance(node, list):
            return [_walk(item) for item in node]
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        return node

    rendered = _walk(cfg)
    return json.dumps(rendered, ensure_ascii=False, indent=2).encode("utf-8")


def check_team_exists(backend_url, team_id, user_principal_id):
    """Return True if the team already exists in the database."""
    check_endpoint = backend_url.rstrip('/') + f'/api/v4/team_configs/{team_id}'
    headers = {'x-ms-client-principal-id': user_principal_id}
    try:
        response = requests.get(check_endpoint, headers=headers)
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        print(f"Error checking team {team_id}: Status {response.status_code}, Response: {response.text}")
        return False
    except Exception as e:
        print(f"Exception checking team {team_id}: {str(e)}")
        return False


def upload_one(backend_url, upload_endpoint, user_principal_id, file_path, team_id):
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
        payload = render_pack_payload(file_path)
        files = {'file': (filename, io.BytesIO(payload), 'application/json')}
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


def main():
    if len(sys.argv) < 3:
        print("Usage: python upload_team_config.py <backend_endpoint> <directory_path> [<user_principal_id>] [<team_id_from_arg>]")
        print(f"  Pass team_id='{CONTENT_PACKS_SENTINEL}' to auto-discover and upload every pack under content_packs/*/agent_teams/*.json")
        sys.exit(1)

    backend_url = sys.argv[1]
    directory_path = sys.argv[2]
    user_principal_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].strip() != "" else "00000000-0000-0000-0000-000000000000"
    team_id_from_arg = sys.argv[4] if len(sys.argv) > 4 else "00000000-0000-0000-0000-000000000001"

    upload_endpoint = backend_url.rstrip('/') + '/api/v4/upload_team_config'

    # --- Branch 1: auto-discover content packs ---
    if team_id_from_arg == CONTENT_PACKS_SENTINEL:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
        packs_root = os.path.join(repo_root, "content_packs")
        if not os.path.isdir(packs_root):
            print(f"No content_packs/ directory found at {packs_root}. Nothing to upload.")
            return 0

        # Scope the glob to the supplied directory_path: if it's a specific pack
        # subdir (e.g. content_packs/content_gen), only that pack is uploaded.
        # If it's the packs root (or anything else), discover every pack.
        scoped = os.path.abspath(directory_path) if directory_path else packs_root
        if os.path.isdir(scoped) and os.path.dirname(scoped) == packs_root:
            pattern = os.path.join(scoped, "agent_teams", "*.json")
        else:
            pattern = os.path.join(packs_root, "*", "agent_teams", "*.json")
        pack_files = sorted(glob.glob(pattern))
        if not pack_files:
            print(f"No team config JSONs found under {pattern}. Nothing to upload.")
            return 0

        print(f"Discovered {len(pack_files)} content pack team config(s).")
        failed = 0
        for file_path in pack_files:
            pack_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                json_team_id = cfg.get("team_id", "")
                uuid.UUID(json_team_id)
                team_id = json_team_id
            except (ValueError, json.JSONDecodeError, OSError):
                team_id = derive_pack_team_id(pack_name)

            if not upload_one(backend_url, upload_endpoint, user_principal_id, file_path, team_id):
                failed += 1

        if failed:
            print(f"Completed with {failed} failure(s).")
            return 1
        print(f"Completed uploading {len(pack_files)} content pack team configuration(s).")
        return 0

    # --- Branch 2: legacy hardcoded list, for the original 6 teams under data/agent_teams ---
    directory_path = os.path.abspath(directory_path)
    print(f"Scanning directory: {directory_path}")

    files_to_process = [
        ("ad_copy_team.json", "00000000-0000-0000-0000-000000000006"),
    ]

    for filename, team_id in files_to_process:
        if team_id == team_id_from_arg:
            file_path = os.path.join(directory_path, filename)
            if not os.path.isfile(file_path):
                print(f"File not found: {filename}")
                return 1
            if not upload_one(backend_url, upload_endpoint, user_principal_id, file_path, team_id):
                return 1

    print("Completed uploading team configurations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
