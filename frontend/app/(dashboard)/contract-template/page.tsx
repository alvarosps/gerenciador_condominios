'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Save,
  Eye,
  Undo,
  History,
  Info,
  Code,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import Editor from '@monaco-editor/react';
import {
  useContractTemplate,
  useSaveContractTemplate,
  usePreviewContractTemplate,
  useTemplateBackups,
  useRestoreTemplateBackup,
} from '@/lib/api/hooks/use-contract-template';
import { WysiwygEditor } from '@/components/contract-editor';
import { RulesEditor } from '@/components/contract-editor/rules-editor';

type EditorMode = 'wysiwyg' | 'code';

export default function ContractTemplatePage() {
  const [content, setContent] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [activeTab, setActiveTab] = useState('editor');
  const [editorMode, setEditorMode] = useState<EditorMode>('wysiwyg');
  const [isBackupModalOpen, setIsBackupModalOpen] = useState(false);
  const [restoreBackupFilename, setRestoreBackupFilename] = useState<string | null>(null);

  const { data: templateData, isLoading } = useContractTemplate();
  const { data: backups, refetch: refetchBackups } = useTemplateBackups();
  const saveMutation = useSaveContractTemplate();
  const previewMutation = usePreviewContractTemplate();
  const restoreMutation = useRestoreTemplateBackup();

  // Load template content when data is fetched
  useEffect(() => {
    if (templateData?.content) {
      setContent(templateData.content);
    }
  }, [templateData]);

  const handleSave = async () => {
    if (!content || !content.trim()) {
      toast.error('O template não pode estar vazio');
      return;
    }

    try {
      const result = await saveMutation.mutateAsync(content);
      toast.success(result.message);
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'response' in error
        && error.response && typeof error.response === 'object' && 'data' in error.response
        && error.response.data && typeof error.response.data === 'object' && 'error' in error.response.data
        && typeof error.response.data.error === 'string'
        ? error.response.data.error
        : 'Erro ao salvar template';
      toast.error(errorMessage);
    }
  };

  const handlePreview = async () => {
    if (!content || !content.trim()) {
      toast.error('O template não pode estar vazio');
      return;
    }

    try {
      const result = await previewMutation.mutateAsync({ content });
      setPreviewHtml(result.html);
      setActiveTab('preview');
      toast.success('Preview gerado com sucesso!');
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'response' in error
        && error.response && typeof error.response === 'object' && 'data' in error.response
        && error.response.data && typeof error.response.data === 'object' && 'error' in error.response.data
        && typeof error.response.data.error === 'string'
        ? error.response.data.error
        : 'Erro ao gerar preview. Verifique se há locações cadastradas.';
      toast.error(errorMessage);
    }
  };

  const handleRevert = () => {
    if (templateData?.content) {
      setContent(templateData.content);
      toast.info('Alterações revertidas');
    }
  };

  const handleRestoreBackup = async () => {
    if (!restoreBackupFilename) return;

    try {
      const result = await restoreMutation.mutateAsync(restoreBackupFilename);
      toast.success(result.message);
      setIsBackupModalOpen(false);
      setRestoreBackupFilename(null);
      refetchBackups();
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'response' in error
        && error.response && typeof error.response === 'object' && 'data' in error.response
        && error.response.data && typeof error.response.data === 'object' && 'error' in error.response.data
        && typeof error.response.data.error === 'string'
        ? error.response.data.error
        : 'Erro ao restaurar backup';
      toast.error(errorMessage);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const hasChanges = content !== templateData?.content;

  return (
    <div className="h-full">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <span>Editor de Template de Contrato</span>
              {hasChanges && (
                <Badge variant="secondary" className="bg-orange-100 text-orange-800 hover:bg-orange-200">
                  Alterações não salvas
                </Badge>
              )}
            </CardTitle>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditorMode((prev) => (prev === 'wysiwyg' ? 'code' : 'wysiwyg'))}
              >
                {editorMode === 'wysiwyg' ? (
                  <>
                    <Code className="h-4 w-4 mr-2" />
                    Código
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Visual
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsBackupModalOpen(true)}
              >
                <History className="h-4 w-4 mr-2" />
                Backups
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handlePreview}
                disabled={previewMutation.isPending}
              >
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRevert}
                disabled={!hasChanges}
              >
                <Undo className="h-4 w-4 mr-2" />
                Reverter
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={saveMutation.isPending || !hasChanges}
              >
                <Save className="h-4 w-4 mr-2" />
                Salvar
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Alert className="mb-4">
            <Info className="h-4 w-4" />
            <AlertDescription className="ml-2">
              <p className="font-medium mb-2">Variáveis Disponíveis</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <code className="bg-gray-100 px-1 py-0.5 rounded">{'{{ tenant.name }}'}</code> - Nome do inquilino
                </div>
                <div>
                  <code className="bg-gray-100 px-1 py-0.5 rounded">{'{{ building_number }}'}</code> - Número do prédio
                </div>
                <div>
                  <code className="bg-gray-100 px-1 py-0.5 rounded">{'{{ apartment_number }}'}</code> - Número do apartamento
                </div>
                <div>
                  <code className="bg-gray-100 px-1 py-0.5 rounded">{'{{ rental_value | currency }}'}</code> - Valor em moeda
                </div>
                <div>
                  <code className="bg-gray-100 px-1 py-0.5 rounded">{'{{ rental_value | extenso }}'}</code> - Valor por extenso
                </div>
                <div>
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => setActiveTab('variables')}
                    className="h-auto p-0"
                  >
                    <Info className="h-3 w-3 mr-1" />
                    Ver todas as variáveis
                  </Button>
                </div>
              </div>
            </AlertDescription>
          </Alert>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="editor">Editor</TabsTrigger>
              <TabsTrigger value="rules">Regras</TabsTrigger>
              <TabsTrigger value="preview">Preview</TabsTrigger>
              <TabsTrigger value="variables">Variáveis</TabsTrigger>
            </TabsList>

            <TabsContent value="editor" className="mt-0">
              <div style={{ height: '65vh' }}>
                {isLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-muted-foreground">Carregando template...</p>
                  </div>
                ) : editorMode === 'wysiwyg' ? (
                  <WysiwygEditor
                    value={content}
                    onChange={setContent}
                    className="h-full"
                  />
                ) : (
                  <Editor
                    height="100%"
                    language="html"
                    value={content}
                    onChange={(value) => setContent(value || '')}
                    theme="vs-dark"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      wordWrap: 'on',
                      formatOnPaste: true,
                      formatOnType: true,
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                    }}
                  />
                )}
              </div>
            </TabsContent>

            <TabsContent value="rules" className="mt-0">
              <div style={{ height: '65vh', overflow: 'auto' }}>
                <RulesEditor />
              </div>
            </TabsContent>

            <TabsContent value="preview" className="mt-0">
              <div
                style={{ height: '65vh', overflow: 'auto' }}
                className="border rounded p-4 bg-white"
              >
                {previewHtml ? (
                  <iframe
                    srcDoc={previewHtml}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Preview"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <Eye className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">
                      Clique em &quot;Preview&quot; para visualizar o template
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="variables" className="mt-0">
              <div style={{ height: '65vh', overflow: 'auto' }} className="p-4">
                <h3 className="text-lg font-semibold mb-3">Variáveis do Locador</h3>
                <ul className="list-disc pl-6 mb-6 space-y-1">
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.name }}'}</code> - Nome do locador</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.cpf_cnpj }}'}</code> - CPF ou CNPJ</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.rg }}'}</code> - RG</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.nationality }}'}</code> - Nacionalidade</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.marital_status }}'}</code> - Estado civil</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.phone }}'}</code> - Telefone</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.email }}'}</code> - Email</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.street }}'}</code> - Rua</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.street_number }}'}</code> - Número</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.neighborhood }}'}</code> - Bairro</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.city }}'}</code> - Cidade</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.state }}'}</code> - Estado</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.zip_code }}'}</code> - CEP</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.country }}'}</code> - País</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ landlord.full_address }}'}</code> - Endereço completo</li>
                </ul>

                <h3 className="text-lg font-semibold mb-3">Variáveis de Inquilino</h3>
                <ul className="list-disc pl-6 mb-6 space-y-1">
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.name }}'}</code> - Nome completo</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.cpf_cnpj }}'}</code> - CPF ou CNPJ</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.rg }}'}</code> - RG</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.phone }}'}</code> - Telefone</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.marital_status }}'}</code> - Estado civil</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.profession }}'}</code> - Profissão</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ tenant.email }}'}</code> - Email</li>
                </ul>

                <h3 className="text-lg font-semibold mb-3">Variáveis de Apartamento</h3>
                <ul className="list-disc pl-6 mb-6 space-y-1">
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ building_number }}'}</code> - Número do prédio</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ apartment_number }}'}</code> - Número do apartamento</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ building_address }}'}</code> - Endereço do prédio</li>
                </ul>

                <h3 className="text-lg font-semibold mb-3">Variáveis de Locação</h3>
                <ul className="list-disc pl-6 mb-6 space-y-1">
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ validity }}'}</code> - Validade em meses</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ start_date }}'}</code> - Data de início</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ final_date }}'}</code> - Data final</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ next_month_date }}'}</code> - Data do próximo mês</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ rental_value }}'}</code> - Valor do aluguel (número)</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ cleaning_fee }}'}</code> - Taxa de limpeza</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ valor_tags }}'}</code> - Valor das tags (50 ou 80)</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ lease.due_day }}'}</code> - Dia de vencimento</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ lease.number_of_tenants }}'}</code> - Número de inquilinos</li>
                </ul>

                <h3 className="text-lg font-semibold mb-3">Filtros Jinja2</h3>
                <ul className="list-disc pl-6 mb-6 space-y-1">
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ rental_value | currency }}'}</code> - Formata como moeda (R$ 1.500,00)</li>
                  <li><code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{'{{ rental_value | extenso }}'}</code> - Escreve por extenso (mil e quinhentos reais)</li>
                </ul>

                <h3 className="text-lg font-semibold mb-3">Loops (Móveis)</h3>
                <pre className="bg-gray-100 p-4 rounded mb-6 text-sm overflow-x-auto">
{`{% for furniture in furnitures %}
  <li>{{ furniture.name }}</li>
{% endfor %}`}
                </pre>

                <h3 className="text-lg font-semibold mb-3">Condicionais</h3>
                <pre className="bg-gray-100 p-4 rounded text-sm overflow-x-auto">
{`{% if tenant.deposit_amount and tenant.deposit_amount > 0 %}
  <p>Caução: {{ tenant.deposit_amount | currency }}</p>
{% endif %}`}
                </pre>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Backups Modal */}
      <Dialog open={isBackupModalOpen} onOpenChange={setIsBackupModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Backups do Template</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {backups && backups.length > 0 ? (
              backups.map((backup) => (
                <div
                  key={backup.filename}
                  className={`flex items-center justify-between p-3 border rounded hover:bg-gray-50 ${
                    backup.is_default ? 'border-blue-300 bg-blue-50' : ''
                  }`}
                >
                  <div className="flex-1">
                    <div className="font-medium text-sm flex items-center gap-2">
                      {backup.is_default ? (
                        <>
                          <Badge variant="default" className="bg-blue-600">
                            Template Original
                          </Badge>
                          <span className="text-muted-foreground">
                            {backup.filename}
                          </span>
                        </>
                      ) : (
                        backup.filename
                      )}
                    </div>
                    <div className="text-xs text-gray-600">
                      Tamanho: {formatBytes(backup.size)}
                    </div>
                    <div className="text-xs text-gray-500">
                      Criado em: {new Date(backup.created_at).toLocaleString('pt-BR')}
                    </div>
                  </div>
                  <Button
                    variant={backup.is_default ? 'default' : 'link'}
                    onClick={() => setRestoreBackupFilename(backup.filename)}
                    disabled={restoreMutation.isPending}
                  >
                    Restaurar
                  </Button>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Nenhum backup encontrado
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <AlertDialog
        open={!!restoreBackupFilename}
        onOpenChange={(open) => !open && setRestoreBackupFilename(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restaurar Backup</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja restaurar o backup &quot;{restoreBackupFilename}&quot;? O template atual será substituído.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRestoreBackup}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Sim, Restaurar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
