export const meta = {
  name: 'coverage-sweep',
  description: 'Find untested/under-tested business logic across core/services/, respecting the mock policy, and propose pytest cases — prioritizing financial-rule logic (late/tag fees, is_offset, prepaid, salary-offset, cash-flow). Read-only: it proposes tests, it does not write them.',
  phases: [
    { title: 'Discover', detail: 'enumerate core/services modules dynamically (no hardcoded list)' },
    { title: 'Analyze', detail: 'per-service coverage-gap analysis + proposed pytest cases' },
    { title: 'Report', detail: 'prioritized gap report' },
  ],
}

const SERVICES = {
  type: 'object', additionalProperties: false,
  required: ['modules'],
  properties: {
    modules: {
      type: 'array',
      items: { type: 'string' },
      description: 'service module paths under core/services/, excluding __init__.py and base.py',
    },
  },
}

const GAPS = {
  type: 'object', additionalProperties: false,
  required: ['module', 'gaps'],
  properties: {
    module: { type: 'string' },
    gaps: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['symbol', 'risk', 'proposedTest'],
        properties: {
          symbol: { type: 'string', description: 'function/method/branch lacking coverage (file:line)' },
          risk: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] },
          proposedTest: { type: 'string', description: 'concrete pytest case (real test DB + factory-boy; mock only external boundaries)' },
        },
      },
    },
  },
}

phase('Discover')
const discovered = await agent(
  'List the Python service modules under core/services/ (run `ls core/services/*.py`). Exclude __init__.py and base.py. Return the relative paths exactly as found.',
  { label: 'discover-services', phase: 'Discover', agentType: 'Explore', schema: SERVICES },
)
const modules = (discovered?.modules || []).filter(Boolean)
log(`Analyzing ${modules.length} service modules for coverage gaps.`)

phase('Analyze')
const perModule = await pipeline(
  modules,
  (m) => agent(
    `Analyze test coverage for \`${m}\` in gerenciador_condominios (Django + pytest). Read the module and its existing tests (search tests/unit and tests/integration). Identify functions/branches/edge cases NOT covered, focusing on business logic (fee calculations, date logic, cash-flow projections, is_offset/prepaid/salary-offset handling, owner-repasse, IPCA/rent-adjustment, month snapshots). For each gap propose a CONCRETE pytest case that uses the REAL test DB + factory-boy/model-bakery and mocks ONLY external boundaries (never the ORM/services/serializers/library). Rank each gap HIGH/MEDIUM/LOW by financial/data-correctness risk. If the module is already well covered, return an empty gaps array.`,
    { label: `coverage:${m}`, phase: 'Analyze', agentType: 'claude', schema: GAPS },
  ),
)

phase('Report')
const rank = { HIGH: 0, MEDIUM: 1, LOW: 2 }
const allGaps = perModule
  .filter(Boolean)
  .flatMap((r) => (r.gaps || []).map((g) => ({ ...g, module: r.module })))
  .sort((a, b) => (rank[a.risk] ?? 9) - (rank[b.risk] ?? 9))

log(`Found ${allGaps.length} coverage gap(s) across ${modules.length} modules.`)
return { gaps: allGaps }
