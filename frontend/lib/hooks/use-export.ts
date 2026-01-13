import { useState } from 'react';
import * as XLSX from 'xlsx';
import { format } from 'date-fns';
import { formatCurrency, formatCPFOrCNPJ, formatBrazilianPhone } from '@/lib/utils/formatters';

interface ExportOptions {
  filename?: string;
  sheetName?: string;
}

/**
 * Custom hook for exporting data to Excel
 * Handles formatting, file generation, and download
 */
export function useExport() {
  const [isExporting, setIsExporting] = useState(false);

  const exportToExcel = async <T extends Record<string, unknown>>(
    data: T[],
    columns: {
      key: string;
      label: string;
      format?: (value: unknown, record: T) => string | number;
    }[],
    options: ExportOptions = {}
  ) => {
    setIsExporting(true);

    try {
      // Transform data to match column definitions
      const formattedData = data.map((record) => {
        const row: Record<string, string | number> = {};
        columns.forEach((column) => {
          const value = record[column.key];
          const formattedValue = column.format
            ? column.format(value, record)
            : String(value ?? '');
          row[column.label] = formattedValue;
        });
        return row;
      });

      // Create workbook and worksheet
      const worksheet = XLSX.utils.json_to_sheet(formattedData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(
        workbook,
        worksheet,
        options.sheetName || 'Dados'
      );

      // Auto-size columns
      const maxWidths: number[] = [];
      columns.forEach((column, idx) => {
        const headerLength = column.label.length;
        const maxContentLength = Math.max(
          ...formattedData.map((row) =>
            String(row[column.label] || '').length
          )
        );
        maxWidths[idx] = Math.min(
          Math.max(headerLength, maxContentLength) + 2,
          50
        );
      });
      worksheet['!cols'] = maxWidths.map((width) => ({ width }));

      // Generate filename with timestamp
      const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss');
      const filename = options.filename
        ? `${options.filename}_${timestamp}.xlsx`
        : `export_${timestamp}.xlsx`;

      // Download file
      XLSX.writeFile(workbook, filename);

      return { success: true, filename };
    } catch (error) {
      console.error('Export error:', error);
      throw new Error('Erro ao exportar arquivo');
    } finally {
      setIsExporting(false);
    }
  };

  const exportToCSV = async <T extends Record<string, unknown>>(
    data: T[],
    columns: {
      key: string;
      label: string;
      format?: (value: unknown, record: T) => string | number;
    }[],
    options: ExportOptions = {}
  ) => {
    setIsExporting(true);

    try {
      // Transform data to match column definitions
      const formattedData = data.map((record) => {
        const row: Record<string, string | number> = {};
        columns.forEach((column) => {
          const value = record[column.key];
          const formattedValue = column.format
            ? column.format(value, record)
            : String(value ?? '');
          row[column.label] = formattedValue;
        });
        return row;
      });

      // Create worksheet for CSV conversion
      const worksheet = XLSX.utils.json_to_sheet(formattedData);
      const csv = XLSX.utils.sheet_to_csv(worksheet);

      // Create blob and download
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss');
      const filename = options.filename
        ? `${options.filename}_${timestamp}.csv`
        : `export_${timestamp}.csv`;

      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      return { success: true, filename };
    } catch (error) {
      console.error('Export error:', error);
      throw new Error('Erro ao exportar arquivo CSV');
    } finally {
      setIsExporting(false);
    }
  };

  return {
    exportToExcel,
    exportToCSV,
    isExporting,
  };
}

/**
 * Predefined column configurations for common entity types
 */

export const buildingExportColumns = [
  { key: 'name' as const, label: 'Nome' },
  { key: 'street_number' as const, label: 'Número' },
  { key: 'address' as const, label: 'Endereço' },
  {
    key: 'created_at' as const,
    label: 'Data de Cadastro',
    format: (value: unknown) => format(new Date(String(value ?? '')), 'dd/MM/yyyy HH:mm'),
  },
];

export const apartmentExportColumns = [
  {
    key: 'number' as const,
    label: 'Número',
  },
  {
    key: 'building' as const,
    label: 'Prédio',
    format: (value: unknown) => (value && typeof value === 'object' && 'name' in value ? String(value.name) : ''),
  },
  {
    key: 'rental_value' as const,
    label: 'Valor do Aluguel',
    format: (value: unknown) => formatCurrency(Number(value) || 0),
  },
  {
    key: 'cleaning_fee' as const,
    label: 'Taxa de Limpeza',
    format: (value: unknown) => formatCurrency(Number(value) || 0),
  },
  {
    key: 'is_rented' as const,
    label: 'Status',
    format: (value: unknown) => (value ? 'Alugado' : 'Disponível'),
  },
  {
    key: 'furnitures' as const,
    label: 'Móveis',
    format: (value: unknown) => (Array.isArray(value) ? value.length : 0),
  },
];

export const tenantExportColumns = [
  { key: 'name' as const, label: 'Nome / Razão Social' },
  {
    key: 'cpf_cnpj' as const,
    label: 'CPF / CNPJ',
    format: (value: unknown) => formatCPFOrCNPJ(String(value ?? '')),
  },
  {
    key: 'phone' as const,
    label: 'Telefone',
    format: (value: unknown) => formatBrazilianPhone(String(value ?? '')),
  },
  { key: 'email' as const, label: 'Email' },
  {
    key: 'is_company' as const,
    label: 'Tipo',
    format: (value: unknown) => (value ? 'Empresa' : 'Pessoa Física'),
  },
  { key: 'profession' as const, label: 'Profissão' },
  { key: 'marital_status' as const, label: 'Estado Civil' },
  {
    key: 'dependents' as const,
    label: 'Dependentes',
    format: (value: unknown) => (Array.isArray(value) ? value.length : 0),
  },
  {
    key: 'furnitures' as const,
    label: 'Móveis',
    format: (value: unknown) => (Array.isArray(value) ? value.length : 0),
  },
];

export const leaseExportColumns = [
  {
    key: 'apartment' as const,
    label: 'Apartamento',
    format: (value: unknown) => {
      if (value && typeof value === 'object' && 'number' in value) {
        const building = 'building' in value && value.building && typeof value.building === 'object' && 'name' in value.building ? String(value.building.name) : '';
        return `${building} - Apto ${value.number}`;
      }
      return '';
    },
  },
  {
    key: 'responsible_tenant' as const,
    label: 'Inquilino Responsável',
    format: (value: unknown) => (value && typeof value === 'object' && 'name' in value ? String(value.name) : ''),
  },
  {
    key: 'start_date' as const,
    label: 'Data de Início',
    format: (value: unknown) => format(new Date(String(value ?? '')), 'dd/MM/yyyy'),
  },
  {
    key: 'final_date' as const,
    label: 'Data Final',
    format: (value: unknown) => format(new Date(String(value ?? '')), 'dd/MM/yyyy'),
  },
  {
    key: 'next_month_date' as const,
    label: 'Próximo Mês',
    format: (value: unknown) => format(new Date(String(value ?? '')), 'dd/MM/yyyy'),
  },
  { key: 'validity_months' as const, label: 'Validade (meses)' },
  { key: 'due_day' as const, label: 'Dia de Vencimento' },
  {
    key: 'rental_value' as const,
    label: 'Valor do Aluguel',
    format: (value: unknown) => formatCurrency(Number(value) || 0),
  },
  {
    key: 'cleaning_fee' as const,
    label: 'Taxa de Limpeza',
    format: (value: unknown) => formatCurrency(Number(value) || 0),
  },
  {
    key: 'tag_fee' as const,
    label: 'Taxa de Etiquetas',
    format: (value: unknown) => formatCurrency(Number(value) || 0),
  },
  {
    key: 'tenants' as const,
    label: 'Total de Inquilinos',
    format: (value: unknown) => (Array.isArray(value) ? value.length : 0),
  },
];

export const furnitureExportColumns = [
  { key: 'name' as const, label: 'Nome' },
  { key: 'description' as const, label: 'Descrição' },
  {
    key: 'created_at' as const,
    label: 'Data de Cadastro',
    format: (value: unknown) => format(new Date(String(value ?? '')), 'dd/MM/yyyy HH:mm'),
  },
];
