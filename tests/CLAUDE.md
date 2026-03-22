# Tests — pytest + pytest-django

## Estrutura

```
tests/unit/               # Testes isolados (models, serializers, services, validators, auth)
tests/integration/        # Testes de API (views, endpoints)
tests/e2e/                # Fluxos completos (auth, lease workflow, property management)
```

## Padrões

- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.pdf`
- Fixtures: usar `factory-boy` e `model-bakery` — NÃO criar objetos manualmente
- Config: `pytest.ini` com `--reuse-db`, `-n auto` (parallel), `--cov-fail-under=60`
- Coverage atual: 83.86% — manter acima de 60%
- Timeout: 300s para testes lentos (PDF generation)

## Fixtures (conftest.py)

- `configure_test_cache()` — in-memory cache para testes
- `mock_pdf_output_dir`, `mock_chrome_path`, `mock_pdf_generation` — mock PDF sem Chrome
- Sample data: `sample_building_data`, `sample_apartment_data`, `sample_tenant_data`, `sample_lease_data`, etc.
- `freeze_time` — freezegun, `settings_override` — override_settings
- Auto-markers: markers adicionados automaticamente baseado no path e nome do test
