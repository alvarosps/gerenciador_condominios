"""
Document storage abstraction for file management.

Phase 4 Infrastructure: Strategy pattern for document storage.

Provides multiple implementations:
- FileSystemDocumentStorage: Local filesystem storage (current)
- S3DocumentStorage: AWS S3 storage (future-ready)

Usage:
    from core.infrastructure import IDocumentStorage, FileSystemDocumentStorage

    storage: IDocumentStorage = FileSystemDocumentStorage(base_path="contracts")
    file_path = storage.save("document.pdf", pdf_bytes)
    pdf_bytes = storage.retrieve("document.pdf")
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

# Try to import boto3 for S3 support (optional dependency)
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)


class IDocumentStorage(ABC):
    """
    Abstract interface for document storage.

    Implementations can store documents in:
    - Local filesystem
    - Cloud storage (S3, Azure Blob, GCS)
    - Database (for small documents)
    """

    @abstractmethod
    def save(self, file_path: str, content: bytes, metadata: Optional[dict] = None) -> str:
        """
        Save a document to storage.

        Args:
            file_path: Relative path/key for the document
            content: Binary content of the document
            metadata: Optional metadata (e.g., content-type, tags)

        Returns:
            str: Full path or URL to the stored document

        Raises:
            StorageError: If save operation fails
        """
        pass

    @abstractmethod
    def retrieve(self, file_path: str) -> bytes:
        """
        Retrieve a document from storage.

        Args:
            file_path: Relative path/key of the document

        Returns:
            bytes: Binary content of the document

        Raises:
            StorageError: If retrieve operation fails
            FileNotFoundError: If document doesn't exist
        """
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Delete a document from storage.

        Args:
            file_path: Relative path/key of the document

        Returns:
            bool: True if deleted successfully, False if not found

        Raises:
            StorageError: If delete operation fails
        """
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        Check if a document exists in storage.

        Args:
            file_path: Relative path/key of the document

        Returns:
            bool: True if document exists, False otherwise
        """
        pass

    @abstractmethod
    def get_url(self, file_path: str, expiry: Optional[int] = None) -> str:
        """
        Get a URL to access the document.

        Args:
            file_path: Relative path/key of the document
            expiry: URL expiry time in seconds (for cloud storage)

        Returns:
            str: URL to access the document

        Raises:
            StorageError: If URL generation fails
        """
        pass


class FileSystemDocumentStorage(IDocumentStorage):
    """
    Document storage using local filesystem.

    Pros:
    - Simple and fast
    - No external dependencies
    - Good for development

    Cons:
    - Not scalable across multiple servers
    - No automatic backups
    - Limited durability
    """

    def __init__(self, base_path: str | Path = "contracts"):
        """
        Initialize filesystem storage.

        Args:
            base_path: Base directory for document storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileSystemDocumentStorage initialized at: {self.base_path}")

    def save(self, file_path: str, content: bytes, metadata: Optional[dict] = None) -> str:
        """
        Save document to local filesystem.

        Args:
            file_path: Relative file path (e.g., "building_836/contract_1.pdf")
            content: Binary content
            metadata: Ignored for filesystem storage

        Returns:
            str: Absolute path to saved file

        Raises:
            StorageError: If save fails
        """
        try:
            full_path = self.base_path / file_path

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            full_path.write_bytes(content)

            logger.info(f"Document saved: {full_path}")
            return str(full_path.absolute())

        except Exception as e:
            logger.error(f"Failed to save document {file_path}: {e}")
            raise StorageError(f"Failed to save document: {e}") from e

    def retrieve(self, file_path: str) -> bytes:
        """
        Retrieve document from local filesystem.

        Args:
            file_path: Relative file path

        Returns:
            bytes: Document content

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If read fails
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")

            content = full_path.read_bytes()
            logger.debug(f"Document retrieved: {full_path}")
            return content

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve document {file_path}: {e}")
            raise StorageError(f"Failed to retrieve document: {e}") from e

    def delete(self, file_path: str) -> bool:
        """
        Delete document from local filesystem.

        Args:
            file_path: Relative file path

        Returns:
            bool: True if deleted, False if not found

        Raises:
            StorageError: If delete fails
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return False

            full_path.unlink()
            logger.info(f"Document deleted: {full_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {file_path}: {e}")
            raise StorageError(f"Failed to delete document: {e}") from e

    def exists(self, file_path: str) -> bool:
        """
        Check if document exists in local filesystem.

        Args:
            file_path: Relative file path

        Returns:
            bool: True if exists
        """
        full_path = self.base_path / file_path
        return full_path.exists()

    def get_url(self, file_path: str, expiry: Optional[int] = None) -> str:
        """
        Get file:// URL for local file.

        Args:
            file_path: Relative file path
            expiry: Ignored for filesystem storage

        Returns:
            str: file:// URL

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.base_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        return full_path.as_uri()


class S3DocumentStorage(IDocumentStorage):
    """
    Document storage using AWS S3 (future implementation).

    Pros:
    - Scalable and durable
    - Automatic backups
    - Global accessibility
    - CDN integration

    Cons:
    - Requires AWS account and configuration
    - Additional costs
    - Network dependency

    Note: Requires boto3 package (not installed by default).
    Install with: pip install boto3
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 storage.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            aws_access_key_id: AWS access key (optional, uses IAM role if not provided)
            aws_secret_access_key: AWS secret key (optional)
        """
        if not HAS_BOTO3:
            raise StorageError("boto3 not installed. Install with: pip install boto3")

        self.bucket_name = bucket_name
        self.region = region

        session_kwargs = {}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs = {
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
            }

        self.s3_client = boto3.client("s3", region_name=region, **session_kwargs)
        logger.info(f"S3DocumentStorage initialized for bucket: {bucket_name}")

    def save(self, file_path: str, content: bytes, metadata: Optional[dict] = None) -> str:
        """
        Save document to S3.

        Args:
            file_path: S3 object key
            content: Binary content
            metadata: S3 metadata (optional)

        Returns:
            str: S3 URL to the object

        Raises:
            StorageError: If upload fails
        """
        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=content,
                **extra_args,
            )

            logger.info(f"Document uploaded to S3: s3://{self.bucket_name}/{file_path}")
            return f"s3://{self.bucket_name}/{file_path}"

        except Exception as e:
            logger.error(f"Failed to upload to S3 {file_path}: {e}")
            raise StorageError(f"Failed to save document to S3: {e}") from e

    def retrieve(self, file_path: str) -> bytes:
        """
        Retrieve document from S3.

        Args:
            file_path: S3 object key

        Returns:
            bytes: Document content

        Raises:
            FileNotFoundError: If object doesn't exist
            StorageError: If download fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            content = response["Body"].read()
            logger.debug(f"Document retrieved from S3: {file_path}")
            return content

        except Exception as e:
            # Check if it's a NoSuchKey error
            error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise FileNotFoundError(f"Document not found in S3: {file_path}")
            logger.error(f"Failed to retrieve from S3 {file_path}: {e}")
            raise StorageError(f"Failed to retrieve document from S3: {e}") from e

    def delete(self, file_path: str) -> bool:
        """
        Delete document from S3.

        Args:
            file_path: S3 object key

        Returns:
            bool: True if deleted, False if not found or error

        Raises:
            StorageError: If delete fails
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            logger.info(f"Document deleted from S3: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete from S3 {file_path}: {e}")
            return False

    def exists(self, file_path: str) -> bool:
        """
        Check if document exists in S3.

        Args:
            file_path: S3 object key

        Returns:
            bool: True if exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception as e:
            # Check if it's a 404/NoSuchKey error
            error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                return False
            return False

    def get_url(self, file_path: str, expiry: Optional[int] = None) -> str:
        """
        Get URL to access S3 object.

        Args:
            file_path: S3 object key
            expiry: URL expiry time in seconds (None for public URL)

        Returns:
            str: URL to access the object

        Raises:
            StorageError: If URL generation fails
        """
        try:
            # If expiry is None, return public URL
            if expiry is None:
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_path}"

            # Generate presigned URL with expiry
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expiry,
            )
            return url

        except Exception as e:
            logger.error(f"Failed to generate S3 URL for {file_path}: {e}")
            raise StorageError(f"Failed to generate presigned URL: {e}") from e


class StorageError(Exception):
    """Exception raised when storage operations fail."""

    pass
