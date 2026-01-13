/**
 * Tests for useDashboard hooks
 */

import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  useDashboardFinancialSummary,
  useDashboardLeaseMetrics,
  useDashboardBuildingStatistics,
  useDashboardLatePayments,
  useDashboardTenantStatistics,
} from '../use-dashboard';
import { createWrapper } from '@/tests/test-utils';

describe('useDashboard hooks', () => {
  describe('useDashboardFinancialSummary', () => {
    it('should fetch financial summary', async () => {
      const { result } = renderHook(() => useDashboardFinancialSummary(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should have financial data
      expect(result.current.data).toHaveProperty('total_revenue');
      expect(result.current.data).toHaveProperty('avg_rental_value');
      expect(result.current.data).toHaveProperty('total_cleaning_fees');
      expect(result.current.data).toHaveProperty('total_late_fees');
      expect(result.current.data).toHaveProperty('occupancy_rate');
    });

    it('should return numeric values for financial metrics', async () => {
      const { result } = renderHook(() => useDashboardFinancialSummary(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(typeof result.current.data?.total_revenue).toBe('number');
      expect(typeof result.current.data?.occupancy_rate).toBe('number');
    });
  });

  describe('useDashboardLeaseMetrics', () => {
    it('should fetch lease metrics', async () => {
      const { result } = renderHook(() => useDashboardLeaseMetrics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should have lease metrics
      expect(result.current.data).toHaveProperty('total_leases');
      expect(result.current.data).toHaveProperty('active_leases');
      expect(result.current.data).toHaveProperty('expired_leases');
      expect(result.current.data).toHaveProperty('expiring_soon');
      expect(result.current.data).toHaveProperty('avg_validity_months');
    });

    it('should return counts as numbers', async () => {
      const { result } = renderHook(() => useDashboardLeaseMetrics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(typeof result.current.data?.total_leases).toBe('number');
      expect(typeof result.current.data?.active_leases).toBe('number');
      expect(result.current.data?.avg_validity_months).toBe(12);
    });
  });

  describe('useDashboardBuildingStatistics', () => {
    it('should fetch building statistics as array', async () => {
      const { result } = renderHook(() => useDashboardBuildingStatistics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should be an array
      expect(Array.isArray(result.current.data)).toBe(true);
    });

    it('should have required fields for each building', async () => {
      const { result } = renderHook(() => useDashboardBuildingStatistics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      if (result.current.data && result.current.data.length > 0) {
        const building = result.current.data[0];
        expect(building).toHaveProperty('building_id');
        expect(building).toHaveProperty('building_name');
        expect(building).toHaveProperty('total_apartments');
        expect(building).toHaveProperty('rented_apartments');
        expect(building).toHaveProperty('occupancy_rate');
        expect(building).toHaveProperty('total_revenue');
      }
    });
  });

  describe('useDashboardLatePayments', () => {
    it('should fetch late payments as array', async () => {
      const { result } = renderHook(() => useDashboardLatePayments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should be an array
      expect(Array.isArray(result.current.data)).toBe(true);
    });

    it('should have required fields for late payments', async () => {
      const { result } = renderHook(() => useDashboardLatePayments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      if (result.current.data && result.current.data.length > 0) {
        const payment = result.current.data[0];
        expect(payment).toHaveProperty('lease_id');
        expect(payment).toHaveProperty('tenant_name');
        expect(payment).toHaveProperty('days_late');
        expect(payment).toHaveProperty('late_fee');
      }
    });
  });

  describe('useDashboardTenantStatistics', () => {
    it('should fetch tenant statistics', async () => {
      const { result } = renderHook(() => useDashboardTenantStatistics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should have tenant statistics
      expect(result.current.data).toHaveProperty('total_tenants');
      expect(result.current.data).toHaveProperty('tenants_with_dependents');
      expect(result.current.data).toHaveProperty('avg_dependents');
      expect(result.current.data).toHaveProperty('tenants_with_furniture');
      expect(result.current.data).toHaveProperty('company_tenants');
      expect(result.current.data).toHaveProperty('person_tenants');
    });

    it('should return numeric values for tenant statistics', async () => {
      const { result } = renderHook(() => useDashboardTenantStatistics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(typeof result.current.data?.total_tenants).toBe('number');
      expect(typeof result.current.data?.avg_dependents).toBe('number');
    });
  });
});
