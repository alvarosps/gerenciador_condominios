-- =============================================
-- Condomínios Manager Database Migration Scripts
-- Version: 2.0.0
-- =============================================

-- =============================================
-- STEP 1: Create Migration Tracking System
-- =============================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW(),
    applied_by VARCHAR(100),
    execution_time_ms INTEGER,
    rollback_script TEXT,
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back'))
);

-- =============================================
-- STEP 2: Add New Tables (Non-Breaking)
-- =============================================

-- Price History Table
CREATE TABLE IF NOT EXISTS apartment_pricing (
    id BIGSERIAL PRIMARY KEY,
    apartment_id BIGINT NOT NULL REFERENCES apartments(id) ON DELETE CASCADE,
    rental_value DECIMAL(10,2) NOT NULL CHECK (rental_value > 0),
    cleaning_fee DECIMAL(10,2) DEFAULT 0 CHECK (cleaning_fee >= 0),
    condominium_fee DECIMAL(10,2) DEFAULT 0 CHECK (condominium_fee >= 0),
    iptu_value DECIMAL(10,2) DEFAULT 0 CHECK (iptu_value >= 0),
    effective_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    reason VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    CONSTRAINT valid_date_range CHECK (end_date IS NULL OR effective_date < end_date),
    CONSTRAINT one_current_price_per_apartment UNIQUE(apartment_id, is_current) WHERE is_current = TRUE
);

-- Payment Tracking Table
CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    lease_id BIGINT NOT NULL REFERENCES leases(id),
    payment_category VARCHAR(20) NOT NULL CHECK (payment_category IN
        ('rent', 'cleaning', 'deposit', 'late_fee', 'damage', 'utility', 'other')),

    -- Financial Information
    amount_due DECIMAL(10,2) NOT NULL CHECK (amount_due > 0),
    amount_paid DECIMAL(10,2) DEFAULT 0 CHECK (amount_paid >= 0),
    discount_amount DECIMAL(10,2) DEFAULT 0 CHECK (discount_amount >= 0),
    late_fee_amount DECIMAL(10,2) DEFAULT 0 CHECK (late_fee_amount >= 0),

    -- Date Information
    due_date DATE NOT NULL,
    paid_date DATE,
    reference_month DATE,

    -- Payment Status and Method
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN
        ('pending', 'partial', 'paid', 'overdue', 'cancelled', 'refunded')),
    payment_method VARCHAR(50) CHECK (payment_method IN
        ('cash', 'check', 'transfer', 'pix', 'credit_card', 'debit_card', 'deposit', 'other')),
    transaction_reference VARCHAR(100),
    bank_name VARCHAR(100),

    -- Metadata
    notes TEXT,
    receipt_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_by VARCHAR(100),
    processing_date TIMESTAMP,

    -- Constraints
    CONSTRAINT paid_date_when_paid CHECK (
        (status IN ('paid', 'refunded') AND paid_date IS NOT NULL) OR
        (status NOT IN ('paid', 'refunded'))
    ),
    CONSTRAINT amount_paid_validation CHECK (
        (status = 'paid' AND amount_paid >= amount_due - discount_amount) OR
        (status = 'partial' AND amount_paid > 0 AND amount_paid < amount_due - discount_amount) OR
        (status IN ('pending', 'overdue', 'cancelled') AND amount_paid = 0) OR
        (status = 'refunded')
    )
);

-- Document Management Table
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN
        ('contract', 'addendum', 'receipt', 'notice', 'warning', 'inspection', 'invoice', 'photo', 'other')),

    -- Associations (flexible - can be linked to multiple entities)
    lease_id BIGINT REFERENCES leases(id) ON DELETE CASCADE,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    apartment_id BIGINT REFERENCES apartments(id) ON DELETE CASCADE,
    payment_id BIGINT REFERENCES payments(id) ON DELETE CASCADE,

    -- Document Information
    title VARCHAR(200) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(50),
    mime_type VARCHAR(100),
    file_hash VARCHAR(64), -- SHA-256 for integrity verification

    -- Version Control
    version INTEGER DEFAULT 1,
    parent_document_id BIGINT REFERENCES documents(id),
    is_latest_version BOOLEAN DEFAULT TRUE,

    -- Digital Signature Tracking
    requires_signatures BOOLEAN DEFAULT FALSE,
    tenant_signed BOOLEAN DEFAULT FALSE,
    tenant_signed_at TIMESTAMP,
    tenant_signature_ip INET,
    landlord_signed BOOLEAN DEFAULT FALSE,
    landlord_signed_at TIMESTAMP,
    landlord_signature_ip INET,

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),
    generated_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    archived_at TIMESTAMP,
    archived_by VARCHAR(100),
    metadata JSONB,

    -- Ensure at least one association exists
    CONSTRAINT document_has_association CHECK (
        lease_id IS NOT NULL OR
        tenant_id IS NOT NULL OR
        apartment_id IS NOT NULL OR
        payment_id IS NOT NULL
    )
);

-- Expense Tracking Table
CREATE TABLE IF NOT EXISTS expenses (
    id BIGSERIAL PRIMARY KEY,
    expense_type VARCHAR(30) NOT NULL CHECK (expense_type IN
        ('maintenance', 'repair', 'tax', 'insurance', 'utility', 'cleaning', 'management', 'legal', 'other')),

    -- Associations
    building_id BIGINT REFERENCES buildings(id) ON DELETE CASCADE,
    apartment_id BIGINT REFERENCES apartments(id) ON DELETE CASCADE,

    -- Expense Details
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    expense_date DATE NOT NULL,
    payment_date DATE,

    -- Vendor Information
    vendor_name VARCHAR(200),
    vendor_document VARCHAR(20),
    vendor_phone VARCHAR(20),
    invoice_number VARCHAR(100),

    -- Recurrence Settings
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(20) CHECK (recurrence_pattern IN
        ('monthly', 'bimonthly', 'quarterly', 'semiannual', 'yearly')),
    recurrence_day INTEGER CHECK (recurrence_day BETWEEN 1 AND 31),
    next_recurrence_date DATE,
    recurrence_end_date DATE,

    -- Approval Workflow
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    approval_notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),

    -- Ensure proper association
    CONSTRAINT expense_has_valid_association CHECK (
        (building_id IS NOT NULL AND apartment_id IS NULL) OR
        (building_id IS NULL AND apartment_id IS NOT NULL)
    ),
    CONSTRAINT recurrence_fields_consistency CHECK (
        (is_recurring = TRUE AND recurrence_pattern IS NOT NULL) OR
        (is_recurring = FALSE AND recurrence_pattern IS NULL)
    )
);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id BIGINT NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN
        ('INSERT', 'UPDATE', 'DELETE', 'RESTORE', 'ARCHIVE')),

    -- Change Details
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    change_summary TEXT,

    -- User Information
    user_id BIGINT,
    user_name VARCHAR(100),
    user_ip INET,
    user_agent TEXT,
    session_id VARCHAR(100),

    -- Additional Context
    request_id VARCHAR(50),
    api_endpoint VARCHAR(200),
    http_method VARCHAR(10),

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notification Queue Table
CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL CHECK (notification_type IN
        ('payment_reminder', 'payment_overdue', 'contract_expiring', 'contract_expired',
         'maintenance_scheduled', 'document_signed', 'warning_issued', 'general')),

    -- Recipients
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    user_id BIGINT,
    recipient_email VARCHAR(255),
    recipient_phone VARCHAR(20),

    -- Content
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN
        ('low', 'normal', 'high', 'urgent')),

    -- Delivery Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN
        ('pending', 'queued', 'sending', 'sent', 'delivered', 'failed', 'cancelled')),
    delivery_method VARCHAR(20) CHECK (delivery_method IN
        ('email', 'sms', 'whatsapp', 'push', 'in_app')),

    -- Tracking
    queued_at TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    failed_at TIMESTAMP,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Related Entities
    related_entity_type VARCHAR(50),
    related_entity_id BIGINT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    scheduled_for TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

-- Lease Status History Table
CREATE TABLE IF NOT EXISTS lease_status_history (
    id BIGSERIAL PRIMARY KEY,
    lease_id BIGINT NOT NULL REFERENCES leases(id) ON DELETE CASCADE,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    reason VARCHAR(200),
    notes TEXT,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(100)
);

-- =============================================
-- STEP 3: Create Indexes for Performance
-- =============================================

-- Payment Indexes
CREATE INDEX idx_payments_lease_status ON payments(lease_id, status, due_date);
CREATE INDEX idx_payments_due_date ON payments(due_date) WHERE status IN ('pending', 'overdue');
CREATE INDEX idx_payments_reference_month ON payments(lease_id, reference_month);
CREATE INDEX idx_payments_overdue ON payments(due_date, status) WHERE status = 'pending' AND due_date < CURRENT_DATE;

-- Document Indexes
CREATE INDEX idx_documents_lease ON documents(lease_id, document_type) WHERE is_active = TRUE;
CREATE INDEX idx_documents_tenant ON documents(tenant_id, document_type) WHERE is_active = TRUE;
CREATE INDEX idx_documents_signatures_pending ON documents(id)
    WHERE requires_signatures = TRUE AND (tenant_signed = FALSE OR landlord_signed = FALSE);

-- Expense Indexes
CREATE INDEX idx_expenses_building_date ON expenses(building_id, expense_date);
CREATE INDEX idx_expenses_apartment_date ON expenses(apartment_id, expense_date);
CREATE INDEX idx_expenses_recurring ON expenses(next_recurrence_date) WHERE is_recurring = TRUE;

-- Audit Log Indexes
CREATE INDEX idx_audit_table_record ON audit_logs(table_name, record_id, created_at DESC);
CREATE INDEX idx_audit_user_actions ON audit_logs(user_id, action, created_at DESC);
CREATE INDEX idx_audit_timestamp ON audit_logs(created_at DESC);

-- Notification Indexes
CREATE INDEX idx_notifications_tenant_pending ON notifications(tenant_id, status)
    WHERE status IN ('pending', 'queued');
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_for)
    WHERE status = 'pending' AND scheduled_for IS NOT NULL;

-- Apartment Pricing Indexes
CREATE INDEX idx_apartment_pricing_current ON apartment_pricing(apartment_id) WHERE is_current = TRUE;
CREATE INDEX idx_apartment_pricing_dates ON apartment_pricing(apartment_id, effective_date, end_date);

-- =============================================
-- STEP 4: Create Views for Backward Compatibility
-- =============================================

-- View to maintain compatibility with old apartment structure
CREATE OR REPLACE VIEW v_apartments_legacy AS
SELECT
    a.*,
    COALESCE(ap.rental_value, a.rental_value) as current_rental_value,
    COALESCE(ap.cleaning_fee, a.cleaning_fee) as current_cleaning_fee,
    CASE
        WHEN l.id IS NOT NULL AND l.status = 'active' THEN TRUE
        ELSE FALSE
    END as is_currently_rented,
    l.start_date as current_lease_start_date
FROM apartments a
LEFT JOIN apartment_pricing ap ON a.id = ap.apartment_id AND ap.is_current = TRUE
LEFT JOIN leases l ON a.id = l.apartment_id AND l.status = 'active';

-- View for payment dashboard
CREATE OR REPLACE VIEW v_payment_summary AS
SELECT
    l.id as lease_id,
    l.lease_number,
    a.number as apartment_number,
    b.street_number as building_number,
    t.name as tenant_name,
    p.due_date,
    p.amount_due,
    p.amount_paid,
    p.status,
    p.payment_category,
    CASE
        WHEN p.status = 'pending' AND p.due_date < CURRENT_DATE THEN 'OVERDUE'
        WHEN p.status = 'pending' AND p.due_date <= CURRENT_DATE + INTERVAL '5 days' THEN 'DUE SOON'
        ELSE 'OK'
    END as urgency
FROM payments p
JOIN leases l ON p.lease_id = l.id
JOIN apartments a ON l.apartment_id = a.id
JOIN buildings b ON a.building_id = b.id
JOIN tenants t ON l.responsible_tenant_id = t.id;

-- View for financial reporting
CREATE OR REPLACE VIEW v_financial_summary AS
SELECT
    DATE_TRUNC('month', p.due_date) as month,
    b.street_number as building_number,
    COUNT(DISTINCT l.id) as active_leases,
    SUM(CASE WHEN p.payment_category = 'rent' THEN p.amount_due ELSE 0 END) as total_rent_due,
    SUM(CASE WHEN p.payment_category = 'rent' AND p.status = 'paid' THEN p.amount_paid ELSE 0 END) as total_rent_collected,
    SUM(CASE WHEN p.status = 'overdue' THEN p.amount_due - p.amount_paid ELSE 0 END) as total_overdue,
    SUM(p.late_fee_amount) as total_late_fees,
    COUNT(CASE WHEN p.status = 'overdue' THEN 1 END) as overdue_count
FROM payments p
JOIN leases l ON p.lease_id = l.id
JOIN apartments a ON l.apartment_id = a.id
JOIN buildings b ON a.building_id = b.id
WHERE p.payment_category = 'rent'
GROUP BY DATE_TRUNC('month', p.due_date), b.street_number;

-- =============================================
-- STEP 5: Create Triggers for Data Integrity
-- =============================================

-- Trigger to maintain audit log
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        table_name,
        record_id,
        action,
        old_values,
        new_values,
        changed_fields,
        user_name,
        created_at
    )
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END,
        CASE
            WHEN TG_OP = 'UPDATE' THEN
                ARRAY(
                    SELECT jsonb_object_keys(to_jsonb(NEW))
                    WHERE to_jsonb(NEW) -> jsonb_object_keys(to_jsonb(NEW))
                        IS DISTINCT FROM to_jsonb(OLD) -> jsonb_object_keys(to_jsonb(NEW))
                )
            ELSE NULL
        END,
        current_user,
        NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to critical tables
CREATE TRIGGER audit_leases AFTER INSERT OR UPDATE OR DELETE ON leases
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
CREATE TRIGGER audit_payments AFTER INSERT OR UPDATE OR DELETE ON payments
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
CREATE TRIGGER audit_tenants AFTER INSERT OR UPDATE OR DELETE ON tenants
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger to update payment status automatically
CREATE OR REPLACE FUNCTION update_payment_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Mark as overdue if past due date
    IF NEW.status = 'pending' AND NEW.due_date < CURRENT_DATE THEN
        NEW.status := 'overdue';
    END IF;

    -- Mark as paid if fully paid
    IF NEW.amount_paid >= (NEW.amount_due - NEW.discount_amount) THEN
        NEW.status := 'paid';
        IF NEW.paid_date IS NULL THEN
            NEW.paid_date := CURRENT_DATE;
        END IF;
    ELSIF NEW.amount_paid > 0 AND NEW.amount_paid < (NEW.amount_due - NEW.discount_amount) THEN
        NEW.status := 'partial';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payment_status_update BEFORE INSERT OR UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_payment_status();

-- Trigger to track lease status changes
CREATE OR REPLACE FUNCTION track_lease_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO lease_status_history (
            lease_id,
            previous_status,
            new_status,
            changed_at,
            changed_by
        )
        VALUES (
            NEW.id,
            OLD.status,
            NEW.status,
            NOW(),
            current_user
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER lease_status_tracker AFTER UPDATE ON leases
    FOR EACH ROW EXECUTE FUNCTION track_lease_status_change();

-- =============================================
-- STEP 6: Data Migration Scripts
-- =============================================

-- Migrate existing apartment pricing to new table
INSERT INTO apartment_pricing (
    apartment_id,
    rental_value,
    cleaning_fee,
    effective_date,
    is_current,
    created_at,
    created_by
)
SELECT
    id,
    rental_value,
    cleaning_fee,
    COALESCE(lease_date, CURRENT_DATE),
    TRUE,
    NOW(),
    'migration_script'
FROM apartments
WHERE rental_value IS NOT NULL
ON CONFLICT (apartment_id, is_current) WHERE is_current = TRUE DO NOTHING;

-- Create initial payment records for active leases
INSERT INTO payments (
    lease_id,
    payment_category,
    amount_due,
    due_date,
    reference_month,
    status,
    created_at
)
SELECT
    l.id,
    'rent',
    l.rental_value,
    DATE(DATE_TRUNC('month', CURRENT_DATE) + (l.due_day - 1) * INTERVAL '1 day'),
    DATE_TRUNC('month', CURRENT_DATE),
    'pending',
    NOW()
FROM leases l
WHERE l.status = 'active'  -- Assuming you add status column to leases
  AND NOT EXISTS (
    SELECT 1 FROM payments p
    WHERE p.lease_id = l.id
      AND p.reference_month = DATE_TRUNC('month', CURRENT_DATE)
      AND p.payment_category = 'rent'
);

-- =============================================
-- STEP 7: Create Stored Procedures
-- =============================================

-- Procedure to generate monthly payments
CREATE OR REPLACE PROCEDURE generate_monthly_payments(
    p_month DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_lease RECORD;
    v_payment_id BIGINT;
BEGIN
    FOR v_lease IN
        SELECT
            l.id,
            l.rental_value,
            l.due_day,
            l.cleaning_fee
        FROM leases l
        WHERE l.status = 'active'
          AND l.start_date <= p_month
          AND (l.end_date IS NULL OR l.end_date >= p_month)
    LOOP
        -- Create rent payment
        INSERT INTO payments (
            lease_id,
            payment_category,
            amount_due,
            due_date,
            reference_month,
            status
        )
        VALUES (
            v_lease.id,
            'rent',
            v_lease.rental_value,
            p_month + (v_lease.due_day - 1) * INTERVAL '1 day',
            p_month,
            'pending'
        )
        ON CONFLICT DO NOTHING
        RETURNING id INTO v_payment_id;

        -- Log the creation
        IF v_payment_id IS NOT NULL THEN
            RAISE NOTICE 'Created payment % for lease %', v_payment_id, v_lease.id;
        END IF;
    END LOOP;

    COMMIT;
END;
$$;

-- Procedure to calculate late fees
CREATE OR REPLACE FUNCTION calculate_late_fee(
    p_payment_id BIGINT
)
RETURNS DECIMAL AS $$
DECLARE
    v_payment RECORD;
    v_days_late INTEGER;
    v_daily_rate DECIMAL;
    v_late_fee DECIMAL;
BEGIN
    SELECT * INTO v_payment
    FROM payments
    WHERE id = p_payment_id;

    IF v_payment.status != 'pending' OR v_payment.due_date >= CURRENT_DATE THEN
        RETURN 0;
    END IF;

    v_days_late := CURRENT_DATE - v_payment.due_date;
    v_daily_rate := v_payment.amount_due / 30;
    v_late_fee := v_daily_rate * v_days_late * 0.05; -- 5% per day

    -- Update the payment record
    UPDATE payments
    SET late_fee_amount = v_late_fee,
        status = 'overdue'
    WHERE id = p_payment_id;

    RETURN v_late_fee;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- STEP 8: Grant Permissions (adjust as needed)
-- =============================================

-- Create roles
CREATE ROLE app_user;
CREATE ROLE app_admin;
CREATE ROLE app_readonly;

-- Grant permissions to app_user
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Grant permissions to app_admin
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_admin;

-- Grant permissions to app_readonly
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

-- =============================================
-- STEP 9: Add Comments for Documentation
-- =============================================

COMMENT ON TABLE payments IS 'Tracks all payment transactions for leases including rent, deposits, and fees';
COMMENT ON COLUMN payments.status IS 'Payment status: pending, partial, paid, overdue, cancelled, refunded';
COMMENT ON COLUMN payments.payment_category IS 'Type of payment: rent, cleaning, deposit, late_fee, damage, utility, other';

COMMENT ON TABLE documents IS 'Document management system for contracts, receipts, and other files';
COMMENT ON COLUMN documents.file_hash IS 'SHA-256 hash for file integrity verification';

COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all database changes';
COMMENT ON COLUMN audit_logs.changed_fields IS 'Array of field names that were modified in UPDATE operations';

-- =============================================
-- STEP 10: Rollback Scripts
-- =============================================

/*
-- ROLLBACK SCRIPT - Use with caution!
-- This will undo the migration

DROP TABLE IF EXISTS lease_status_history CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS apartment_pricing CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;

DROP VIEW IF EXISTS v_apartments_legacy;
DROP VIEW IF EXISTS v_payment_summary;
DROP VIEW IF EXISTS v_financial_summary;

DROP FUNCTION IF EXISTS audit_trigger_function() CASCADE;
DROP FUNCTION IF EXISTS update_payment_status() CASCADE;
DROP FUNCTION IF EXISTS track_lease_status_change() CASCADE;
DROP FUNCTION IF EXISTS calculate_late_fee(BIGINT) CASCADE;
DROP PROCEDURE IF EXISTS generate_monthly_payments(DATE) CASCADE;

DROP ROLE IF EXISTS app_user;
DROP ROLE IF EXISTS app_admin;
DROP ROLE IF EXISTS app_readonly;
*/

-- =============================================
-- Record Migration Completion
-- =============================================

INSERT INTO schema_migrations (version, description, applied_by)
VALUES (
    '2.0.0',
    'Major database refactoring: Added payment tracking, document management, audit logs, expense tracking',
    current_user
);