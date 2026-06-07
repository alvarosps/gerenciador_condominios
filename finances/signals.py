"""Finances app signal handlers.

Cache-invalidation receivers (the ``finance-*`` prefixes) and the cross-app
receivers (Apartment / Lease / RentAdjustment / MonthSnapshot) are introduced in
Phase 4 (Session 41), alongside the cache layer that owns the prefix constants.

This module exists so ``FinancesConfig.ready()`` has something to import without a
``try/except ImportError`` guard; it deliberately registers no receivers yet.
"""
