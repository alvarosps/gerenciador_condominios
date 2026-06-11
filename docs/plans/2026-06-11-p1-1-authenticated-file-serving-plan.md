# Plano P1.1 — Servir contratos/comprovantes só autenticado (remover static serve e /download)

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P1 (Hardening de segurança) · **Branch sugerida:** `fix/authenticated-file-serving` · **Depende de:** P0.1

## Objetivo

Fechar o vazamento de PII/LGPD: hoje qualquer anônimo baixa contratos PDF (CPF, RG, endereço, valor de aluguel) e comprovantes PIX porque `condominios_manager/urls.py` serve `^contracts/` e `^media/` via `django.views.static.serve` **sem autenticação** em produção, com nomes de arquivo previsíveis e enumeráveis. Este plano move o download de arquivos para endpoints DRF autenticados que verificam posse (admin OU dono), faz o frontend baixar via proxy same-origin (blob) levando os cookies HttpOnly, e remove as rotas estáticas e o `/download` redirect. O backend passa a devolver um identificador/URL de API, nunca o caminho absoluto do filesystem.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | `^contracts/` e `^media/` servidos por `static.serve` sem auth em prod → enumeração/download anônimo de contratos e comprovantes | `condominios_manager/urls.py:88-97` | Remover as `re_path` estáticas em prod; servir só sob `if settings.DEBUG`; arquivos passam por endpoint DRF autenticado |
| ALTO | `/download` redireciona para a origem do backend fora do proxy → browser segue sem cookies; backend devolve caminho absoluto do filesystem em `generate_contract` | `frontend/app/download/route.ts:1-18`; `core/views.py:392-393` (`pdf_path`), `core/tasks.py:16` (`return str(path)`) | Deletar `download/route.ts`; download via `apiClient` (blob, same-origin); `generate_contract`/`task_status` devolvem só `lease_id` (cliente monta URL de API) |

## Abordagem técnica

Ordem de execução (backend → contrato FE↔API → frontend → remoção das rotas inseguras).

### 1. Backend — endpoint DRF autenticado para contrato (admin OU dono)

`core/viewsets/tenant_views.py` já tem `TenantViewSet.contract` (linhas 132-178): resolve o `pdf_path` a partir de `apt.building.street_number` / `apt.number` / `lease.pk`, valida `lease.contract_generated`, valida `pdf_path.is_file()` e devolve `FileResponse(..., content_type="application/pdf", as_attachment=False)`. Mas é só para o inquilino (`IsTenantUser`) e usa o lease ativo do tenant, não um `lease_id` arbitrário.

Adicionar um `@action(detail=True, methods=["get"], url_path="contract")` na `LeaseViewSet` (`core/views.py`), permissão `[IsAuthenticatedAndActive, CanGenerateContract]` (mesma usada por `generate_contract`, já valida admin OU `responsible_tenant.user == request.user` — `core/permissions.py:146-165`). O método:
1. `lease = self.get_object()` (dispara `has_object_permission` de `CanGenerateContract`).
2. Se `not lease.contract_generated` → `Response({"detail": "Contrato ainda não foi gerado."}, status=404)`.
3. Calcular o caminho **reaproveitando a SSOT** `ContractService.get_contract_relative_path(lease)` (`core/services/contract_service.py:225-248`, devolve `"{building}/contract_apto_{apt}_{lease_id}.pdf"`) e resolver o caminho absoluto via `Path(settings.BASE_DIR) / settings.PDF_OUTPUT_DIR / relative_path`. **Não** duplicar a montagem manual de `f"contract_apto_{apt.number}_{lease.pk}.pdf"`.
4. Se `not pdf_path.is_file()` → `Response({"detail": "Arquivo do contrato não encontrado."}, status=404)`.
5. `return FileResponse(pdf_path.open("rb"), content_type="application/pdf", as_attachment=False, filename=f"contrato_apto_{apt.number}.pdf")`.
   - Tipo de retorno da action: `HttpResponseBase` (FileResponse e Response herdam dele), como em `tenant_views.contract`.

**DRY:** extrair a resolução do caminho absoluto do contrato para um helper estático em `ContractService` — `get_contract_absolute_path(lease) -> Path` — que `tenant_views.TenantViewSet.contract` (linhas 159-165) também passa a usar, removendo a montagem manual duplicada lá. Assim a regra "onde mora o PDF" fica numa só função.

### 2. Backend — endpoint DRF autenticado para arquivo do comprovante (admin OU dono)

O comprovante (`PaymentProof.file`, `FileField(upload_to="payment_proofs/%Y/%m/")`, servido hoje por `^media/`) precisa de dois consumidores autenticados:

- **Admin** (revisão): `AdminProofViewSet` (`core/viewsets/proof_views.py`, `IsAdminUser`, registrado em `admin/proofs`). Adicionar `@action(detail=True, methods=["get"], url_path="file")`:
  1. `proof = PaymentProof.objects.select_related("lease").get(pk=pk)`; `DoesNotExist` → 404 `{"detail": "Comprovante não encontrado."}`.
  2. `if not proof.file: return Response({"detail": "Arquivo não encontrado."}, status=404)`.
  3. `return FileResponse(proof.file.open("rb"), as_attachment=False, filename=Path(proof.file.name).name)` (content-type inferido pelo Django pela extensão; PaymentProofSerializer já restringe upload a jpeg/png/pdf).
- **Dono** (inquilino vendo o próprio comprovante): adicionar `@action(detail=False, methods=["get"], url_path=r"payments/proof/(?P<proof_id>\d+)/file")` em `TenantViewSet` (`core/viewsets/tenant_views.py`), espelhando `payments_proof_status` (linhas 343-381) que já faz `PaymentProof.objects.get(pk=int(proof_id), lease=lease)` — ou seja, o filtro por `lease` do tenant garante a posse. Devolver o mesmo `FileResponse`.

**DRY:** extrair o "abrir o FileField e devolver FileResponse" num pequeno helper de serviço `core/services/file_response_service.py::proof_file_response(proof) -> FileResponse` (fronteira = filesystem), consumido pelas duas actions. Mantém a lógica de posse nos viewsets (HTTP) e o I/O no service.

### 3. Contrato FE↔API — parar de vazar caminho de filesystem

- `core/tasks.py:9-16` (`generate_contract_pdf`) hoje `return str(path)` (caminho absoluto). Manter o retorno do service como está internamente, **mas** a action `generate_contract` (`core/views.py:359-405`) não deve mais expor `pdf_path`. Trocar a resposta de sucesso (linhas 391-395) para:
  ```python
  return Response(
      {"lease_id": lease.id, "message": "Contrato gerado com sucesso!"},
      status=status.HTTP_200_OK,
  )
  ```
  O caminho async (202, linhas 385-389) já devolve só `task_id`/`status` — manter.
- `core/views.py:869-880` (`task_status`): hoje devolve `result.result` (caminho absoluto) em `data["result"]`. Como o cliente só precisa saber que terminou (e qual lease), remover o caminho do payload: ao concluir com sucesso, **não** colocar `result.result`; devolver apenas `status` (e, se necessário para o polling do FE, o `lease_id` — mas o FE já conhece o lease que pediu, então basta `status`). Ajustar para `data["status"]` refletir conclusão sem expor o path. (Verificar consumidores de `task_status` no FE/mobile antes — ver Constraints.)

A nova URL canônica de download do contrato passa a ser `/api/leases/{id}/contract/` (registrada automaticamente pelo router DRF via `@action`). O comprovante: `/api/admin/proofs/{id}/file/` (admin) e `/api/tenant/payments/proof/{id}/file/` (dono).

### 4. Frontend — baixar via proxy same-origin (blob), com cookies

- **Deletar** `frontend/app/download/route.ts` (redirect inseguro).
- `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx`: hoje guarda `pdfPath` (string) e em `handleDownload` (linhas 45-53) reescreve o path e abre `/download?path=...`. Trocar para:
  - O hook `useGenerateContract` passa a devolver `{ lease_id, message }` (sem `pdf_path`). Guardar `leaseId` (ou um boolean `generated`).
  - `handleDownload` faz `apiClient.get(`/leases/${leaseId}/contract/`, { responseType: 'blob' })`, cria `URL.createObjectURL(blob)`, abre/baixa, e revoga a URL. Reusar/criar um util `downloadBlob(blob, filename)` (verificar se já existe em `lib/utils/`; se não, criar um simples).
- `frontend/app/(dashboard)/tenants/_components/contract-view-modal.tsx`: `getContractPdfUrl` (linhas 21-32) hoje monta `${NEXT_PUBLIC_BACKEND_URL}/contracts/.../*.pdf` e injeta no `<iframe src>`. Trocar para buscar o PDF via `apiClient.get('/leases/{id}/contract/', { responseType: 'blob' })` num `useEffect`/hook, gerar `objectURL` e usar como `src` do iframe; revogar no cleanup. (Same-origin via proxy `app/api/[...route]/route.ts` carrega os cookies HttpOnly.)
- `frontend/lib/api/hooks/use-leases.ts:140-161` (`useGenerateContract`): ajustar o tipo de retorno do `apiClient.post` de `{ pdf_path; message }` para `{ lease_id: number; message: string }`.
- Criar hook `useContractPdf(leaseId)` (ou função) em `frontend/lib/api/hooks/use-leases.ts` que faz o GET blob — para reuso entre os dois modais (DRY).
- **Mobile:** o app Expo consome `/api/tenant/contract/` (não muda) — confirmar com grep em `mobile/` que nada depende de `pdf_path`/`task_status.result`.

### 5. Remover as rotas estáticas inseguras

`condominios_manager/urls.py:88-97`: hoje o bloco `urlpatterns += [re_path(^contracts/...), re_path(^media/...)]` roda **sempre**. Mudar para servir **apenas em DEBUG** (dev), removendo de produção:
```python
if settings.DEBUG:
    urlpatterns += [
        re_path(r"^contracts/(?P<path>.*)$", serve,
                {"document_root": str(Path(settings.BASE_DIR) / settings.PDF_OUTPUT_DIR)}),
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
```
Em produção (`DEBUG=False`) essas rotas deixam de existir → 404 para acesso anônimo direto. O acesso legítimo passa 100% pelos endpoints DRF autenticados.

## Arquivos a criar / modificar

**Backend**
- `core/services/contract_service.py` — novo método estático `get_contract_absolute_path(lease) -> Path` (envolve `get_contract_relative_path` + `BASE_DIR/PDF_OUTPUT_DIR`); SSOT do caminho do PDF.
- `core/services/file_response_service.py` — **novo**: `proof_file_response(proof) -> FileResponse` (I/O de filesystem na fronteira).
- `core/views.py` — `LeaseViewSet`: nova `@action contract` (GET, `[IsAuthenticatedAndActive, CanGenerateContract]`); `generate_contract` deixa de devolver `pdf_path` (devolve `lease_id`); `task_status` deixa de devolver `result.result`.
- `core/viewsets/proof_views.py` — `AdminProofViewSet`: nova `@action file` (GET, detail).
- `core/viewsets/tenant_views.py` — `TenantViewSet`: nova `@action payments_proof_file`; `contract` passa a usar `ContractService.get_contract_absolute_path`.
- `core/urls.py` — registrar manualmente `_tenant_proof_file = TenantPortalViewSet.as_view({"get": "payments_proof_file"})` em `/api/tenant/payments/proof/<int:proof_id>/file/` (as actions do `TenantPortalViewSet` são roteadas à mão, linhas 90-134). `admin/proofs` e `leases` são router-registrados (actions aparecem automaticamente).
- `condominios_manager/urls.py` — bloco `^contracts/`/`^media/` movido para dentro de `if settings.DEBUG`.

**Frontend**
- `frontend/app/download/route.ts` — **deletar**.
- `frontend/app/download/__tests__/route.test.ts` — deletar se existir.
- `frontend/lib/api/hooks/use-leases.ts` — `useGenerateContract` retorna `{ lease_id; message }`; novo `useContractPdfBlob`/util de download.
- `frontend/lib/utils/download.ts` — `downloadBlob(blob, filename)` (se ainda não existir).
- `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx` — download via blob/`apiClient`.
- `frontend/app/(dashboard)/tenants/_components/contract-view-modal.tsx` — iframe via blob `objectURL`.
- `frontend/app/(dashboard)/finances/.../*proof*` ou tela de revisão de comprovantes (admin) — se exibir `proof.file` direto via `/media/`, trocar para `/api/admin/proofs/{id}/file/` (grep por `proof.file`/`/media/` no FE).

**Testes**
- Backend: `tests/integration/test_lease_contract_download.py`, `tests/integration/test_proof_file_download.py`, `tests/unit/test_contract_service_paths.py` (helper de caminho), ajuste em `tests/.../test_generate_contract*.py` (response sem `pdf_path`).
- Frontend: `contract-generate-modal.test.tsx`, `contract-view-modal.test.tsx`, `use-leases.test.tsx` (MSW na fronteira HTTP); remover testes de `/download`.

## TDD — cenários de teste

**Backend — `GET /api/leases/{id}/contract/`**
- `test_admin_baixa_contrato_existente_retorna_pdf` — admin, `contract_generated=True`, arquivo existe → 200 `application/pdf`, corpo = bytes do PDF.
- `test_dono_baixa_proprio_contrato` — `responsible_tenant.user` == request.user → 200.
- `test_inquilino_de_outro_lease_recebe_403` — tenant não-dono → 403 (regressão IDOR: prova o bug de enumeração).
- `test_anonimo_recebe_401` — sem auth → 401.
- `test_contrato_nao_gerado_retorna_404` — `contract_generated=False` → 404 `{"detail": ...}`.
- `test_arquivo_ausente_no_disco_retorna_404` — `contract_generated=True` mas PDF não está no disco → 404.
- `test_caminho_resolvido_pela_ssot` (unit) — `get_contract_absolute_path` == `BASE_DIR/PDF_OUTPUT_DIR/get_contract_relative_path`.

**Backend — comprovantes**
- `test_admin_baixa_arquivo_comprovante` — `GET /api/admin/proofs/{id}/file/` admin → 200, bytes.
- `test_nao_admin_recebe_403_no_admin_proof_file` — tenant → 403 (IsAdminUser).
- `test_dono_baixa_proprio_comprovante` — `GET /api/tenant/payments/proof/{id}/file/` com proof do próprio lease → 200.
- `test_inquilino_nao_baixa_comprovante_de_outro_lease` — proof de outro lease → 404 (filtro por lease, regressão IDOR).
- `test_comprovante_sem_arquivo_retorna_404`.

**Backend — não vazar caminho**
- `test_generate_contract_response_nao_contem_pdf_path` — sucesso eager → corpo tem `lease_id`+`message`, **não** tem `pdf_path` (regressão do vazamento de path).
- `test_task_status_nao_expoe_caminho_filesystem` — após task de contrato concluída, `result` não contém `C:\`/`/opt/`/`contracts/`.

**Backend — rotas estáticas removidas em prod**
- `test_contracts_static_route_ausente_quando_debug_false` — com `override_settings(DEBUG=False)` + re-resolução de URLConf, `GET /contracts/x.pdf` resolve 404 (não casa `static.serve`). (Se reverter URLConf for custoso no ambiente de teste, validar via `resolve()` levantando `Resolver404`.)
- `test_contracts_static_route_presente_em_debug` — `DEBUG=True` → rota existe.

**Frontend (vitest + MSW na fronteira HTTP)**
- `contract-generate-modal`: gera contrato → mostra sucesso; "Baixar" chama `GET /leases/:id/contract/` (handler MSW devolve blob), cria objectURL e dispara download; assert que **não** navega para `/download?path=`.
- `contract-view-modal`: com `contract_generated=true`, busca `/leases/:id/contract/` (blob) e seta `iframe src` para o objectURL; assert que **não** monta URL `…/contracts/…pdf`.
- `use-leases.test.tsx`: `useGenerateContract` resolve `{ lease_id, message }` (sem `pdf_path`).
- Remover/atualizar testes de `/download/route`.

## Migrations / dados

N/A — nenhuma mudança de schema (nenhuma tabela nova, nenhum campo). Sem migration, sem RLS, sem backup de banco necessário.

Nota de dados vivos (fora do escopo de código deste plano, registrar no Handoff): os PDFs de contrato e comprovantes que hoje estão no repo/host com nomes previsíveis continuam existindo no disco; este plano só remove o **acesso anônimo** a eles. A avaliação de nomes não-previsíveis (UUID) para **novos** comprovantes/contratos é registrada como melhoria futura (não implementada aqui para não quebrar a SSOT de caminho do contrato que outros lugares assumem) — ver Constraints.

## Constraints (o que NÃO fazer)

- NÃO renomear o esquema de caminho do contrato (`{building}/contract_apto_{apt}_{lease_id}.pdf`) — `ContractService.get_contract_relative_path`, `tenant_views.contract` e os PDFs já no disco dependem dele. UUID para arquivos é melhoria futura, fora deste plano.
- NÃO mexer no motor de PDF (Playwright/Celery), na lógica de geração nem no fluxo de proof upload/review além de adicionar as actions de download.
- NÃO usar `# noqa`/`# type: ignore`/`eslint-disable`/`@ts-ignore`. Sem `from __future__ import annotations`. Tipos importados direto.
- NÃO inline checks de permissão nos viewsets — reusar `CanGenerateContract`/`IsAdminUser`/`IsTenantUser` de `core/permissions.py`. Lógica de posse no viewset (HTTP), I/O de arquivo no service.
- NÃO deixar `^contracts/`/`^media/` acessível em produção "por compat" — remoção completa (só DEBUG). Sem shim de redirect.
- NÃO refatorar o módulo financeiro legado nem o `task_status` além de parar de vazar o path.
- Mensagens de erro de usuário em PT (`{"detail": ...}`), logs em EN.

## Critérios de aceite (binários)

- [ ] `GET /api/leases/{id}/contract/` devolve o PDF para admin e para o dono; 403 para outro inquilino; 401 anônimo; 404 se não gerado/ausente.
- [ ] `GET /api/admin/proofs/{id}/file/` (admin) e `GET /api/tenant/payments/proof/{id}/file/` (dono) devolvem o arquivo; 403/404 nos casos negativos.
- [ ] Em produção (`DEBUG=False`), `GET /contracts/...` e `GET /media/...` retornam 404 (rotas removidas); em DEBUG continuam servindo.
- [ ] Resposta de `generate_contract` e de `task_status` **não** contêm caminho de filesystem nem `pdf_path`.
- [ ] `frontend/app/download/route.ts` removido; nenhuma referência a `/download?path=` no FE.
- [ ] Modais de contrato (gerar e visualizar) baixam/exibem o PDF via `apiClient` (blob, same-origin) com cookies.
- [ ] Suite escopada + regressão dirigida passam; zero erros/warnings em Ruff/mypy/Pyright/ESLint/TS/pytest nos arquivos tocados.

## Gate de verificação

Backend (escopado nos arquivos tocados + regressão dirigida):
```
ruff check core/views.py core/urls.py core/viewsets/proof_views.py core/viewsets/tenant_views.py core/services/contract_service.py core/services/file_response_service.py condominios_manager/urls.py
ruff format --check core/ condominios_manager/
mypy core/
pyright
python -m pytest tests/integration/test_lease_contract_download.py tests/integration/test_proof_file_download.py tests/unit/test_contract_service_paths.py tests/ -k "contract or proof or task_status" -p no:cacheprovider
```
(Suite cheia tem flakiness pré-existente de xdist/Redis — não é bloqueio; rodar escopado + os `-k` de regressão.)

Frontend:
```
cd frontend && npm run lint && npm run type-check && npm run test:unit
```
Zero erros E zero warnings.

## Handoff

**Commit sugerido:**
```
fix(security): serve contracts/proofs only via authenticated DRF endpoints

Remove unauthenticated ^contracts/ and ^media/ static serve in production
and the /download redirect (followed without cookies). Add owner/admin
FileResponse endpoints: GET /api/leases/{id}/contract/,
/api/admin/proofs/{id}/file/, /api/tenant/payments/proof/{id}/file/.
generate_contract/task_status no longer leak the filesystem path; frontend
downloads via same-origin proxy (blob).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

- Atualizar `MEMORY.md` (entrada do achado de file serving) marcando como endereçado.
- **O próximo plano assume:** o caminho canônico de download passa a ser a API DRF; qualquer feature nova que exiba arquivo deve usar esses endpoints, nunca `/contracts/`, `/media/` ou `/download`. A melhoria "nomes UUID para novos comprovantes/contratos" fica registrada como follow-up de hardening (defesa em profundidade contra enumeração mesmo com auth) — não coberta aqui.
- Verificar antes de fechar: grep `mobile/` por `pdf_path`/`task_status` e `frontend/` por `proof.file`/`/media/` para garantir que nenhum consumidor ficou apontando para o caminho antigo.
