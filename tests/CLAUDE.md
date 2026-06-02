# Tests — pytest + pytest-django

## Estrutura

```
tests/unit/               # Testes isolados (models, serializers, services, validators, auth)
tests/integration/        # Testes de API (views, endpoints)
tests/e2e/                # Fluxos completos (auth, lease workflow, property management)
```

## Mock Policy — CRITICAL

IMPORTANT: Mock APENAS external boundaries. NUNCA fazer mock de métodos internos da aplicação ou de bibliotecas.

**Pode mockar:**
- Chrome/PDF (process externo) — usar `mock_pdf_generation` fixture
- File system I/O — quando testes criariam arquivos reais
- HTTP para APIs externas — usar `responses` library
- Tempo — usar `freezegun` (mock do relógio do sistema)

**NUNCA mockar:**
- Django ORM — usar banco real (--reuse-db)
- Services internos (CashFlowService, DashboardService, etc.)
- Serializers — testar com instâncias reais
- Model methods — testar com instâncias reais
- Funções utilitárias internas
- Código de bibliotecas (Django, DRF)

**Por quê:** mockar internals cria testes que passam mesmo com o código real quebrado. Os testes devem exercitar o caminho de código real para pegar bugs reais. Se um teste é difícil de escrever sem mockar internals, isso sinaliza que o código precisa de melhor design (injeção de dependência, funções menores), não de mais mocks.

## Padrões

- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.pdf`
- Fixtures: usar `factory-boy` e `model-bakery` — NÃO criar objetos manualmente
- Config: `pytest.ini` com `--reuse-db`, `-n auto` (parallel), `--cov-fail-under=60`
- Coverage: manter acima de 60%
- Timeout: 300s para testes lentos (PDF generation)

## Fixtures (conftest.py)

- `configure_test_cache()` — in-memory cache para testes
- `mock_pdf_output_dir`, `mock_chrome_path`, `mock_pdf_generation` — mock PDF sem Chrome
- Sample data: `sample_building_data`, `sample_apartment_data`, `sample_tenant_data`, `sample_lease_data`, etc.
- `freeze_time` — freezegun, `settings_override` — override_settings
- Auto-markers: markers adicionados automaticamente baseado no path e nome do test

## Princípios gerais
- Todo bug fix inclui um teste de regressão.
- Testar o comportamento, não a implementação. Não testar código de framework (ORM, render do React).
- Preferir testes de integração que exercitam o stack completo (view → service → model) a unit tests isolados.
- Unit tests são para lógica de negócio complexa em services (cálculo de fees, lógica de datas, projeções de cash flow).
- Frontend (Vitest + MSW): nunca mockar internals do TanStack Query — usar `QueryClient` real com cache curto; sobrescrever handlers MSW por teste com `server.use()`; usar o render custom de `tests/test-utils.tsx`.
