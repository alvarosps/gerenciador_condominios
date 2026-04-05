import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type Person, personSchema } from '@/lib/schemas/person.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export function usePersons() {
  return useQuery({
    queryKey: queryKeys.persons.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Person> | Person[]>('/persons/', {
        params: { page_size: 10000 },
      });
      const persons = extractResults(data);
      return persons.map((person) => personSchema.parse(person));
    },
  });
}

export function usePerson(id: number | null) {
  return useQuery({
    queryKey: queryKeys.persons.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Person ID is required');
      const { data } = await apiClient.get<Person>(`/persons/${id}/`);
      return personSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreatePerson() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Person, 'id' | 'credit_cards'>) => {
      const response = await apiClient.post<Person>('/persons/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
    },
  });
}

export function useUpdatePerson() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Person> & { id: number }) => {
      if (!data.id) throw new Error('Person ID is required for update');
      const { credit_cards: _credit_cards, ...updateData } = data;
      const response = await apiClient.put<Person>(`/persons/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.persons.detail(data.id) });
      }
    },
  });
}

export function useDeletePerson() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/persons/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
    },
  });
}
