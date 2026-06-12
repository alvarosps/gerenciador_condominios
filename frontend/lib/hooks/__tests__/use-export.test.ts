import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useExport } from '../use-export';

// Mock ONLY the download boundary of xlsx (writeFile triggers a real file write); the sheet/csv
// computation (json_to_sheet/sheet_to_csv) runs for real — mock policy: external I/O only.
vi.mock('xlsx', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('xlsx');
  return { ...actual, writeFile: vi.fn() };
});

const columns = [{ key: 'name', label: 'Nome' }];
const data = [{ name: 'Alvaro' }];

describe('useExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // happy-dom may not provide the blob-download primitives the CSV path uses.
    URL.createObjectURL = vi.fn(() => 'blob:mock');
    URL.revokeObjectURL = vi.fn();
  });

  it('exportToExcel resolves a Promise with a .xlsx filename and triggers the xlsx download', async () => {
    const XLSX = await import('xlsx');
    const { result } = renderHook(() => useExport());

    let out: { success: boolean; filename: string } | undefined;
    await act(async () => {
      out = await result.current.exportToExcel(data, columns);
    });

    expect(out?.success).toBe(true);
    expect(out?.filename).toMatch(/\.xlsx$/);
    expect(XLSX.writeFile).toHaveBeenCalledTimes(1);
  });

  it('exportToCSV resolves a Promise with a .csv filename and clicks a download link', async () => {
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    const { result } = renderHook(() => useExport());

    let out: { success: boolean; filename: string } | undefined;
    await act(async () => {
      out = await result.current.exportToCSV(data, columns);
    });

    expect(out?.filename).toMatch(/\.csv$/);
    expect(clickSpy).toHaveBeenCalled();
  });

  it('isExporting returns to false after the export resolves (finally)', async () => {
    const { result } = renderHook(() => useExport());

    await act(async () => {
      await result.current.exportToExcel(data, columns);
    });

    expect(result.current.isExporting).toBe(false);
  });

  it('propagates "Erro ao exportar arquivo" when the Excel write fails', async () => {
    const XLSX = await import('xlsx');
    vi.mocked(XLSX.writeFile).mockImplementationOnce(() => {
      throw new Error('boom');
    });
    const { result } = renderHook(() => useExport());

    await expect(
      act(async () => {
        await result.current.exportToExcel(data, columns);
      })
    ).rejects.toThrow('Erro ao exportar arquivo');
  });

  it('propagates the CSV-specific "Erro ao exportar arquivo CSV" when the download fails', async () => {
    URL.createObjectURL = vi.fn(() => {
      throw new Error('boom');
    });
    const { result } = renderHook(() => useExport());

    await expect(
      act(async () => {
        await result.current.exportToCSV(data, columns);
      })
    ).rejects.toThrow('Erro ao exportar arquivo CSV');
  });

  it('exposes async exporters (the lazy-import path makes them AsyncFunctions)', () => {
    const { result } = renderHook(() => useExport());
    expect(result.current.exportToExcel.constructor.name).toBe('AsyncFunction');
    expect(result.current.exportToCSV.constructor.name).toBe('AsyncFunction');
  });
});
