"""
Tests package for Condomínios Manager

This package contains comprehensive test suites for all components:
- Unit tests: Fast, isolated tests for models, serializers, and utilities
- Integration tests: API endpoint and database interaction tests
- Fixtures: Reusable test data factories and fixtures

Test Organization:
    tests/
    ├── unit/           - Unit tests (models, serializers, utils)
    ├── integration/    - Integration tests (API views, workflows)
    └── fixtures/       - Test fixtures and factories

Test Markers:
    @pytest.mark.unit          - Fast unit tests
    @pytest.mark.integration   - Integration tests
    @pytest.mark.slow          - Slow tests (PDF generation)
    @pytest.mark.pdf           - PDF-specific tests
"""

__version__ = "1.0.0"
