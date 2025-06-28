export interface Building {
  id: number;
  street_number: number;
  name: string;
  address: string;
}

export interface Furniture {
  id: number;
  name: string;
  description?: string;
}

export interface Apartment {
  id: number;
  building: Building;
  building_id?: number;
  number: number;
  interfone_configured: boolean;
  contract_generated: boolean;
  contract_signed: boolean;
  rental_value: number;
  cleaning_fee: number;
  max_tenants: number;
  is_rented: boolean;
  lease_date?: string;
  last_rent_increase_date?: string;
  furnitures: Furniture[];
}

export interface Dependent {
  id: number;
  name: string;
  phone: string;
  tenant: number;
}

export interface Tenant {
  id: number;
  name: string;
  cpf_cnpj: string;
  is_company: boolean;
  rg?: string;
  phone: string;
  marital_status: string;
  profession: string;
  deposit_amount?: number;
  cleaning_fee_paid: boolean;
  tag_deposit_paid: boolean;
  rent_due_day: number;
  dependents: Dependent[];
  furnitures: Furniture[];
  furniture_ids?: number[];
}

export interface Lease {
  id: number;
  apartment: Apartment;
  apartment_id?: number;
  responsible_tenant: Tenant;
  responsible_tenant_id?: number;
  tenants: Tenant[];
  tenant_ids?: number[];
  number_of_tenants: number;
  start_date: string;
  validity_months: number;
  due_day: number;
  rental_value: number;
  cleaning_fee: number;
  tag_fee: number;
  contract_generated: boolean;
  contract_signed: boolean;
  interfone_configured: boolean;
  warning_count: number;
}

export interface CreateApartmentRequest {
  building_id: number;
  number: number;
  rental_value: number;
  cleaning_fee: number;
  max_tenants: number;
  furniture_ids?: number[];
}

export interface CreateTenantRequest {
  name: string;
  cpf_cnpj: string;
  is_company: boolean;
  rg?: string;
  phone: string;
  marital_status: string;
  profession: string;
  deposit_amount?: number;
  rent_due_day: number;
  dependents?: Omit<Dependent, 'id' | 'tenant'>[];
  furniture_ids?: number[];
}

export interface CreateLeaseRequest {
  apartment_id: number;
  responsible_tenant_id: number;
  tenant_ids: number[];
  number_of_tenants: number;
  start_date: string;
  validity_months: number;
  due_day: number;
  rental_value: number;
  cleaning_fee: number;
  tag_fee: number;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

// Utility types for statistics and dashboard
export interface DashboardStats {
  totalBuildings: number;
  totalApartments: number;
  occupiedApartments: number;
  vacantApartments: number;
  occupancyRate: number;
  totalTenants: number;
  individualTenants: number;
  companyTenants: number;
  totalLeases: number;
  activeLeases: number;
  pendingLeases: number;
  monthlyRevenue: number;
  contractsToSign: number;
  contractsWithWarnings: number;
}

export interface ActivityItem {
  id: number;
  type: 'contract_signed' | 'payment_received' | 'maintenance_request' | 'contract_renewal' | 'new_tenant';
  description: string;
  date: string;
  tenant: string;
}

export interface BuildingStats {
  id: number;
  name: string;
  totalApartments: number;
  occupiedApartments: number;
  vacantApartments: number;
  occupancyRate: number;
  monthlyRevenue: number;
}

export interface ApartmentFilters {
  buildingId?: number;
  isRented?: boolean;
  minRentalValue?: number;
  maxRentalValue?: number;
  maxTenants?: number;
}

export interface TenantFilters {
  isCompany?: boolean;
  hasContract?: boolean;
  buildingId?: number;
}

export interface LeaseFilters {
  buildingId?: number;
  contractSigned?: boolean;
  hasWarnings?: boolean;
  startDate?: string;
  endDate?: string;
}
