import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { toast } from 'sonner';
import { useCrudPage } from '../use-crud-page';
import { useExport } from '../use-export';
import { createWrapper } from '@/tests/test-utils';

// useExport is the sanctioned boundary to mock here — the real export triggers xlsx + a DOM
// download. handleExport's own logic (guards, await, toasts) is what we exercise.
vi.mock('../use-export', () => ({ useExport: vi.fn() }));
vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

const exportToExcel = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const exportToCSV = vi.fn<(...args: unknown[]) => Promise<unknown>>();

const deleteMutation = { mutate: vi.fn(), isPending: false } as never;
const columns = [{ key: 'name', label: 'Nome' }];
const rows: { id?: number; name: string }[] = [{ name: 'Alvaro' }];

function setup(overrides: Record<string, unknown> = {}) {
  return renderHook(
    () =>
      useCrudPage<{ id?: number; name: string }>({
        entityName: 'conta',
        entityNamePlural: 'contas',
        deleteMutation,
        exportColumns: columns,
        exportFilename: 'contas',
        ...overrides,
      }),
    { wrapper: createWrapper() }
  );
}

describe('useCrudPage.handleExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    exportToExcel.mockResolvedValue({ success: true, filename: 'contas.xlsx' });
    exportToCSV.mockResolvedValue({ success: true, filename: 'contas.csv' });
    vi.mocked(useExport).mockReturnValue({
      exportToExcel,
      exportToCSV,
      isExporting: false,
    } as unknown as ReturnType<typeof useExport>);
  });

  it('excel: awaits exportToExcel then toasts success', async () => {
    const { result } = setup();
    await act(async () => {
      await result.current.handleExport('excel', rows);
    });
    expect(exportToExcel).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalledWith('Arquivo Excel exportado com sucesso!');
  });

  it('csv: a rejected export shows the error toast (await keeps the rejection in try/catch)', async () => {
    exportToCSV.mockRejectedValueOnce(new Error('boom'));
    const { result } = setup();
    await act(async () => {
      await result.current.handleExport('csv', rows);
    });
    expect(toast.error).toHaveBeenCalledWith('Erro ao exportar arquivo');
    expect(toast.success).not.toHaveBeenCalled();
  });

  it('warns and does not export when there is no data', async () => {
    const { result } = setup();
    await act(async () => {
      await result.current.handleExport('excel', []);
    });
    expect(toast.warning).toHaveBeenCalledWith('Não há dados para exportar');
    expect(exportToExcel).not.toHaveBeenCalled();
  });

  it('warns when export is not configured', async () => {
    const { result } = setup({ exportColumns: undefined, exportFilename: undefined });
    await act(async () => {
      await result.current.handleExport('excel', rows);
    });
    expect(toast.warning).toHaveBeenCalledWith('Exportação não configurada');
    expect(exportToExcel).not.toHaveBeenCalled();
  });
});
