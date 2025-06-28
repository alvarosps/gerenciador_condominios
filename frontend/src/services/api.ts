import axios from 'axios';
import {
    Apartment,
    Building,
    CreateApartmentRequest,
    CreateLeaseRequest,
    CreateTenantRequest,
    Furniture,
    Lease,
    Tenant,
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para logs de desenvolvimento
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Buildings
  buildings: {
    getAll: () => api.get<Building[]>('/buildings/'),
    getById: (id: number) => api.get<Building>(`/buildings/${id}/`),
    create: (data: Omit<Building, 'id'>) => api.post<Building>('/buildings/', data),
    update: (id: number, data: Partial<Building>) => api.put<Building>(`/buildings/${id}/`, data),
    delete: (id: number) => api.delete(`/buildings/${id}/`),
  },

  // Furnitures
  furnitures: {
    getAll: () => api.get<Furniture[]>('/furnitures/'),
    getById: (id: number) => api.get<Furniture>(`/furnitures/${id}/`),
    create: (data: Omit<Furniture, 'id'>) => api.post<Furniture>('/furnitures/', data),
    update: (id: number, data: Partial<Furniture>) => api.put<Furniture>(`/furnitures/${id}/`, data),
    delete: (id: number) => api.delete(`/furnitures/${id}/`),
  },

  // Apartments
  apartments: {
    getAll: () => api.get<Apartment[]>('/apartments/'),
    getById: (id: number) => api.get<Apartment>(`/apartments/${id}/`),
    create: (data: CreateApartmentRequest) => api.post<Apartment>('/apartments/', data),
    update: (id: number, data: Partial<Apartment>) => api.put<Apartment>(`/apartments/${id}/`, data),
    delete: (id: number) => api.delete(`/apartments/${id}/`),
  },

  // Tenants
  tenants: {
    getAll: () => api.get<Tenant[]>('/tenants/'),
    getById: (id: number) => api.get<Tenant>(`/tenants/${id}/`),
    create: (data: CreateTenantRequest) => api.post<Tenant>('/tenants/', data),
    update: (id: number, data: Partial<CreateTenantRequest>) => api.put<Tenant>(`/tenants/${id}/`, data),
    delete: (id: number) => api.delete(`/tenants/${id}/`),
  },

  // Leases
  leases: {
    getAll: () => api.get<Lease[]>('/leases/'),
    getById: (id: number) => api.get<Lease>(`/leases/${id}/`),
    create: (data: CreateLeaseRequest) => api.post<Lease>('/leases/', data),
    update: (id: number, data: Partial<CreateLeaseRequest>) => api.put<Lease>(`/leases/${id}/`, data),
    delete: (id: number) => api.delete(`/leases/${id}/`),
    generateContract: (id: number) => api.post(`/leases/${id}/generate_contract/`),
    calculateLateFee: (id: number) => api.get(`/leases/${id}/calculate_late_fee/`),
    changeDueDate: (id: number, newDueDay: number) => 
      api.post(`/leases/${id}/change_due_date/`, { new_due_day: newDueDay }),
  },
};

export default api;
