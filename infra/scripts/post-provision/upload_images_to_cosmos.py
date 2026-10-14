import sys
import os
import base64
from azure.identity import AzureCliCredential
from azure.cosmos import CosmosClient, exceptions

if len(sys.argv) < 5:
    print("Usage: python upload_images_to_cosmos.py <cosmos_endpoint> <database_name> <container_name> <images_directory>")
    sys.exit(1)

cosmos_endpoint = sys.argv[1]
database_name = sys.argv[2]
container_name = sys.argv[3]
images_directory = sys.argv[4]

# Convert to absolute path if relative
images_directory = os.path.abspath(images_directory)
print(f"Scanning images directory: {images_directory}")

if not os.path.isdir(images_directory):
    print(f"Error: Directory not found: {images_directory}")
    sys.exit(1)

credential = AzureCliCredential()

try:
    client = CosmosClient(url=cosmos_endpoint, credential=credential)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    print(f"Connected to CosmosDB database '{database_name}', container '{container_name}'")
except Exception as e:
    print(f"Error connecting to CosmosDB: {e}")
    sys.exit(1)

supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
image_files = [
    f for f in os.listdir(images_directory)
    if os.path.isfile(os.path.join(images_directory, f))
    and f.lower().endswith(supported_extensions)
]

if not image_files:
    print(f"No image files found in {images_directory}")
    sys.exit(1)

print(f"Found {len(image_files)} image(s) to upload")

success_count = 0
fail_count = 0

for filename in image_files:
    file_path = os.path.join(images_directory, filename)
    product_name = os.path.splitext(filename)[0]
    doc_id = product_name.lower().replace(' ', '-')

    ext = os.path.splitext(filename)[1].lower()
    content_type_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    try:
        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        document = {
            'id': doc_id,
            'filename': filename,
            'product_name': product_name,
            'content_type': content_type,
            'image_data': image_base64,
        }

        container.upsert_item(document)
        print(f"Uploaded image: {filename} (id: {doc_id})")
        success_count += 1
    except exceptions.CosmosHttpResponseError as e:
        print(f"CosmosDB error uploading {filename}: {e}")
        fail_count += 1
    except Exception as e:
        print(f"Error uploading {filename}: {e}")
        fail_count += 1

print(f"\nCompleted: {success_count} uploaded, {fail_count} failed")

if fail_count > 0:
    sys.exit(1)
