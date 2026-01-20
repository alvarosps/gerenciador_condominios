'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Editor } from '@tiptap/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Code2, Search, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VariableInserterProps {
  editor: Editor;
  className?: string;
}

interface VariableDefinition {
  name: string;
  label: string;
  description: string;
  category: string;
}

const TEMPLATE_VARIABLES: VariableDefinition[] = [
  // Locador
  {
    name: 'landlord.name',
    label: 'Nome do Locador',
    description: 'Nome completo',
    category: 'locador',
  },
  {
    name: 'landlord.cpf_cnpj',
    label: 'CPF/CNPJ',
    description: 'Documento',
    category: 'locador',
  },
  {
    name: 'landlord.rg',
    label: 'RG',
    description: 'RG do locador',
    category: 'locador',
  },
  {
    name: 'landlord.nationality',
    label: 'Nacionalidade',
    description: 'Nacionalidade',
    category: 'locador',
  },
  {
    name: 'landlord.marital_status',
    label: 'Estado Civil',
    description: 'Estado civil',
    category: 'locador',
  },
  {
    name: 'landlord.phone',
    label: 'Telefone',
    description: 'Telefone',
    category: 'locador',
  },
  {
    name: 'landlord.email',
    label: 'Email',
    description: 'Email',
    category: 'locador',
  },
  {
    name: 'landlord.full_address',
    label: 'Endereço Completo',
    description: 'Endereço formatado',
    category: 'locador',
  },
  // Inquilino
  {
    name: 'tenant.name',
    label: 'Nome do Inquilino',
    description: 'Nome completo',
    category: 'inquilino',
  },
  {
    name: 'tenant.cpf_cnpj',
    label: 'CPF/CNPJ',
    description: 'Documento',
    category: 'inquilino',
  },
  {
    name: 'tenant.rg',
    label: 'RG',
    description: 'RG do inquilino',
    category: 'inquilino',
  },
  {
    name: 'tenant.phone',
    label: 'Telefone',
    description: 'Telefone',
    category: 'inquilino',
  },
  {
    name: 'tenant.marital_status',
    label: 'Estado Civil',
    description: 'Estado civil',
    category: 'inquilino',
  },
  {
    name: 'tenant.profession',
    label: 'Profissão',
    description: 'Profissão',
    category: 'inquilino',
  },
  {
    name: 'tenant.email',
    label: 'Email',
    description: 'Email',
    category: 'inquilino',
  },
  // Apartamento
  {
    name: 'building_number',
    label: 'Número do Prédio',
    description: 'Número',
    category: 'apartamento',
  },
  {
    name: 'apartment_number',
    label: 'Número do Apto',
    description: 'Número',
    category: 'apartamento',
  },
  {
    name: 'building_address',
    label: 'Endereço do Prédio',
    description: 'Endereço',
    category: 'apartamento',
  },
  // Locação
  {
    name: 'rental_value',
    label: 'Valor do Aluguel',
    description: 'Valor numérico',
    category: 'locacao',
  },
  {
    name: 'cleaning_fee',
    label: 'Taxa de Limpeza',
    description: 'Valor da limpeza',
    category: 'locacao',
  },
  {
    name: 'valor_tags',
    label: 'Valor das Tags',
    description: '50 ou 80',
    category: 'locacao',
  },
  {
    name: 'start_date',
    label: 'Data de Início',
    description: 'Data início',
    category: 'locacao',
  },
  {
    name: 'final_date',
    label: 'Data Final',
    description: 'Data término',
    category: 'locacao',
  },
  {
    name: 'validity',
    label: 'Validade',
    description: 'Meses',
    category: 'locacao',
  },
  {
    name: 'lease.due_day',
    label: 'Dia de Vencimento',
    description: 'Dia do mês',
    category: 'locacao',
  },
];

const CATEGORY_LABELS: Record<string, string> = {
  locador: 'Locador',
  inquilino: 'Inquilino',
  apartamento: 'Apartamento',
  locacao: 'Locação',
};

export const VariableInserter: React.FC<VariableInserterProps> = React.memo(
  ({ editor, className }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [selectedFilter, setSelectedFilter] = useState<string>('none');

    const filteredVariables = useMemo(() => {
      return TEMPLATE_VARIABLES.filter((v) => {
        const matchesSearch =
          searchTerm === '' ||
          v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          v.label.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCategory =
          selectedCategory === 'all' || v.category === selectedCategory;
        return matchesSearch && matchesCategory;
      });
    }, [searchTerm, selectedCategory]);

    const groupedVariables = useMemo(() => {
      const groups: Record<string, VariableDefinition[]> = {};
      filteredVariables.forEach((v) => {
        if (!groups[v.category]) groups[v.category] = [];
        groups[v.category].push(v);
      });
      return groups;
    }, [filteredVariables]);

    const handleInsertVariable = useCallback(
      (variable: VariableDefinition) => {
        const filter = selectedFilter !== 'none' ? selectedFilter : undefined;
        editor
          .chain()
          .focus()
          .insertTemplateVariable({ variable: variable.name, filter })
          .run();
        setIsOpen(false);
        setSearchTerm('');
        setSelectedFilter('none');
      },
      [editor, selectedFilter]
    );

    const handleInsertBlock = useCallback(
      (
        blockType: 'if' | 'for' | 'endif' | 'endfor',
        content?: string
      ) => {
        editor
          .chain()
          .focus()
          .insertTemplateBlock({ blockType, content })
          .run();
        setIsOpen(false);
      },
      [editor]
    );

    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className={cn('gap-2', className)}>
            <Code2 className="h-4 w-4" />
            Inserir Variável
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[380px] p-0" align="start">
          <div className="p-3 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 h-8"
              />
            </div>
            <div className="flex gap-2">
              <Select
                value={selectedCategory}
                onValueChange={setSelectedCategory}
              >
                <SelectTrigger className="flex-1 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="locador">Locador</SelectItem>
                  <SelectItem value="inquilino">Inquilino</SelectItem>
                  <SelectItem value="apartamento">Apartamento</SelectItem>
                  <SelectItem value="locacao">Locação</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={selectedFilter}
                onValueChange={setSelectedFilter}
              >
                <SelectTrigger className="flex-1 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sem filtro</SelectItem>
                  <SelectItem value="currency">Moeda</SelectItem>
                  <SelectItem value="extenso">Por Extenso</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Separator />
          <div className="max-h-[250px] overflow-y-auto p-2">
            {Object.entries(groupedVariables).map(([category, variables]) => (
              <div key={category} className="mb-3">
                <div className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase">
                  {CATEGORY_LABELS[category]}
                </div>
                {variables.map((v) => (
                  <button
                    key={v.name}
                    onClick={() => handleInsertVariable(v)}
                    className="w-full text-left px-2 py-1.5 rounded hover:bg-muted"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{v.label}</span>
                      <Badge
                        variant="secondary"
                        className="text-xs font-mono"
                      >{`{{ ${v.name} }}`}</Badge>
                    </div>
                  </button>
                ))}
              </div>
            ))}
            {Object.keys(groupedVariables).length === 0 && (
              <div className="text-center py-4 text-muted-foreground text-sm">
                Nenhuma variável encontrada
              </div>
            )}
          </div>
          <Separator />
          <div className="p-2">
            <div className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase">
              Blocos
            </div>
            <div className="grid grid-cols-2 gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInsertBlock('if', 'condition')}
                className="justify-start text-xs"
              >
                <Plus className="h-3 w-3 mr-1" />
                {'{% if %}'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInsertBlock('endif')}
                className="justify-start text-xs"
              >
                <Plus className="h-3 w-3 mr-1" />
                {'{% endif %}'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInsertBlock('for', 'item in items')}
                className="justify-start text-xs"
              >
                <Plus className="h-3 w-3 mr-1" />
                {'{% for %}'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInsertBlock('endfor')}
                className="justify-start text-xs"
              >
                <Plus className="h-3 w-3 mr-1" />
                {'{% endfor %}'}
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    );
  }
);

VariableInserter.displayName = 'VariableInserter';
