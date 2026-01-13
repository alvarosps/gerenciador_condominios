/**
 * Re-export from wizard module for backward compatibility.
 * The wizard has been split into smaller, focused components:
 * - wizard/types.ts - Schema and type definitions
 * - wizard/basic-info-step.tsx - Name and document info
 * - wizard/contact-info-step.tsx - Phone and email
 * - wizard/professional-info-step.tsx - Profession and marital status
 * - wizard/dependents-step.tsx - Dependent management
 * - wizard/furniture-step.tsx - Furniture selection
 * - wizard/review-step.tsx - Final review before save
 * - wizard/index.tsx - Main orchestrator
 */
export { TenantFormWizard } from './wizard';
