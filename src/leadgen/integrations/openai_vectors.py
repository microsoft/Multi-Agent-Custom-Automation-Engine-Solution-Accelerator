"""OpenAI Vector Store management utilities.

This module provides utilities for managing OpenAI Vector Stores, including
creating stores, uploading files, and managing file associations for
RAG-powered voice agents.

Note: Uses client.vector_stores (NOT client.beta.vector_stores) as
the Vector Store API is now generally available.
"""

import asyncio
import io
import logging
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from openai import OpenAI

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 60
MAX_FILES_PER_VECTOR_STORE = 10000
MAX_FILE_SIZE_BYTES = 512 * 1024 * 1024  # 512 MB
MAX_FILE_TOKENS = 5_000_000
SUPPORTED_FILE_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html", ".json"}
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 400


class VectorStoreStatus(str, Enum):
    """Vector store status values."""

    EXPIRED = "expired"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FileStatus(str, Enum):
    """File processing status values."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VectorStoreError(Exception):
    """Base exception for Vector Store errors."""

    pass


class VectorStoreNotFoundError(VectorStoreError):
    """Raised when a vector store is not found."""

    pass


class VectorStoreQuotaError(VectorStoreError):
    """Raised when quota limits are exceeded."""

    pass


class VectorStoreFileError(VectorStoreError):
    """Raised when file operations fail."""

    pass


class VectorStoreAuthError(VectorStoreError):
    """Raised when API authentication fails."""

    pass


@dataclass
class VectorStoreInfo:
    """Represents information about a vector store.

    Attributes:
        id: Vector store ID.
        name: Vector store name.
        status: Processing status.
        file_counts: Dictionary with file count by status.
        usage_bytes: Storage usage in bytes.
        created_at: Creation timestamp.
        expires_at: Expiration timestamp (if set).
        expires_after_days: Days after last activity before expiration.
        success: Whether the operation was successful.
        error: Error message if operation failed.
    """

    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    file_counts: dict[str, int] = field(default_factory=dict)
    usage_bytes: int = 0
    created_at: Optional[int] = None
    expires_at: Optional[int] = None
    expires_after_days: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "file_counts": self.file_counts,
            "usage_bytes": self.usage_bytes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "expires_after_days": self.expires_after_days,
            "success": self.success,
            "error": self.error,
        }

    @property
    def total_files(self) -> int:
        """Get total number of files in the vector store."""
        return sum(self.file_counts.values())

    @property
    def is_ready(self) -> bool:
        """Check if vector store is ready for queries."""
        return self.status == VectorStoreStatus.COMPLETED

    @property
    def is_processing(self) -> bool:
        """Check if vector store is still processing files."""
        return self.status == VectorStoreStatus.IN_PROGRESS


@dataclass
class FileInfo:
    """Represents information about a file in a vector store.

    Attributes:
        id: File ID.
        filename: Original filename.
        bytes: File size in bytes.
        status: Processing status.
        status_details: Additional status information.
        vector_store_id: Associated vector store ID.
        created_at: Creation timestamp.
        success: Whether the operation was successful.
        error: Error message if operation failed.
    """

    id: str
    filename: Optional[str] = None
    bytes: int = 0
    status: Optional[str] = None
    status_details: Optional[str] = None
    vector_store_id: Optional[str] = None
    created_at: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "filename": self.filename,
            "bytes": self.bytes,
            "status": self.status,
            "status_details": self.status_details,
            "vector_store_id": self.vector_store_id,
            "created_at": self.created_at,
            "success": self.success,
            "error": self.error,
        }

    @property
    def is_ready(self) -> bool:
        """Check if file is processed and ready for queries."""
        return self.status == FileStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if file processing failed."""
        return self.status == FileStatus.FAILED


@dataclass
class UploadResult:
    """Represents the result of uploading files to a vector store.

    Attributes:
        vector_store_id: The vector store files were added to.
        uploaded_files: List of successfully uploaded file infos.
        failed_files: List of filenames that failed to upload.
        success: Whether all files were uploaded successfully.
        error: General error message if operation failed.
    """

    vector_store_id: str
    uploaded_files: list[FileInfo] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    @property
    def total_uploaded(self) -> int:
        """Get count of successfully uploaded files."""
        return len(self.uploaded_files)

    @property
    def total_failed(self) -> int:
        """Get count of failed uploads."""
        return len(self.failed_files)


class VectorStoreManager:
    """Manager for OpenAI Vector Store operations.

    Provides methods for creating, managing, and populating vector stores
    for use with file_search in OpenAI assistants and responses.

    Attributes:
        api_key: OpenAI API key.
        timeout_seconds: Request timeout in seconds.

    Example:
        >>> manager = VectorStoreManager()
        >>> store = await manager.create_vector_store("Acme Dental Knowledge Base")
        >>> await manager.add_content(store.id, "# Services\\n\\nWe offer...")
        >>> print(store.id)
        vs_abc123...
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize Vector Store manager.

        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            timeout_seconds: Request timeout in seconds. Defaults to 60.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.timeout_seconds = timeout_seconds
        self._client = OpenAI(api_key=self.api_key, timeout=timeout_seconds)
        logger.info("VectorStoreManager initialized with %ds timeout", timeout_seconds)

    def _parse_vector_store(self, vs: Any) -> VectorStoreInfo:
        """Parse raw API response into VectorStoreInfo.

        Args:
            vs: Vector store object from API response.

        Returns:
            Parsed VectorStoreInfo object.
        """
        file_counts = {}
        if hasattr(vs, "file_counts"):
            fc = vs.file_counts
            file_counts = {
                "in_progress": getattr(fc, "in_progress", 0),
                "completed": getattr(fc, "completed", 0),
                "failed": getattr(fc, "failed", 0),
                "cancelled": getattr(fc, "cancelled", 0),
                "total": getattr(fc, "total", 0),
            }

        expires_after_days = None
        if hasattr(vs, "expires_after") and vs.expires_after:
            expires_after_days = getattr(vs.expires_after, "days", None)

        return VectorStoreInfo(
            id=vs.id,
            name=getattr(vs, "name", None),
            status=getattr(vs, "status", None),
            file_counts=file_counts,
            usage_bytes=getattr(vs, "usage_bytes", 0),
            created_at=getattr(vs, "created_at", None),
            expires_at=getattr(vs, "expires_at", None),
            expires_after_days=expires_after_days,
            success=True,
            error=None,
        )

    def _parse_file(self, f: Any, vector_store_id: Optional[str] = None) -> FileInfo:
        """Parse raw API response into FileInfo.

        Args:
            f: File object from API response.
            vector_store_id: Associated vector store ID.

        Returns:
            Parsed FileInfo object.
        """
        status_details = None
        if hasattr(f, "last_error") and f.last_error:
            status_details = getattr(f.last_error, "message", str(f.last_error))

        return FileInfo(
            id=f.id,
            filename=getattr(f, "filename", None),
            bytes=getattr(f, "bytes", 0),
            status=getattr(f, "status", None),
            status_details=status_details,
            vector_store_id=vector_store_id or getattr(f, "vector_store_id", None),
            created_at=getattr(f, "created_at", None),
            success=True,
            error=None,
        )

    async def create_vector_store(
        self,
        name: str,
        expires_after_days: Optional[int] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> VectorStoreInfo:
        """Create a new vector store.

        Args:
            name: Name for the vector store.
            expires_after_days: Days after last activity before expiration.
            metadata: Additional metadata key-value pairs.

        Returns:
            VectorStoreInfo for the created store.

        Raises:
            VectorStoreAuthError: If authentication fails.
            VectorStoreQuotaError: If quota is exceeded.
            VectorStoreError: If creation fails.
        """
        logger.info("Creating vector store: %s", name)

        kwargs: dict[str, Any] = {"name": name}

        if expires_after_days:
            kwargs["expires_after"] = {
                "anchor": "last_active_at",
                "days": expires_after_days,
            }

        if metadata:
            kwargs["metadata"] = metadata

        loop = asyncio.get_event_loop()

        try:
            vs = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.create(**kwargs),
            )

            result = self._parse_vector_store(vs)
            logger.info("Created vector store: %s (id=%s)", name, result.id)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to create vector store: %s", error_msg)

            if "401" in error_msg or "invalid_api_key" in error_msg.lower():
                raise VectorStoreAuthError(f"Authentication failed: {error_msg}") from e
            elif "429" in error_msg or "quota" in error_msg.lower():
                raise VectorStoreQuotaError(f"Quota exceeded: {error_msg}") from e
            else:
                raise VectorStoreError(f"Failed to create vector store: {error_msg}") from e

    async def get_vector_store(self, vector_store_id: str) -> VectorStoreInfo:
        """Get information about a vector store.

        Args:
            vector_store_id: The ID of the vector store to retrieve.

        Returns:
            VectorStoreInfo with current status and file counts.

        Raises:
            VectorStoreNotFoundError: If vector store doesn't exist.
            VectorStoreError: If retrieval fails.
        """
        logger.info("Getting vector store: %s", vector_store_id)

        loop = asyncio.get_event_loop()

        try:
            vs = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.retrieve(vector_store_id),
            )

            result = self._parse_vector_store(vs)
            logger.info(
                "Retrieved vector store: %s (status=%s, files=%d)",
                result.name,
                result.status,
                result.total_files,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to get vector store: %s", error_msg)

            if "404" in error_msg or "not_found" in error_msg.lower():
                raise VectorStoreNotFoundError(
                    f"Vector store not found: {vector_store_id}"
                ) from e
            else:
                raise VectorStoreError(f"Failed to get vector store: {error_msg}") from e

    async def delete_vector_store(self, vector_store_id: str) -> bool:
        """Delete a vector store.

        Args:
            vector_store_id: The ID of the vector store to delete.

        Returns:
            True if deletion was successful.

        Raises:
            VectorStoreNotFoundError: If vector store doesn't exist.
            VectorStoreError: If deletion fails.
        """
        logger.info("Deleting vector store: %s", vector_store_id)

        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.delete(vector_store_id),
            )

            deleted = getattr(result, "deleted", False)
            if deleted:
                logger.info("Deleted vector store: %s", vector_store_id)
            else:
                logger.warning("Vector store deletion returned false: %s", vector_store_id)

            return deleted

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to delete vector store: %s", error_msg)

            if "404" in error_msg or "not_found" in error_msg.lower():
                raise VectorStoreNotFoundError(
                    f"Vector store not found: {vector_store_id}"
                ) from e
            else:
                raise VectorStoreError(
                    f"Failed to delete vector store: {error_msg}"
                ) from e

    async def upload_file(
        self,
        file_path: Union[str, Path],
        purpose: str = "assistants",
    ) -> FileInfo:
        """Upload a file to OpenAI for use in vector stores.

        Args:
            file_path: Path to the file to upload.
            purpose: File purpose (must be "assistants" for vector stores).

        Returns:
            FileInfo for the uploaded file.

        Raises:
            VectorStoreFileError: If upload fails.
            FileNotFoundError: If file doesn't exist.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            raise VectorStoreFileError(
                f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )

        logger.info("Uploading file: %s", file_path.name)

        loop = asyncio.get_event_loop()

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            file_obj = await loop.run_in_executor(
                None,
                lambda: self._client.files.create(
                    file=(file_path.name, file_content),
                    purpose=purpose,
                ),
            )

            result = FileInfo(
                id=file_obj.id,
                filename=getattr(file_obj, "filename", file_path.name),
                bytes=getattr(file_obj, "bytes", len(file_content)),
                status="uploaded",
                created_at=getattr(file_obj, "created_at", None),
                success=True,
            )

            logger.info("Uploaded file: %s (id=%s)", file_path.name, result.id)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to upload file: %s", error_msg)
            raise VectorStoreFileError(f"Failed to upload file: {error_msg}") from e

    async def add_file_to_vector_store(
        self,
        vector_store_id: str,
        file_id: str,
    ) -> FileInfo:
        """Add an uploaded file to a vector store.

        Args:
            vector_store_id: The vector store to add the file to.
            file_id: The ID of the uploaded file.

        Returns:
            FileInfo with processing status.

        Raises:
            VectorStoreNotFoundError: If vector store doesn't exist.
            VectorStoreFileError: If adding file fails.
        """
        logger.info("Adding file %s to vector store %s", file_id, vector_store_id)

        loop = asyncio.get_event_loop()

        try:
            vs_file = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id,
                ),
            )

            result = self._parse_file(vs_file, vector_store_id)
            logger.info(
                "Added file to vector store: %s (status=%s)",
                file_id,
                result.status,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to add file to vector store: %s", error_msg)

            if "404" in error_msg or "not_found" in error_msg.lower():
                raise VectorStoreNotFoundError(
                    f"Vector store or file not found: {error_msg}"
                ) from e
            else:
                raise VectorStoreFileError(
                    f"Failed to add file to vector store: {error_msg}"
                ) from e

    async def add_content(
        self,
        vector_store_id: str,
        content: str,
        filename: str = "content.md",
    ) -> FileInfo:
        """Add text content directly to a vector store.

        Creates a temporary file, uploads it, and adds it to the vector store.

        Args:
            vector_store_id: The vector store to add content to.
            content: Text content to add (markdown recommended).
            filename: Name for the created file.

        Returns:
            FileInfo for the added content.

        Raises:
            VectorStoreFileError: If adding content fails.
        """
        logger.info(
            "Adding content to vector store %s (filename=%s, size=%d bytes)",
            vector_store_id,
            filename,
            len(content.encode("utf-8")),
        )

        loop = asyncio.get_event_loop()

        try:
            # Upload content as a file
            file_bytes = content.encode("utf-8")

            file_obj = await loop.run_in_executor(
                None,
                lambda: self._client.files.create(
                    file=(filename, file_bytes),
                    purpose="assistants",
                ),
            )

            # Add to vector store
            vs_file = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_obj.id,
                ),
            )

            result = self._parse_file(vs_file, vector_store_id)
            result.filename = filename
            result.bytes = len(file_bytes)

            logger.info(
                "Added content to vector store: %s (file_id=%s)",
                filename,
                result.id,
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to add content to vector store: %s", error_msg)
            raise VectorStoreFileError(
                f"Failed to add content to vector store: {error_msg}"
            ) from e

    async def upload_and_add_files(
        self,
        vector_store_id: str,
        file_paths: list[Union[str, Path]],
        concurrency: int = 3,
    ) -> UploadResult:
        """Upload multiple files and add them to a vector store.

        Args:
            vector_store_id: The vector store to add files to.
            file_paths: List of file paths to upload.
            concurrency: Maximum concurrent uploads. Defaults to 3.

        Returns:
            UploadResult with success/failure details.
        """
        logger.info(
            "Uploading %d files to vector store %s (concurrency=%d)",
            len(file_paths),
            vector_store_id,
            concurrency,
        )

        semaphore = asyncio.Semaphore(concurrency)
        uploaded_files: list[FileInfo] = []
        failed_files: list[str] = []

        async def upload_and_add(path: Union[str, Path]) -> Optional[FileInfo]:
            async with semaphore:
                path = Path(path)
                try:
                    file_info = await self.upload_file(path)
                    vs_file = await self.add_file_to_vector_store(
                        vector_store_id,
                        file_info.id,
                    )
                    return vs_file
                except Exception as e:
                    logger.warning("Failed to upload %s: %s", path.name, e)
                    failed_files.append(str(path))
                    return None

        results = await asyncio.gather(
            *[upload_and_add(path) for path in file_paths],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, FileInfo):
                uploaded_files.append(result)
            elif isinstance(result, Exception):
                logger.warning("Upload task failed: %s", result)

        upload_result = UploadResult(
            vector_store_id=vector_store_id,
            uploaded_files=uploaded_files,
            failed_files=failed_files,
            success=len(failed_files) == 0,
        )

        logger.info(
            "Upload complete: %d succeeded, %d failed",
            upload_result.total_uploaded,
            upload_result.total_failed,
        )

        return upload_result

    async def list_files(
        self,
        vector_store_id: str,
        limit: int = 100,
    ) -> list[FileInfo]:
        """List files in a vector store.

        Args:
            vector_store_id: The vector store to list files from.
            limit: Maximum number of files to return.

        Returns:
            List of FileInfo objects.

        Raises:
            VectorStoreNotFoundError: If vector store doesn't exist.
            VectorStoreError: If listing fails.
        """
        logger.info("Listing files in vector store: %s", vector_store_id)

        loop = asyncio.get_event_loop()

        try:
            files_list = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.files.list(
                    vector_store_id=vector_store_id,
                    limit=limit,
                ),
            )

            files = [self._parse_file(f, vector_store_id) for f in files_list.data]
            logger.info("Listed %d files in vector store", len(files))
            return files

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to list files: %s", error_msg)

            if "404" in error_msg or "not_found" in error_msg.lower():
                raise VectorStoreNotFoundError(
                    f"Vector store not found: {vector_store_id}"
                ) from e
            else:
                raise VectorStoreError(f"Failed to list files: {error_msg}") from e

    async def remove_file(
        self,
        vector_store_id: str,
        file_id: str,
    ) -> bool:
        """Remove a file from a vector store.

        Args:
            vector_store_id: The vector store to remove the file from.
            file_id: The ID of the file to remove.

        Returns:
            True if removal was successful.

        Raises:
            VectorStoreNotFoundError: If vector store or file doesn't exist.
            VectorStoreFileError: If removal fails.
        """
        logger.info("Removing file %s from vector store %s", file_id, vector_store_id)

        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.vector_stores.files.delete(
                    vector_store_id=vector_store_id,
                    file_id=file_id,
                ),
            )

            deleted = getattr(result, "deleted", False)
            if deleted:
                logger.info("Removed file %s from vector store", file_id)
            else:
                logger.warning("File removal returned false: %s", file_id)

            return deleted

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to remove file: %s", error_msg)

            if "404" in error_msg or "not_found" in error_msg.lower():
                raise VectorStoreNotFoundError(
                    f"Vector store or file not found: {error_msg}"
                ) from e
            else:
                raise VectorStoreFileError(f"Failed to remove file: {error_msg}") from e

    async def wait_for_processing(
        self,
        vector_store_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
    ) -> VectorStoreInfo:
        """Wait for all files in a vector store to finish processing.

        Args:
            vector_store_id: The vector store to wait for.
            timeout_seconds: Maximum time to wait. Defaults to 300 (5 min).
            poll_interval: Seconds between status checks. Defaults to 2.

        Returns:
            VectorStoreInfo with final status.

        Raises:
            TimeoutError: If processing doesn't complete within timeout.
            VectorStoreError: If an error occurs during processing.
        """
        logger.info(
            "Waiting for vector store processing: %s (timeout=%ds)",
            vector_store_id,
            timeout_seconds,
        )

        elapsed = 0.0
        while elapsed < timeout_seconds:
            vs_info = await self.get_vector_store(vector_store_id)

            if vs_info.is_ready:
                logger.info(
                    "Vector store ready: %s (files=%d)",
                    vector_store_id,
                    vs_info.total_files,
                )
                return vs_info

            if vs_info.status == VectorStoreStatus.EXPIRED:
                raise VectorStoreError(f"Vector store expired: {vector_store_id}")

            # Check for failed files
            failed_count = vs_info.file_counts.get("failed", 0)
            if failed_count > 0:
                logger.warning(
                    "Vector store has %d failed files: %s",
                    failed_count,
                    vector_store_id,
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"Vector store processing timed out after {timeout_seconds}s: {vector_store_id}"
        )

    async def create_with_content(
        self,
        name: str,
        content: str,
        filename: str = "dossier.md",
        expires_after_days: Optional[int] = None,
        metadata: Optional[dict[str, str]] = None,
        wait_for_ready: bool = True,
    ) -> VectorStoreInfo:
        """Create a vector store and populate it with content in one call.

        Convenience method for creating a vector store with initial content.

        Args:
            name: Name for the vector store.
            content: Text content to add (markdown recommended).
            filename: Name for the content file.
            expires_after_days: Days after last activity before expiration.
            metadata: Additional metadata key-value pairs.
            wait_for_ready: Whether to wait for processing to complete.

        Returns:
            VectorStoreInfo for the created and populated store.
        """
        logger.info("Creating vector store with content: %s", name)

        # Create the vector store
        vs_info = await self.create_vector_store(
            name=name,
            expires_after_days=expires_after_days,
            metadata=metadata,
        )

        # Add the content
        await self.add_content(vs_info.id, content, filename)

        # Optionally wait for processing
        if wait_for_ready:
            vs_info = await self.wait_for_processing(vs_info.id)

        return vs_info

    async def create_with_files(
        self,
        name: str,
        file_paths: list[Union[str, Path]],
        expires_after_days: Optional[int] = None,
        metadata: Optional[dict[str, str]] = None,
        wait_for_ready: bool = True,
        concurrency: int = 3,
    ) -> tuple[VectorStoreInfo, UploadResult]:
        """Create a vector store and populate it with files in one call.

        Convenience method for creating a vector store with initial files.

        Args:
            name: Name for the vector store.
            file_paths: List of file paths to upload.
            expires_after_days: Days after last activity before expiration.
            metadata: Additional metadata key-value pairs.
            wait_for_ready: Whether to wait for processing to complete.
            concurrency: Maximum concurrent uploads.

        Returns:
            Tuple of (VectorStoreInfo, UploadResult).
        """
        logger.info("Creating vector store with %d files: %s", len(file_paths), name)

        # Create the vector store
        vs_info = await self.create_vector_store(
            name=name,
            expires_after_days=expires_after_days,
            metadata=metadata,
        )

        # Upload and add files
        upload_result = await self.upload_and_add_files(
            vs_info.id,
            file_paths,
            concurrency=concurrency,
        )

        # Optionally wait for processing
        if wait_for_ready and upload_result.total_uploaded > 0:
            vs_info = await self.wait_for_processing(vs_info.id)

        return vs_info, upload_result

    def close(self) -> None:
        """Clean up client resources."""
        # OpenAI client doesn't require explicit cleanup,
        # but we provide this method for consistency
        if hasattr(self._client, "close"):
            self._client.close()

    async def __aenter__(self) -> "VectorStoreManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
