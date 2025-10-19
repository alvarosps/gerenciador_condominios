import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  useFurniture,
  useCreateFurniture,
  useUpdateFurniture,
  useDeleteFurniture,
} from '@/lib/api/hooks/use-furniture';
import type { Furniture } from '@/lib/schemas/furniture.schema';

// Mock data
const mockFurniture: Furniture[] = [
  { id: 1, name: 'Sofá' },
  { id: 2, name: 'Mesa' },
  { id: 3, name: 'Cama' },
];

// Set up MSW server
const server = setupServer(
  http.get('http://localhost:8000/api/furnitures/', () => {
    return HttpResponse.json(mockFurniture);
  }),
  http.post('http://localhost:8000/api/furnitures/', async ({ request }) => {
    const body = await request.json() as Omit<Furniture, 'id'>;
    return HttpResponse.json({ id: 4, ...body });
  }),
  http.put('http://localhost:8000/api/furnitures/:id/', async ({ request }) => {
    const body = await request.json() as Furniture;
    return HttpResponse.json(body);
  }),
  http.delete('http://localhost:8000/api/furnitures/:id/', () => {
    return new HttpResponse(null, { status: 204 });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Helper to create a wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useFurniture', () => {
  it('should fetch furniture items successfully', async () => {
    const { result } = renderHook(() => useFurniture(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockFurniture);
    expect(result.current.data).toHaveLength(3);
  });

  it('should handle fetch error', async () => {
    server.use(
      http.get('http://localhost:8000/api/furnitures/', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    const { result } = renderHook(() => useFurniture(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe('useCreateFurniture', () => {
  it('should create a furniture item successfully', async () => {
    const { result } = renderHook(() => useCreateFurniture(), {
      wrapper: createWrapper(),
    });

    const newFurniture = {
      name: 'Cadeira',
    };

    result.current.mutate(newFurniture);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject(newFurniture);
    expect(result.current.data?.id).toBe(4);
  });

  it('should handle create error', async () => {
    server.use(
      http.post('http://localhost:8000/api/furnitures/', () => {
        return new HttpResponse(null, { status: 400 });
      })
    );

    const { result } = renderHook(() => useCreateFurniture(), {
      wrapper: createWrapper(),
    });

    const newFurniture = {
      name: 'Cadeira',
    };

    result.current.mutate(newFurniture);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateFurniture', () => {
  it('should update a furniture item successfully', async () => {
    const { result } = renderHook(() => useUpdateFurniture(), {
      wrapper: createWrapper(),
    });

    const updatedFurniture = {
      id: 1,
      name: 'Sofá Atualizado',
    };

    result.current.mutate(updatedFurniture);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(updatedFurniture);
  });

  it('should handle update error', async () => {
    server.use(
      http.put('http://localhost:8000/api/furnitures/:id/', () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    const { result } = renderHook(() => useUpdateFurniture(), {
      wrapper: createWrapper(),
    });

    const updatedFurniture = {
      id: 999,
      name: 'Móvel Inexistente',
    };

    result.current.mutate(updatedFurniture);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useDeleteFurniture', () => {
  it('should delete a furniture item successfully', async () => {
    const { result } = renderHook(() => useDeleteFurniture(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('should handle delete error', async () => {
    server.use(
      http.delete('http://localhost:8000/api/furnitures/:id/', () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    const { result } = renderHook(() => useDeleteFurniture(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(999);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
