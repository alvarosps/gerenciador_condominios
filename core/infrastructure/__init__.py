"""
Infrastructure layer for Condomínios Manager.

Phase 4 Infrastructure Improvements: Abstractions for external dependencies.

Provides:
- PDF Generation: IPDFGenerator interface with multiple implementations
- Document Storage: IDocumentStorage interface for file management
- Future: Email service, notification service, etc.
"""

from .pdf_generator import (
    IPDFGenerator,
    PDFGenerationError,
    PlaywrightPDFGenerator,
    PyppeteerPDFGenerator,
)
from .storage import FileSystemDocumentStorage, IDocumentStorage, S3DocumentStorage, StorageError

__all__ = [
    "FileSystemDocumentStorage",
    "IDocumentStorage",
    "IPDFGenerator",
    "PDFGenerationError",
    "PlaywrightPDFGenerator",
    "PyppeteerPDFGenerator",
    "S3DocumentStorage",
    "StorageError",
]
