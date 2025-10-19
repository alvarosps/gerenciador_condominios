import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  useBuildings,
  useCreateBuilding,
  useUpdateBuilding,
  useDeleteBuilding,
} from '@/lib/api/hooks/use-buildings';
import type { Building } from '@/lib/schemas/building.schema';

// Mock data
const mockBuildings: Building[] = [
  { id: 1, street_number: 836, name: 'Prédio A', address: 'Rua X, 100' },
  { id: 2, street_number: 850, name: 'Prédio B', address: 'Rua Y, 200' },
];

// Set up MSW server
const server = setupServer(
  http.get('http://localhost:8000/api/buildings/', () => {
    return HttpResponse.json(mockBuildings);
  }),
  http.post('http://localhost:8000/api/buildings/', async ({ request }) => {
    const body = await request.json() as Omit<Building, 'id'>;
    return HttpResponse.json({ id: 3, ...body });
  }),
  http.put('http://localhost:8000/api/buildings/:id/', async ({ request }) => {
    const body = await request.json() as Building;
    return HttpResponse.json(body);
  }),
  http.delete('http://localhost:8000/api/buildings/:id/', () => {
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

describe('useBuildings', () => {
  it('should fetch buildings successfully', async () => {
    const { result } = renderHook(() => useBuildings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockBuildings);
    expect(result.current.data).toHaveLength(2);
  });

  it('should handle fetch error', async () => {
    server.use(
      http.get('http://localhost:8000/api/buildings/', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    const { result } = renderHook(() => useBuildings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe('useCreateBuilding', () => {
  it('should create a building successfully', async () => {
    const { result } = renderHook(() => useCreateBuilding(), {
      wrapper: createWrapper(),
    });

    const newBuilding = {
      street_number: 900,
      name: 'Prédio C',
      address: 'Rua Z, 300',
    };

    result.current.mutate(newBuilding);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject(newBuilding);
    expect(result.current.data?.id).toBe(3);
  });

  it('should handle create error', async () => {
    server.use(
      http.post('http://localhost:8000/api/buildings/', () => {
        return new HttpResponse(null, { status: 400 });
      })
    );

    const { result } = renderHook(() => useCreateBuilding(), {
      wrapper: createWrapper(),
    });

    const newBuilding = {
      street_number: 900,
      name: 'Prédio C',
      address: 'Rua Z, 300',
    };

    result.current.mutate(newBuilding);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateBuilding', () => {
  it('should update a building successfully', async () => {
    const { result } = renderHook(() => useUpdateBuilding(), {
      wrapper: createWrapper(),
    });

    const updatedBuilding = {
      id: 1,
      street_number: 836,
      name: 'Prédio A Updated',
      address: 'Rua X, 100 - Updated',
    };

    result.current.mutate(updatedBuilding);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(updatedBuilding);
  });

  it('should handle update error', async () => {
    server.use(
      http.put('http://localhost:8000/api/buildings/:id/', () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    const { result } = renderHook(() => useUpdateBuilding(), {
      wrapper: createWrapper(),
    });

    const updatedBuilding = {
      id: 999,
      street_number: 836,
      name: 'Prédio A',
      address: 'Rua X, 100',
    };

    result.current.mutate(updatedBuilding);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useDeleteBuilding', () => {
  it('should delete a building successfully', async () => {
    const { result } = renderHook(() => useDeleteBuilding(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('should handle delete error', async () => {
    server.use(
      http.delete('http://localhost:8000/api/buildings/:id/', () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    const { result } = renderHook(() => useDeleteBuilding(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(999);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
