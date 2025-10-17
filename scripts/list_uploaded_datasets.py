#!/usr/bin/env python3
"""
List all uploaded datasets that the MCP server can discover.
This helps verify that datasets are properly uploaded and accessible.
"""

import json
from pathlib import Path

def list_datasets():
    """List all datasets in the uploads directory."""
    repo_root = Path(__file__).parent.parent
    uploads_dir = repo_root / "data" / "uploads"
    
    if not uploads_dir.exists():
        print("❌ No uploads directory found!")
        print(f"   Looking in: {uploads_dir}")
        return
    
    print("="*70)
    print("  📊 UPLOADED DATASETS")
    print("="*70)
    print()
    
    datasets_found = 0
    
    for user_dir in uploads_dir.iterdir():
        if not user_dir.is_dir():
            continue
            
        for dataset_dir in user_dir.iterdir():
            if not dataset_dir.is_dir():
                continue
                
            metadata_file = dataset_dir / "metadata.json"
            if not metadata_file.exists():
                continue
                
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                datasets_found += 1
                
                print(f"Dataset #{datasets_found}")
                print(f"  📁 File: {metadata.get('original_filename')}")
                print(f"  🆔 Dataset ID: {metadata.get('dataset_id')}")
                print(f"  👤 User ID: {metadata.get('user_id')}")
                print(f"  📅 Uploaded: {metadata.get('uploaded_at')}")
                print(f"  📏 Size: {metadata.get('size_bytes')} bytes")
                print(f"  📊 Columns: {', '.join(metadata.get('columns', []))}")
                print(f"  🔢 Numeric Columns: {', '.join(metadata.get('numeric_columns', []))}")
                print()
                
                # Show how to reference this dataset
                print(f"  💡 To use this dataset, tell the agent:")
                print(f"     'Use dataset_id: {metadata.get('dataset_id')}'")
                print()
                print("-"*70)
                print()
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse metadata in {metadata_file}: {e}")
                print()
    
    if datasets_found == 0:
        print("❌ No datasets found!")
        print()
        print("To upload a dataset:")
        print("  1. Go to frontend: http://localhost:3001")
        print("  2. Find 'Forecast Dataset Panel'")
        print("  3. Click 'Upload Dataset'")
        print("  4. Choose a CSV file")
        print()
    else:
        print("="*70)
        print(f"✅ Total datasets found: {datasets_found}")
        print("="*70)
        print()
        print("📝 Quick Reference:")
        print("   When agents ask for the dataset, provide the dataset_id above")
        print("   Example: 'Use dataset_id: 40adbd2f-0a3d-432c-9ff5-73abcbb2f455'")
        print()

if __name__ == "__main__":
    list_datasets()





