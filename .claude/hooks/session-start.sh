#!/usr/bin/env bash
# SessionStart hook: surface the data-safety invariants that have bitten this repo
# before (real condo/financial data). stdout from SessionStart is added to context.
cat <<'EOF'
[gerenciador_condominios — lembretes de data-safety]
- Backup ANTES de qualquer op destrutiva de banco: `python scripts/backup_db.py`. NUNCA rode flush / sqlflush / reset_db / dbshell destrutivo em dados reais.
- Soft delete: `Model.objects.all()` JÁ exclui registros deletados — use `.with_deleted()` quando precisar incluí-los, `.deleted_only()` para só os deletados.
- Cache Redis invalida automaticamente via signals — ao mudar models/signals, verifique o impacto no cache (core/cache.py, core/signals.py).
EOF
exit 0
