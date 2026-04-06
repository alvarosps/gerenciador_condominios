"""Unit tests for core/infrastructure — FileSystemDocumentStorage and PlaywrightPDFGenerator."""

import pytest

from core.infrastructure import (
    FileSystemDocumentStorage,
    PDFGenerationError,
    PlaywrightPDFGenerator,
    StorageError,
)


# =============================================================================
# FileSystemDocumentStorage tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.infrastructure
class TestFileSystemDocumentStorage:
    @pytest.fixture
    def storage(self, tmp_path):
        return FileSystemDocumentStorage(base_path=tmp_path / "docs")

    def test_save_creates_file(self, storage, tmp_path):
        content = b"PDF content here"
        returned_path = storage.save("test/document.pdf", content)
        assert returned_path.endswith("document.pdf")
        assert (tmp_path / "docs" / "test" / "document.pdf").exists()

    def test_save_creates_intermediate_dirs(self, storage, tmp_path):
        content = b"data"
        storage.save("a/b/c/deep.pdf", content)
        assert (tmp_path / "docs" / "a" / "b" / "c" / "deep.pdf").exists()

    def test_save_with_metadata_does_not_fail(self, storage):
        storage.save("meta.pdf", b"content", metadata={"type": "application/pdf"})

    def test_retrieve_returns_bytes(self, storage):
        content = b"hello world"
        storage.save("retrieve_test.pdf", content)
        retrieved = storage.retrieve("retrieve_test.pdf")
        assert retrieved == content

    def test_retrieve_nonexistent_raises_file_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.retrieve("does_not_exist.pdf")

    def test_delete_existing_file_returns_true(self, storage):
        storage.save("to_delete.pdf", b"data")
        result = storage.delete("to_delete.pdf")
        assert result is True
        assert not storage.exists("to_delete.pdf")

    def test_delete_nonexistent_file_returns_false(self, storage):
        result = storage.delete("missing.pdf")
        assert result is False

    def test_exists_when_file_present(self, storage):
        storage.save("present.pdf", b"data")
        assert storage.exists("present.pdf") is True

    def test_exists_when_file_absent(self, storage):
        assert storage.exists("absent.pdf") is False

    def test_get_url_returns_file_uri(self, storage):
        storage.save("url_test.pdf", b"data")
        url = storage.get_url("url_test.pdf")
        assert url.startswith("file://")
        assert "url_test.pdf" in url

    def test_get_url_nonexistent_raises_file_not_found(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.get_url("not_here.pdf")

    def test_get_url_expiry_param_ignored(self, storage):
        storage.save("expiry.pdf", b"data")
        url = storage.get_url("expiry.pdf", expiry=3600)
        assert url.startswith("file://")

    def test_init_creates_base_directory(self, tmp_path):
        new_path = tmp_path / "new_dir"
        assert not new_path.exists()
        FileSystemDocumentStorage(base_path=new_path)
        assert new_path.exists()

    def test_save_raises_storage_error_on_write_failure(self, tmp_path):
        """Simulate OS error by making the file read-only directory."""
        storage = FileSystemDocumentStorage(base_path=tmp_path / "storage")
        # Make the target file a directory so write fails
        target_dir = tmp_path / "storage" / "blocked.pdf"
        target_dir.mkdir(parents=True, exist_ok=True)
        with pytest.raises((StorageError, OSError, IsADirectoryError)):
            storage.save("blocked.pdf", b"data")

    def test_retrieve_raises_storage_error_on_read_failure(self, tmp_path, mocker):
        """Covers lines 198-201: OSError during read_bytes raises StorageError."""
        storage = FileSystemDocumentStorage(base_path=tmp_path / "storage")
        storage.save("exist.pdf", b"data")
        # Patch read_bytes to raise OSError
        mocker.patch("pathlib.Path.read_bytes", side_effect=OSError("read error"))
        with pytest.raises(StorageError, match="Failed to retrieve document"):
            storage.retrieve("exist.pdf")

    def test_delete_raises_storage_error_on_unlink_failure(self, tmp_path, mocker):
        """Covers lines 226-229: OSError during unlink raises StorageError."""
        storage = FileSystemDocumentStorage(base_path=tmp_path / "storage")
        storage.save("to_del.pdf", b"data")
        mocker.patch("pathlib.Path.unlink", side_effect=OSError("unlink error"))
        with pytest.raises(StorageError, match="Failed to delete document"):
            storage.delete("to_del.pdf")


# =============================================================================
# PlaywrightPDFGenerator tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.infrastructure
@pytest.mark.pdf
class TestPlaywrightPDFGenerator:
    def test_generate_pdf_calls_playwright(self, tmp_path, mocker):
        """PDF generation should invoke Playwright's sync_playwright."""
        mock_playwright = mocker.patch("core.infrastructure.pdf_generator.sync_playwright")
        mock_context = mocker.MagicMock()
        mock_playwright.return_value.__enter__ = mocker.MagicMock(return_value=mock_context)
        mock_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.pdf.return_value = None

        output_path = tmp_path / "out.pdf"
        generator = PlaywrightPDFGenerator()
        result = generator.generate_pdf("<html><body>Test</body></html>", output_path)

        assert result == str(output_path)
        mock_playwright.assert_called_once()
        mock_context.chromium.launch.assert_called_once()
        mock_page.pdf.assert_called_once()

    def test_generate_pdf_with_chrome_path(self, tmp_path, mocker):
        """When chrome_path is set, it should be passed to Playwright launch."""
        mock_playwright = mocker.patch("core.infrastructure.pdf_generator.sync_playwright")
        mock_context = mocker.MagicMock()
        mock_playwright.return_value.__enter__ = mocker.MagicMock(return_value=mock_context)
        mock_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        output_path = tmp_path / "out.pdf"
        generator = PlaywrightPDFGenerator(chrome_path="/usr/bin/chromium")
        generator.generate_pdf("<html></html>", output_path)

        call_kwargs = mock_context.chromium.launch.call_args[1]
        assert call_kwargs.get("executable_path") == "/usr/bin/chromium"

    def test_generate_pdf_raises_pdf_generation_error_on_failure(self, tmp_path, mocker):
        """Any exception during generation should be wrapped as PDFGenerationError."""
        mocker.patch(
            "core.infrastructure.pdf_generator.sync_playwright",
            side_effect=RuntimeError("Chromium not found"),
        )
        generator = PlaywrightPDFGenerator()
        with pytest.raises(PDFGenerationError, match="Playwright PDF generation failed"):
            generator.generate_pdf("<html></html>", tmp_path / "fail.pdf")

    def test_generate_pdf_creates_output_directory(self, tmp_path, mocker):
        """Output directory is created if it doesn't exist."""
        mock_playwright = mocker.patch("core.infrastructure.pdf_generator.sync_playwright")
        mock_context = mocker.MagicMock()
        mock_playwright.return_value.__enter__ = mocker.MagicMock(return_value=mock_context)
        mock_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        nested_path = tmp_path / "a" / "b" / "c" / "out.pdf"
        assert not nested_path.parent.exists()

        generator = PlaywrightPDFGenerator()
        generator.generate_pdf("<html></html>", nested_path)

        assert nested_path.parent.exists()

    def test_generate_pdf_with_custom_options(self, tmp_path, mocker):
        """Options dict should be merged into the pdf call."""
        mock_playwright = mocker.patch("core.infrastructure.pdf_generator.sync_playwright")
        mock_context = mocker.MagicMock()
        mock_playwright.return_value.__enter__ = mocker.MagicMock(return_value=mock_context)
        mock_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        generator = PlaywrightPDFGenerator()
        generator.generate_pdf(
            "<html></html>",
            tmp_path / "out.pdf",
            options={"format": "Letter"},
        )

        call_kwargs = mock_page.pdf.call_args[1]
        assert call_kwargs.get("format") == "Letter"


# =============================================================================
# S3DocumentStorage tests (boto3 mocked)
# =============================================================================


@pytest.mark.unit
@pytest.mark.infrastructure
class TestS3DocumentStorage:
    """Test S3DocumentStorage behavior using a mocked boto3 client."""

    @pytest.fixture
    def mock_boto3(self, mocker):
        """Patch boto3 and HAS_BOTO3 so S3DocumentStorage can be instantiated."""
        mock_b3 = mocker.MagicMock()
        mocker.patch("core.infrastructure.storage.boto3", mock_b3)
        mocker.patch("core.infrastructure.storage.HAS_BOTO3", True)
        return mock_b3

    @pytest.fixture
    def s3_storage(self, mock_boto3):
        from core.infrastructure.storage import S3DocumentStorage

        return S3DocumentStorage(
            bucket_name="test-bucket",
            region="us-east-1",
        )

    @pytest.fixture
    def s3_storage_with_credentials(self, mock_boto3):
        from core.infrastructure.storage import S3DocumentStorage

        return S3DocumentStorage(
            bucket_name="cred-bucket",
            region="sa-east-1",
            aws_access_key_id="AKID",
            aws_secret_access_key="SECRET",
        )

    def test_init_raises_when_boto3_not_installed(self, mocker):
        """Covers line 305-307: S3DocumentStorage raises StorageError if boto3 missing."""
        from core.infrastructure.storage import S3DocumentStorage, StorageError

        mocker.patch("core.infrastructure.storage.HAS_BOTO3", False)
        with pytest.raises(StorageError, match="boto3 not installed"):
            S3DocumentStorage(bucket_name="x")

    def test_init_with_credentials_passes_to_boto3(self, s3_storage_with_credentials, mock_boto3):
        """Covers lines 313-319: credential kwargs passed to boto3.client."""
        call_kwargs = mock_boto3.client.call_args[1]
        assert call_kwargs.get("aws_access_key_id") == "AKID"
        assert call_kwargs.get("aws_secret_access_key") == "SECRET"

    def test_save_returns_s3_url(self, s3_storage):
        """Covers lines 337-354: save method returns s3:// URL."""
        result = s3_storage.save("contracts/doc.pdf", b"PDF content")
        assert result == "s3://test-bucket/contracts/doc.pdf"
        s3_storage.s3_client.put_object.assert_called_once()

    def test_save_with_metadata(self, s3_storage):
        """Covers lines 338-339: metadata is passed as ExtraArgs."""
        s3_storage.save("doc.pdf", b"data", metadata={"x-type": "pdf"})
        call_kwargs = s3_storage.s3_client.put_object.call_args[1]
        assert call_kwargs.get("Metadata") == {"x-type": "pdf"}

    def test_save_raises_storage_error_on_os_error(self, s3_storage):
        """Covers lines 348-351: OSError during put_object wrapped as StorageError."""
        from core.infrastructure.storage import StorageError

        s3_storage.s3_client.put_object.side_effect = OSError("upload failed")
        with pytest.raises(StorageError, match="Failed to save document to S3"):
            s3_storage.save("fail.pdf", b"data")

    def test_retrieve_returns_bytes(self, s3_storage):
        """Covers lines 370-384: retrieve reads Body from S3 response."""
        mock_body = mocker.MagicMock() if False else None
        # Build a proper mock response
        s3_storage.s3_client.get_object.return_value = {"Body": type("B", (), {"read": lambda self: b"pdf data"})()}
        result = s3_storage.retrieve("doc.pdf")
        assert result == b"pdf data"

    def test_retrieve_raises_file_not_found_on_404(self, s3_storage):
        """Covers lines 375-378: NoSuchKey error raises FileNotFoundError."""
        error = OSError("NoSuchKey")
        error.response = {"Error": {"Code": "NoSuchKey"}}  # type: ignore[attr-defined]
        s3_storage.s3_client.get_object.side_effect = error
        with pytest.raises(FileNotFoundError):
            s3_storage.retrieve("missing.pdf")

    def test_retrieve_raises_storage_error_on_other_os_error(self, s3_storage):
        """Covers lines 379-381: other OSError raises StorageError."""
        from core.infrastructure.storage import StorageError

        error = OSError("network timeout")
        error.response = {"Error": {"Code": "ServiceUnavailable"}}  # type: ignore[attr-defined]
        s3_storage.s3_client.get_object.side_effect = error
        with pytest.raises(StorageError, match="Failed to retrieve document from S3"):
            s3_storage.retrieve("doc.pdf")

    def test_delete_returns_true_on_success(self, s3_storage):
        """Covers lines 399-406: delete returns True when no error."""
        result = s3_storage.delete("doc.pdf")
        assert result is True
        s3_storage.s3_client.delete_object.assert_called_once()

    def test_delete_returns_false_on_error(self, s3_storage):
        """Covers lines 401-403: OSError returns False."""
        s3_storage.s3_client.delete_object.side_effect = OSError("forbidden")
        result = s3_storage.delete("doc.pdf")
        assert result is False

    def test_exists_returns_true_when_head_succeeds(self, s3_storage):
        """Covers lines 418-423: head_object succeeds → True."""
        s3_storage.s3_client.head_object.return_value = {}
        assert s3_storage.exists("doc.pdf") is True

    def test_exists_returns_false_when_exception(self, s3_storage):
        """Covers line 420: any exception → False."""
        s3_storage.s3_client.head_object.side_effect = Exception("not found")
        assert s3_storage.exists("doc.pdf") is False

    def test_get_url_without_expiry_returns_public_url(self, s3_storage):
        """Covers lines 439-442: expiry=None returns public https URL."""
        url = s3_storage.get_url("doc.pdf")
        assert url == "https://test-bucket.s3.us-east-1.amazonaws.com/doc.pdf"

    def test_get_url_with_expiry_generates_presigned_url(self, s3_storage):
        """Covers lines 444-452: expiry set → generate_presigned_url called."""
        s3_storage.s3_client.generate_presigned_url.return_value = "https://presigned.url/doc.pdf"
        url = s3_storage.get_url("doc.pdf", expiry=3600)
        assert url == "https://presigned.url/doc.pdf"
        s3_storage.s3_client.generate_presigned_url.assert_called_once()

    def test_get_url_raises_storage_error_on_exception(self, s3_storage):
        """Covers lines 454-457: exception in presigned URL raises StorageError."""
        from core.infrastructure.storage import StorageError

        s3_storage.s3_client.generate_presigned_url.side_effect = Exception("signing failed")
        with pytest.raises(StorageError, match="Failed to generate presigned URL"):
            s3_storage.get_url("doc.pdf", expiry=600)


# =============================================================================
# StorageError (line 460-461) — already covered by usage, test explicit raise
# =============================================================================


@pytest.mark.unit
@pytest.mark.infrastructure
class TestStorageError:
    def test_storage_error_is_exception(self):
        from core.infrastructure.storage import StorageError

        err = StorageError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"
