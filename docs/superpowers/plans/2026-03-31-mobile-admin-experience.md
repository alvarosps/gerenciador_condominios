# Mobile Admin Experience — Implementation Plan (Plan 4 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all 5 admin tab screens — Dashboard (occupancy, late payments, lease metrics, adjustment alerts), Properties (buildings, apartments, tenants, create lease), Financial (dashboard, daily control, monthly purchases), Actions (mark paid, proofs, rent adjustment), Notifications.

**Architecture:** Expo Router file-based routing under `app/(admin)/`. All screens consume existing backend endpoints via TanStack Query hooks. No new backend endpoints needed — admin mobile reuses the existing API.

**Tech Stack:** Expo Router, React Native Paper, TanStack Query, Zod, Axios

**Spec:** `docs/superpowers/specs/2026-03-25-mobile-app-design.md` — Seção Admin Tab Bar

**Depends on:** Plan 1 (Backend API), Plan 2 (Mobile Setup + Auth)

---

## File Structure

```
mobile/
├── app/(admin)/
│   ├── _layout.tsx              # UPDATE — 5 tabs
│   ├── index.tsx                # UPDATE — full dashboard
│   ├── properties/
│   │   ├── _layout.tsx          # Stack navigator
│   │   ├── index.tsx            # Buildings list
│   │   ├── [id].tsx             # Building detail → apartments → tenants
│   │   └── new-lease.tsx        # Create new lease form
│   ├── financial/
│   │   ├── _layout.tsx          # Stack navigator
│   │   ├── index.tsx            # Financial dashboard
│   │   ├── daily.tsx            # Daily control
│   │   └── purchases.tsx        # Monthly purchases
│   ├── actions/
│   │   ├── _layout.tsx          # Stack navigator
│   │   ├── index.tsx            # Actions menu
│   │   ├── mark-paid.tsx        # Mark rent as paid
│   │   ├── proofs.tsx           # Approve/reject proofs
│   │   └── rent-adjustment.tsx  # Apply rent adjustment
│   └── notifications.tsx        # Admin notifications
├── lib/api/hooks/
│   ├── use-admin-dashboard.ts   # Dashboard hooks
│   ├── use-admin-properties.ts  # Buildings, apartments, leases hooks
│   ├── use-admin-financial.ts   # Financial dashboard, daily control, purchases
│   ├── use-admin-actions.ts     # Mark paid, proofs, rent adjustment
│   └── use-admin-notifications.ts # Admin notifications
└── lib/schemas/
    └── admin.ts                 # Zod schemas for admin API responses
```

---

## Task 1: Admin API Hooks + Schemas

Create all hook and schema files for the admin experience. These consume existing backend endpoints.

### Schemas (mobile/lib/schemas/admin.ts)
Types needed:
- FinancialSummary, LatePaymentSummary, LeaseMetrics, BuildingStatistics
- Building, Apartment, Lease (simplified for list views)
- FinancialOverview, DebtByPerson, DebtByType, CategoryBreakdown
- DailyBreakdown, DailySummary
- MonthlyPurchases (by_type, by_category)
- PaymentProof (for admin review)
- RentAdjustmentAlert

### Hooks
**use-admin-dashboard.ts:**
- useFinancialSummary() — GET /dashboard/financial_summary/
- useLatePayments() — GET /dashboard/late_payment_summary/
- useLeaseMetrics() — GET /dashboard/lease_metrics/
- useBuildingStatistics() — GET /dashboard/building_statistics/
- useRentAdjustmentAlerts() — GET /dashboard/rent_adjustment_alerts/

**use-admin-properties.ts:**
- useBuildings() — GET /buildings/
- useApartments(buildingId?) — GET /apartments/?building_id=X
- useLeases(filters?) — GET /leases/
- useCreateLease() — POST /leases/ (mutation)
- useTenantSearch(query) — GET /tenants/?search=X
- useGenerateContract(leaseId) — POST /leases/{id}/generate_contract/ (mutation)

**use-admin-financial.ts:**
- useFinancialOverview() — GET /financial-dashboard/overview/
- useDebtByPerson() — GET /financial-dashboard/debt_by_person/
- useDebtByType() — GET /financial-dashboard/debt_by_type/
- useUpcomingInstallments(days?) — GET /financial-dashboard/upcoming_installments/
- useOverdueInstallments() — GET /financial-dashboard/overdue_installments/
- useCategoryBreakdown(year, month) — GET /financial-dashboard/category_breakdown/
- useDailyBreakdown(year, month) — GET /daily-control/breakdown/
- useDailySummary(year, month) — GET /daily-control/summary/
- useMarkDailyPaid() — POST /daily-control/mark_paid/ (mutation)
- useMonthlyPurchases(year, month) — GET /financial-dashboard/monthly_purchases/

**use-admin-actions.ts:**
- useMarkRentPaid() — POST /dashboard/mark_rent_paid/ (mutation)
- useCalculateLateFee(leaseId) — GET /leases/{id}/calculate_late_fee/
- useAdminProofs(status?) — GET /admin/proofs/?status=X
- useReviewProof() — POST /admin/proofs/{id}/review/ (mutation)
- useApplyRentAdjustment(leaseId) — POST /leases/{id}/adjust_rent/ (mutation)

**use-admin-notifications.ts:**
- Same pattern as tenant notifications but for admin user

Commit: `feat(mobile): add admin API hooks and Zod schemas`

---

## Task 2: Admin Tab Layout (5 tabs) + Stack Navigators

Update `mobile/app/(admin)/_layout.tsx` with 5 tabs:
- Dashboard (dashboard icon)
- Imóveis (building icon) — headerShown: false
- Financeiro (money icon) — headerShown: false
- Ações (bolt icon) — headerShown: false
- Alertas (bell icon)

Create stack navigators for properties, financial, actions.

Commit: `feat(mobile): update admin tabs and add stack navigators`

---

## Task 3: Admin Dashboard Screen

Full dashboard with cards:
- Occupancy summary (total apartments, rented, vacant, occupancy %)
- Late payments alert (count, total amount)
- Lease metrics (active, expired, expiring soon)
- Rent adjustment alerts (eligible leases count)
- Pending proof approvals count

Commit: `feat(mobile): add admin dashboard with occupancy, late payments, and metrics`

---

## Task 4: Properties Screens (Buildings, Apartments, Create Lease)

3 screens:
- **Buildings list**: FlatList of buildings with apartment count
- **Building detail [id]**: apartments list with rental value, is_rented badge, tenant name
- **New lease form**: apartment select, tenant search, start date, months, rental value (auto-fill), submit

Commit: `feat(mobile): add properties screens — buildings, apartments, create lease`

---

## Task 5: Financial Screens (Dashboard, Daily Control, Purchases)

3 screens:
- **Financial dashboard**: overview cards (income, expenses, balance), debt by person/type, upcoming/overdue installments
- **Daily control**: month navigator, summary cards, timeline list with mark-paid action
- **Monthly purchases**: month navigator, summary cards by type, accordion with items

Commit: `feat(mobile): add financial screens — dashboard, daily control, monthly purchases`

---

## Task 6: Actions Screens (Mark Paid, Proofs, Rent Adjustment)

4 screens:
- **Actions menu**: cards linking to each action
- **Mark rent paid**: lease selector, month, amount, submit
- **Proofs**: FlatList of pending proofs, approve/reject buttons with reason input
- **Rent adjustment**: lease selector, suggested IPCA %, date, apply with confirmation

Commit: `feat(mobile): add action screens — mark paid, proofs, rent adjustment`

---

## Task 7: Admin Notifications Screen

Same pattern as tenant notifications but for admin.

Commit: `feat(mobile): add admin notifications screen`
