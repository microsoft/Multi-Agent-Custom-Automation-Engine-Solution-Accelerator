"""File-system backed dataset storage for user uploads."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.utils.dataset_utils import (
    detect_numeric_columns,
    ensure_allowed_extension,
    extract_numeric_series,
    read_preview,
)


METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    """Restrict identifiers to filesystem-safe characters."""

    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


def _sanitize_filename(value: str) -> str:
    """Normalize filenames while preserving the extension."""

    name_part, dot, extension = value.partition(".")
    sanitized_name = re.sub(r"[^A-Za-z0-9_-]", "_", name_part) or "dataset"
    sanitized_extension = re.sub(r"[^A-Za-z0-9]", "", extension)
    return f"{sanitized_name}{dot}{sanitized_extension}" if dot else sanitized_name


class DatasetService:
    """Persist uploads to disk and expose metadata helpers."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers
    def _user_directory(self, user_id: str) -> Path:
        return self.base_path / _sanitize_identifier(user_id)

    def _dataset_directory(self, user_id: str, dataset_id: str) -> Path:
        return self._user_directory(user_id) / _sanitize_identifier(dataset_id)

    # ------------------------------------------------------------------
    # Metadata helpers
    @staticmethod
    def _metadata_path(dataset_dir: Path) -> Path:
        return dataset_dir / METADATA_FILENAME

    @classmethod
    def _read_metadata(cls, dataset_dir: Path) -> Optional[Dict[str, Any]]:
        metadata_path = cls._metadata_path(dataset_dir)
        if not metadata_path.exists():
            return None
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    @classmethod
    def _write_metadata(cls, dataset_dir: Path, metadata: Dict[str, Any]) -> None:
        metadata_path = cls._metadata_path(dataset_dir)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public operations
    def save_dataset(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Persist an uploaded dataset and return its metadata."""

        dataset_id = str(uuid.uuid4())
        dataset_dir = self._dataset_directory(user_id, dataset_id)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        stored_filename = _sanitize_filename(filename)
        file_path = dataset_dir / stored_filename
        file_path.write_bytes(content)

        ensure_allowed_extension(file_path)

        columns, preview = read_preview(file_path)
        numeric_columns = detect_numeric_columns(file_path)

        metadata = {
            "dataset_id": dataset_id,
            "user_id": user_id,
            "original_filename": filename,
            "stored_filename": stored_filename,
            "content_type": content_type,
            "size_bytes": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "columns": columns,
            "preview": preview,
            "numeric_columns": numeric_columns,
        }

        self._write_metadata(dataset_dir, metadata)
        return metadata

    def list_datasets(self, user_id: str) -> List[Dict[str, Any]]:
        """Return metadata for all datasets uploaded by the user."""

        user_dir = self._user_directory(user_id)
        if not user_dir.exists():
            return []

        datasets: List[Dict[str, Any]] = []
        for item in sorted(user_dir.iterdir()):
            if not item.is_dir():
                continue
            metadata = self._read_metadata(item)
            if metadata:
                datasets.append(metadata)

        return datasets

    def get_dataset(self, user_id: str, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a specific dataset."""

        dataset_dir = self._dataset_directory(user_id, dataset_id)
        if not dataset_dir.exists():
            return None

        metadata = self._read_metadata(dataset_dir)
        if not metadata:
            return None

        return metadata

    def dataset_file_path(self, user_id: str, dataset_id: str) -> Optional[Path]:
        """Return the absolute path to the stored dataset file."""

        dataset_dir = self._dataset_directory(user_id, dataset_id)
        if not dataset_dir.exists():
            return None

        metadata = self._read_metadata(dataset_dir)
        if not metadata:
            return None

        stored = metadata.get("stored_filename")
        if not stored:
            return None

        file_path = dataset_dir / stored
        if file_path.exists():
            return file_path
        return None

    def delete_dataset(self, user_id: str, dataset_id: str) -> bool:
        """Remove a dataset directory and metadata."""
        import logging
        import time
        import platform
        import stat
        import os
        
        logger = logging.getLogger(__name__)
        
        dataset_dir = self._dataset_directory(user_id, dataset_id)
        if not dataset_dir.exists():
            logger.warning(f"Dataset directory does not exist: {dataset_dir}")
            return False

        # Windows-specific helper to handle read-only files and OneDrive locks
        def handle_remove_readonly(func, path, exc_info):
            """Error handler for Windows readonly files."""
            if not os.access(path, os.W_OK):
                # Try to add write permission
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        is_windows = platform.system() == "Windows"
        max_retries = 3 if is_windows else 1
        retry_delay = 0.5  # seconds
        
        for attempt in range(max_retries):
            try:
                if is_windows:
                    # Use onerror handler for Windows readonly/OneDrive files
                    shutil.rmtree(dataset_dir, onerror=handle_remove_readonly)
                else:
                    shutil.rmtree(dataset_dir)
                
                logger.info(f"Successfully removed dataset directory: {dataset_dir}")
                return True
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Permission error deleting {dataset_dir} (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {retry_delay}s... (This may be due to OneDrive sync)"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to delete dataset directory {dataset_dir} after {max_retries} attempts. "
                        f"This may be due to OneDrive sync or file locks. Error: {str(e)}"
                    )
                    raise PermissionError(
                        f"Unable to delete dataset. The file may be locked by OneDrive or another process. "
                        f"Please try again in a moment, or manually delete: {dataset_dir}"
                    )
                    
            except Exception as e:
                logger.error(f"Error removing dataset directory {dataset_dir}: {str(e)}")
                raise

    def locate_dataset_path(self, dataset_id: str) -> Optional[Path]:
        """Search across all users for a dataset directory."""

        for user_dir in self.base_path.iterdir():
            if not user_dir.is_dir():
                continue
            candidate = user_dir / _sanitize_identifier(dataset_id)
            if candidate.exists():
                metadata = self._read_metadata(candidate)
                if metadata:
                    stored = metadata.get("stored_filename")
                    if stored:
                        return candidate / stored
        return None

    def load_numeric_series(
        self, dataset_path: Path, target_column: str
    ) -> Dict[str, Any]:
        """Extract numeric data alongside derived statistics."""

        values, row_count = extract_numeric_series(dataset_path, target_column)
        return {
            "values": values,
            "row_count": row_count,
        }
