#!/usr/bin/env python3
"""
Repository Organization Script
Moves files to their proper locations for better repository structure
"""

import shutil
from pathlib import Path

def move_file(source, destination):
    """Move a file from source to destination, creating directories as needed."""
    source_path = Path(source)
    dest_path = Path(destination)
    
    if not source_path.exists():
        print(f"⚠️  Source not found: {source}")
        return False
    
    # Create destination directory if it doesn't exist
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        shutil.move(str(source_path), str(dest_path))
        print(f"✅ Moved: {source} → {destination}")
        return True
    except Exception as e:
        print(f"❌ Error moving {source}: {e}")
        return False

def main():
    print("=" * 70)
    print("Repository Organization - Moving Files")
    print("=" * 70)
    print()
    
    # Define all file moves
    moves = [
        # Sprint 1 Documentation
        ("docs/FinanceForecasting_Sprint1_Complete.md", "docs/sprints/sprint1/FinanceForecasting_Sprint1_Complete.md"),
        ("docs/FinanceForecasting_Audit.md", "docs/sprints/sprint1/FinanceForecasting_Audit.md"),
        
        # Sprint 2 Documentation
        ("docs/CustomerOperations_Sprint2_Complete.md", "docs/sprints/sprint2/CustomerOperations_Sprint2_Complete.md"),
        
        # Sprint 3 Documentation
        ("docs/PricingMarketing_Sprint3_Complete.md", "docs/sprints/sprint3/PricingMarketing_Sprint3_Complete.md"),
        
        # Sprint 4 Documentation
        ("docs/Frontend_Sprint4_Implementation_Guide.md", "docs/sprints/sprint4/Frontend_Sprint4_Implementation_Guide.md"),
        ("SPRINT4_IMPLEMENTATION_COMPLETE.md", "docs/sprints/sprint4/SPRINT4_IMPLEMENTATION_COMPLETE.md"),
        ("SPRINT4_TESTING_COMPLETE.md", "docs/sprints/sprint4/SPRINT4_TESTING_COMPLETE.md"),
        ("SPRINT4_TESTING_GUIDE.md", "docs/sprints/sprint4/SPRINT4_TESTING_GUIDE.md"),
        ("SPRINT4_FINAL_REPORT.md", "docs/sprints/sprint4/SPRINT4_FINAL_REPORT.md"),
        
        # Sprint 5 Documentation
        ("SPRINT5_PLAN.md", "docs/sprints/sprint5/SPRINT5_PLAN.md"),
        ("SPRINT5_EXECUTIVE_SUMMARY.md", "docs/sprints/sprint5/SPRINT5_EXECUTIVE_SUMMARY.md"),
        
        # Test Runner Scripts
        ("run_sprint1_tests.py", "scripts/testing/run_sprint1_tests.py"),
        ("run_sprint2_tests.py", "scripts/testing/run_sprint2_tests.py"),
        ("run_sprint3_tests.py", "scripts/testing/run_sprint3_tests.py"),
        
        # Frontend Helper Scripts
        ("run_frontend.ps1", "scripts/frontend/run_frontend.ps1"),
        ("run_frontend.bat", "scripts/frontend/run_frontend.bat"),
    ]
    
    successful = 0
    failed = 0
    skipped = 0
    
    for source, destination in moves:
        result = move_file(source, destination)
        if result:
            successful += 1
        elif not Path(source).exists():
            skipped += 1
        else:
            failed += 1
    
    print()
    print("=" * 70)
    print("Organization Summary")
    print("=" * 70)
    print(f"✅ Successfully moved: {successful}")
    print(f"⚠️  Skipped (not found): {skipped}")
    print(f"❌ Failed: {failed}")
    print()
    
    if failed == 0:
        print("🎉 Repository organization complete!")
    else:
        print("⚠️  Some files could not be moved. Please review errors above.")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())

