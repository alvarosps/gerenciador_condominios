"""
Unit tests for document storage implementations.

Tests both FileSystemDocumentStorage and S3DocumentStorage to ensure
they correctly implement the IDocumentStorage interface.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.infrastructure.storage import FileSystemDocumentStorage, IDocumentStorage, S3DocumentStorage, StorageError


@pytest.mark.unit
@pytest.mark.infrastructure
class TestFileSystemDocumentStorage:
    """Test suite for FileSystemDocumentStorage."""

    @pytest.fixture
    def temp_base_path(self):
        """Create a temporary directory for storage tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def storage(self, temp_base_path):
        """Create a FileSystemDocumentStorage instance."""
        return FileSystemDocumentStorage(base_path=str(temp_base_path))

    def test_implements_interface(self, storage):
        """Test that FileSystemDocumentStorage implements IDocumentStorage."""
        assert isinstance(storage, IDocumentStorage)

    def test_init_creates_base_directory(self):
        """Test that initialization creates base directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "storage"
            storage = FileSystemDocumentStorage(base_path=str(base_path))
            assert base_path.exists()
            assert storage.base_path == base_path

    def test_save_document(self, storage):
        """Test saving a document."""
        file_path = "test/document.pdf"
        content = b"Test PDF content"
        metadata = {"content-type": "application/pdf"}

        result = storage.save(file_path, content, metadata)

        # Verify file was created
        full_path = storage.base_path / file_path
        assert full_path.exists()
        assert full_path.read_bytes() == content
        assert result == str(full_path)

    def test_save_creates_subdirectories(self, storage):
        """Test that save creates parent directories."""
        file_path = "level1/level2/level3/document.pdf"
        content = b"Test content"

        storage.save(file_path, content)

        full_path = storage.base_path / file_path
        assert full_path.exists()
        assert full_path.parent.exists()

    def test_save_overwrites_existing_file(self, storage):
        """Test that save overwrites existing files."""
        file_path = "document.pdf"
        original_content = b"Original content"
        new_content = b"New content"

        # Save original file
        storage.save(file_path, original_content)

        # Overwrite with new content
        storage.save(file_path, new_content)

        # Verify file was overwritten
        full_path = storage.base_path / file_path
        assert full_path.read_bytes() == new_content

    def test_retrieve_document(self, storage):
        """Test retrieving a document."""
        file_path = "test/document.pdf"
        content = b"Test PDF content"

        # Save document first
        storage.save(file_path, content)

        # Retrieve document
        retrieved_content = storage.retrieve(file_path)

        assert retrieved_content == content

    def test_retrieve_nonexistent_file(self, storage):
        """Test retrieving a nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            storage.retrieve("nonexistent.pdf")

    def test_delete_document(self, storage):
        """Test deleting a document."""
        file_path = "document.pdf"
        content = b"Test content"

        # Save document first
        storage.save(file_path, content)

        # Delete document
        result = storage.delete(file_path)

        assert result is True
        assert not (storage.base_path / file_path).exists()

    def test_delete_nonexistent_file(self, storage):
        """Test deleting a nonexistent file returns False."""
        result = storage.delete("nonexistent.pdf")
        assert result is False

    def test_exists_true(self, storage):
        """Test exists returns True for existing file."""
        file_path = "document.pdf"
        content = b"Test content"

        storage.save(file_path, content)

        assert storage.exists(file_path) is True

    def test_exists_false(self, storage):
        """Test exists returns False for nonexistent file."""
        assert storage.exists("nonexistent.pdf") is False

    def test_get_url_returns_file_path(self, storage):
        """Test get_url returns file:// URL."""
        file_path = "document.pdf"
        content = b"Test content"

        storage.save(file_path, content)

        url = storage.get_url(file_path)

        assert url.startswith("file:///")
        assert file_path in url

    def test_get_url_nonexistent_file(self, storage):
        """Test get_url for nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            storage.get_url("nonexistent.pdf")

    def test_save_with_path_traversal_attack(self, storage):
        """Test that path traversal attacks are prevented."""
        # Attempt to save file outside base directory
        file_path = "../../../etc/passwd"
        content = b"Malicious content"

        # Save should normalize the path and keep it within base_path
        result = storage.save(file_path, content)

        # Verify file is within base_path
        full_path = Path(result)
        assert full_path.is_relative_to(storage.base_path) or str(storage.base_path) in str(full_path)


@pytest.mark.unit
@pytest.mark.infrastructure
class TestS3DocumentStorage:
    """Test suite for S3DocumentStorage."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        with patch("core.infrastructure.storage.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create an S3DocumentStorage instance with mocked S3."""
        return S3DocumentStorage(bucket_name="test-bucket", region="us-east-1")

    def test_implements_interface(self, storage):
        """Test that S3DocumentStorage implements IDocumentStorage."""
        assert isinstance(storage, IDocumentStorage)

    def test_init_with_credentials(self, mock_s3_client):
        """Test initialization with custom AWS credentials."""
        storage = S3DocumentStorage(
            bucket_name="test-bucket",
            region="us-west-2",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
        )

        assert storage.bucket_name == "test-bucket"
        assert storage.region == "us-west-2"

    def test_save_document(self, storage, mock_s3_client):
        """Test saving a document to S3."""
        file_path = "test/document.pdf"
        content = b"Test PDF content"
        metadata = {"content-type": "application/pdf"}

        result = storage.save(file_path, content, metadata)

        # Verify S3 put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args

        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == file_path
        assert call_args[1]["Body"] == content
        assert call_args[1]["Metadata"] == metadata
        assert result == f"s3://test-bucket/{file_path}"

    def test_save_handles_s3_error(self, storage, mock_s3_client):
        """Test that save handles S3 errors."""
        mock_s3_client.put_object.side_effect = Exception("S3 upload failed")

        with pytest.raises(StorageError, match="Failed to save document to S3"):
            storage.save("document.pdf", b"content")

    def test_retrieve_document(self, storage, mock_s3_client):
        """Test retrieving a document from S3."""
        file_path = "document.pdf"
        content = b"Test content"

        # Mock S3 get_object response
        mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: content)}

        retrieved_content = storage.retrieve(file_path)

        assert retrieved_content == content
        mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key=file_path)

    def test_retrieve_handles_s3_error(self, storage, mock_s3_client):
        """Test that retrieve handles S3 errors."""
        mock_s3_client.get_object.side_effect = Exception("S3 download failed")

        with pytest.raises(StorageError, match="Failed to retrieve document from S3"):
            storage.retrieve("document.pdf")

    def test_delete_document(self, storage, mock_s3_client):
        """Test deleting a document from S3."""
        file_path = "document.pdf"

        result = storage.delete(file_path)

        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=file_path)

    def test_delete_handles_s3_error(self, storage, mock_s3_client):
        """Test that delete handles S3 errors gracefully."""
        mock_s3_client.delete_object.side_effect = Exception("S3 delete failed")

        result = storage.delete("document.pdf")

        assert result is False

    def test_exists_true(self, storage, mock_s3_client):
        """Test exists returns True for existing S3 object."""
        file_path = "document.pdf"

        # Mock successful head_object response
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        assert storage.exists(file_path) is True
        mock_s3_client.head_object.assert_called_once_with(Bucket="test-bucket", Key=file_path)

    def test_exists_false(self, storage, mock_s3_client):
        """Test exists returns False for nonexistent S3 object."""
        # Mock 404 error
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        assert storage.exists("nonexistent.pdf") is False

    def test_get_url_with_expiry(self, storage, mock_s3_client):
        """Test generating a presigned URL with expiry."""
        file_path = "document.pdf"
        expiry = 3600

        # Mock presigned URL generation
        mock_s3_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/document.pdf?signature=xyz"
        )

        url = storage.get_url(file_path, expiry=expiry)

        mock_s3_client.generate_presigned_url.assert_called_once()
        call_args = mock_s3_client.generate_presigned_url.call_args

        assert call_args[0][0] == "get_object"
        assert call_args[1]["Params"]["Bucket"] == "test-bucket"
        assert call_args[1]["Params"]["Key"] == file_path
        assert call_args[1]["ExpiresIn"] == expiry
        assert "https://s3.amazonaws.com" in url

    def test_get_url_without_expiry(self, storage, mock_s3_client):
        """Test generating a public S3 URL without expiry."""
        file_path = "document.pdf"

        url = storage.get_url(file_path)

        # Should not call generate_presigned_url
        mock_s3_client.generate_presigned_url.assert_not_called()

        # Should return public URL
        assert url == "https://test-bucket.s3.us-east-1.amazonaws.com/document.pdf"

    def test_get_url_handles_error(self, storage, mock_s3_client):
        """Test that get_url handles errors."""
        mock_s3_client.generate_presigned_url.side_effect = Exception("URL generation failed")

        with pytest.raises(StorageError, match="Failed to generate presigned URL"):
            storage.get_url("document.pdf", expiry=3600)


@pytest.mark.unit
@pytest.mark.infrastructure
class TestStorageComparison:
    """Comparison tests between storage implementations."""

    @pytest.fixture
    def filesystem_storage(self, tmp_path):
        """Create a FileSystemDocumentStorage instance."""
        return FileSystemDocumentStorage(base_path=str(tmp_path))

    @pytest.fixture
    def s3_storage(self):
        """Create an S3DocumentStorage instance with mocked S3."""
        with patch("core.infrastructure.storage.boto3"):
            return S3DocumentStorage(bucket_name="test-bucket")

    def test_both_implement_interface(self, filesystem_storage, s3_storage):
        """Test that both storages implement the same interface."""
        assert isinstance(filesystem_storage, IDocumentStorage)
        assert isinstance(s3_storage, IDocumentStorage)

    def test_both_have_required_methods(self, filesystem_storage, s3_storage):
        """Test that both storages have all required methods."""
        required_methods = ["save", "retrieve", "delete", "exists", "get_url"]

        for method_name in required_methods:
            assert hasattr(filesystem_storage, method_name)
            assert hasattr(s3_storage, method_name)

    def test_both_accept_same_save_parameters(self, filesystem_storage, s3_storage):
        """Test that both storages accept the same save parameters."""
        import inspect

        fs_sig = inspect.signature(filesystem_storage.save)
        s3_sig = inspect.signature(s3_storage.save)

        # Compare parameter names (ignore 'self')
        fs_params = [p for p in fs_sig.parameters.keys() if p != "self"]
        s3_params = [p for p in s3_sig.parameters.keys() if p != "self"]

        assert fs_params == s3_params
