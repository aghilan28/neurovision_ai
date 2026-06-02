# NeuroVision UI Replacement Map

Dependency: `FRONTEND_SURFACE_MAP.md` exists and defines the discovered surface area. This map preserves existing behavior and maps presentation-only replacement work.

## SECTION A - Screen Replacement Matrix

| Existing screen | Purpose | Current UX/layout/components | Current state usage | Current backend usage | Future screen | Future workspace | Future navigation position | Future design-system components | Future layout structure | Constitution alignment |
|---|---|---|---|---|---|---|---|---|---|---|
| Login | authenticate user | static form, alert, prose | session expired, flash | `login` | Login | Identity | anonymous shell | form fields, alert, submit action | centered auth panel within app shell | preserve auth contract |
| Register | create account | static form with role select | flash | `register_user` | Register | Identity | anonymous shell | form fields, role select, submit action | same auth shell | preserve registration flow |
| Dashboard | authenticated landing | kv panels and recent tables | user/session/uploads/workflows/predictions | `list_eeg`, `list_analysis_history` via dashboard refresh | Dashboard | Intelligence Overview | primary authenticated nav | status metrics, recent activity tables | dense operational dashboard | preserve refresh behavior |
| Upload EEG | submit and track recordings | upload form, supported formats, history table | uploads | `upload_eeg`, `list_eeg`, `retrieve_eeg` | Upload Workspace | Data Intake | primary nav after dashboard | file picker, validation/error state, upload history table | intake form plus history/results region | preserve EEG upload workflow |
| Analysis | run backend workflow | stage list and history table | workflows | `start_analysis`, `list_analysis_history`; reports enrich stages | Analysis Workspace | Workflow Execution | primary nav | stepper/timeline, analysis table, action controls | workflow-centered operational layout | preserve backend workflow stages |
| Prediction | review prediction asset | kv panels, probability table, explanation summary | predictions cache | `retrieve_prediction`, `retrieve_confidence`, `retrieve_explanation` | Prediction Workspace | Inference Review | primary nav | confidence gauge, probability table, explanation panel | uncertainty-first prediction review | preserve uncertainty and explanation |
| Reports | view/download reports | report list, validation/audit kv, JSON sections | reports cache | `list_reports` | Reports Workspace | Evidence Center | primary nav | report index, validation badges, audit summary, structured report viewer | report browser with detail region | preserve all report content |
| Clinical System Status | clinical overview | sections, badges, tables, charts | snapshot | none | Clinical Dashboard | Clinical Workstation | clinical nav first | metrics, status badges, charts | clinical operations dashboard | preserve registered artifact source |
| Clinical Cases | case browser/details | overview plus case pages | cases/reviews/findings | none | Cases | Clinical Workstation | clinical nav | table, detail pane, report chips | master/detail workspace | preserve case artifacts |
| Clinical Reviews | review browser/details | tables, assignments, reports | reviews | none | Reviews | Clinical Workstation | clinical nav | table, assignment list, validation badges | master/detail workspace | preserve review artifacts |
| Clinical Findings | finding browser/details | evidence and report sections | findings | none | Findings | Clinical Workstation | clinical nav | evidence table, validation badges | findings detail workspace | preserve finding evidence |
| Clinical Knowledge | knowledge artifacts | kv/table/graph | knowledge | none | Knowledge | Clinical Workstation | clinical nav | graph, relationship table | knowledge graph workspace | preserve registered knowledge |
| Clinical Intelligence | intelligence analytics | metrics/trends/quality charts | intelligence | none | Intelligence | Clinical Workstation | clinical nav | analytics charts, quality badges | analytics workspace | preserve intelligence artifacts |
| Clinical Decision Support | decision bundles | overview/detail pages | decision_support | none | Decision Support | Clinical Workstation | clinical nav | decision cards, evidence tables | decision review workspace | preserve decision bundles |
| Clinical Audit | audit log browser | unified tables/timelines | audit logs | none | Audit | Clinical Workstation | clinical nav | audit timeline, verification badges | chronological audit workspace | preserve immutable audit |
| Clinical Lineage | traceability graph | graph/table/chain coverage | lineage | none | Lineage | Clinical Workstation | clinical nav | lineage graph, chain table | provenance workspace | preserve chain verification |
| Clinical Reports | report center | report index | all reports | none | Reports | Clinical Workstation | clinical nav | report index/detail viewer | evidence center | preserve report inventory |
| Operational System Health | operational health | metrics/status/charts | analytics/meta/audits | none | System Health | Operational Workstation | operational nav first | health metrics, risk chart, status badges | operations command view | preserve registered analytics |
| Operational Events | event stream/taxonomy | tables/charts | events | none | Events | Operational Workstation | operational nav | event stream, taxonomy table | event operations workspace | preserve event registry |
| Operational Timelines | temporal analytics | timeline/evolution views | timelines | none | Timelines | Operational Workstation | operational nav | timeline chart, metrics table | temporal workspace | preserve temporal artifacts |
| Operational Workflows | workflow registry | workflow tables/graphs | workflows | none | Workflows | Operational Workstation | operational nav | workflow graph, bottleneck table | workflow operations workspace | preserve workflow registry |
| Operational Graph | dependency graph | node/edge registry/projection | graph | none | Graph | Operational Workstation | operational nav | graph renderer, registry tables | graph exploration workspace | preserve graph registry |
| Operational Analytics | operational analytics | dimension tables/charts | analytics | none | Analytics | Operational Workstation | operational nav | metric grids, trend/risk charts | analytics workspace | preserve all dimensions |
| Operational Recommendations | operational suggestions | recommendation and escalation tables | recommendations | none | Recommendations | Operational Workstation | operational nav | priority list, evidence table | recommendation review workspace | preserve non-execution constraint |
| Operational Audit | audit browser | audit tables/timelines | audit logs | none | Audit | Operational Workstation | operational nav | audit timeline, integrity badges | audit workspace | preserve immutable audit |
| Operational Lineage | V3 traceability | chain coverage/graphs | lineage | none | Lineage | Operational Workstation | operational nav | provenance graph, chain badges | lineage workspace | preserve Patient-to-Recommendations chain |
| Operational Reports | V3 report center | report index | subsystem reports | none | Reports | Operational Workstation | operational nav | report index/detail | evidence center | preserve report center |
| Autonomous System Health | human oversight landing | overview, monitoring, controls summary | governance/meta/audits/controls | none | System Health | Autonomous Operations | autonomous nav first | health metrics, control summary, alerts | oversight command view | preserve human oversight |
| Autonomous Goals | governed goal entities | shared entity page | goals block | none | Goals | Autonomous Operations | autonomous nav | entity table, lifecycle badges | governed entity workspace | preserve entity contract |
| Autonomous Policies | governed policies | entity page plus constraints | policies block | none | Policies | Autonomous Operations | autonomous nav | constraints table, policy detail | governed entity workspace | preserve constraints |
| Autonomous Plans | governed plans | entity page | plans block | none | Plans | Autonomous Operations | autonomous nav | dependencies, approval badges | governed entity workspace | preserve plan data |
| Autonomous Tasks | governed tasks | entity page | tasks block | none | Tasks | Autonomous Operations | autonomous nav | assignment/dependency tables | governed entity workspace | preserve task data |
| Autonomous Agents | governed agents | entity page plus controls | agents block | none | Agents | Autonomous Operations | autonomous nav | capability table, intervention controls | governed entity workspace | preserve control semantics |
| Autonomous Executions | governed executions | entity page, monitoring, controls | executions/governance | none | Executions | Autonomous Operations | autonomous nav | execution table, control bar, monitoring flags | execution oversight workspace | preserve intervention semantics |
| Autonomous Governance | governance intelligence | approvals/violations/risks/metrics | governance | none | Governance | Autonomous Operations | autonomous nav | risk table, violation list, metric chart | governance workspace | preserve governance intelligence |
| Autonomous Audit | V4 audit browser | unified audit tables | audits | none | Audit | Autonomous Operations | autonomous nav | audit timeline, integrity badges | audit workspace | preserve immutable audit |
| Autonomous Lineage | V4 traceability | graph/table | lineage | none | Lineage | Autonomous Operations | autonomous nav | provenance graph, chain table | lineage workspace | preserve autonomous chain |
| Autonomous Reports | V4 report center | report index | reports blocks | none | Reports | Autonomous Operations | autonomous nav | report index/detail | evidence center | preserve all subsystem reports |
| Offline Upload | research run input overview | artifact metadata/charts | run artifacts | none | Upload | Research App | research workflow nav | artifact summary, EEG metadata, channel layout | research workflow page | preserve registered artifact-only source |
| Offline Dataset Intelligence | dataset profile | stats/class charts | dataset intelligence | none | Dataset Intelligence | Research App | research workflow nav | stat tables, class chart | research analytics page | preserve dataset profile |
| Offline Inference | prediction run review | prediction/calibration/conformal/risk | outputs/reports | none | Inference | Research App | research workflow nav | probability table, calibration/coverage/risk charts | inference review page | preserve uncertainty/risk |
| Offline Benchmark | benchmark evidence | benchmark/split tables | registries/reports | none | Benchmark | Research App | research workflow nav | benchmark comparison, split table | benchmark page | preserve benchmark registry |
| Offline Audit | run audit trail | lineage/audit/version charts | registries/reports/manifest | none | Audit | Research App | research workflow nav | audit timeline, lineage graph | audit page | preserve audit trail |

## SECTION B - Component Replacement Matrix

| Current component | Current responsibility | Replacement strategy | Reuse level | Justification |
|---|---|---|---|---|
| Application `components.nav` | builds authenticated/anonymous nav items | map to new app shell navigation | Partial reuse | preserve nav ids/auth visibility |
| Application `components.alert` | flash/error/warning section | replace visual treatment | Partial reuse | preserve level/message |
| Application `components.kv` | key/value panels | replace with metric/detail components | Partial reuse | data shape is useful; visual shell changes |
| Application `components.table` | tabular sections | replace with design-system data tables | Partial reuse | preserve rows/headers |
| Application `components.form_section` | form section view model | replace with typed form components | Partial reuse | preserve form action/field descriptors |
| Application `components.stages` | workflow stage progress | replace with stepper/timeline | Partial reuse | preserve stage status data |
| Application `components.items_list` | simple list | replace with list/report index | Partial reuse | preserve item sequence |
| Application `components.report_section` | report content section | replace with structured report viewer | Partial reuse | preserve raw JSON/content |
| Application `layouts.render` | complete static HTML and CSS | full visual rewrite | Full rewrite | presentation-only renderer |
| Workstation `kv_panel`, `table`, `badges`, `text`, `metric_row`, `validation_badges` | section view-model components | adapt to design-system panels/tables/badges | Partial reuse | preserve section semantics |
| Workstation chart spec builders | produce deterministic chart specs | reuse as data adapters; replace chart renderer if needed | Partial reuse | specs derive from registered artifacts |
| Workstation HTML report renderers | inline CSS/SVG static documents | full presentation rewrite | Full rewrite | visual layer only |
| Autonomous `InterventionControl` | governed action metadata | preserve and restyle controls | High reuse | business-critical oversight semantics |
| Autonomous `entity_pages` | standard governed entity page builder | reuse as functional adapter or replace with equivalent per-entity view models | Partial reuse | captures repeated entity capability |
| Offline research components | section builders for registered artifacts | adapt to research design system | Partial reuse | artifact-only contract must stay |

## SECTION C - Workflow Preservation Matrix

| Current workflow | Future workspace | Preserve exactly | Presentation replacement allowed |
|---|---|---|---|
| Register/Login/Logout | Identity | gateway operations, validation behavior, session expiration, token non-rendering | form layout, alert styling, auth shell |
| Upload EEG | Upload Workspace | `upload_eeg`, `list_eeg`, `retrieve_eeg`, upload cache, backend-supported formats statement | intake UI, progress/status display |
| Analysis | Analysis Workspace | `start_analysis`, `list_analysis_history`, workflow ids/status/stages, report-based stage enrichment | workflow timeline/stepper visuals |
| Prediction | Prediction Workspace | prediction/confidence/explanation API calls, confidence/calibration always shown, class probabilities | charts, cards, explanation layout |
| Reports | Reports Workspace | `list_reports`, validation/audit summary fields, canonical JSON download content | report browser layout |
| Dashboard | Dashboard Workspace | refresh uploads/history, recent user activity summaries | dashboard composition |
| Clinical workflows | Clinical Workstation | snapshot-only data boundary, all ten nav areas, validation, lineage/audit/report integrity | clinical workspace visuals |
| Operational workflows | Operational Workstation | snapshot-only data boundary, all ten nav areas, non-clinical recommendation framing | operational workspace visuals |
| Autonomous workflows | Autonomous Operations | snapshot-only data boundary, eleven nav areas, governed controls, human oversight semantics | oversight workspace visuals |
| Offline research workflows | Research App | registered run-dir artifact loading, five workflow pages, no backend/domain imports | research report visuals |

## SECTION D - Technical Preservation Matrix

Protected assets:

| Asset | Must remain untouched | Reason |
|---|---|---|
| `BackendGateway.handle(operation, params, token)` contract | yes | canonical frontend/backend boundary |
| Gateway operation constants | yes | maps directly to backend API vocabulary |
| Authentication flow and volatile token handling | yes | security-critical; token excluded from render/snapshot |
| `ApplicationState.snapshot()` shape unless adapter is deliberate | yes | deterministic state source for pages/reports |
| Controllers in `auth`, `uploads`, `workflows`, `predictions`, `reports` | yes | preserve backend integrations |
| `FrontendPrediction` uncertainty/calibration fields | yes | mandated user-facing uncertainty |
| `ReportController.download` canonical JSON behavior | yes | report fidelity |
| Workstation snapshot loaders | yes | no backend/domain coupling in frontend |
| Workstation validation modules | yes | integrity guardrails |
| Workstation navigation area ids and context keys | yes | preserve navigation behavior and state consistency |
| Autonomous intervention controls | yes | governed human oversight |
| Offline `AppState.load(run_dir)` artifact contract | yes | offline artifact-only boundary |

## SECTION E - Reuse Opportunities

- Use current page/workspace builders as a functional inventory and migration checklist.
- Reuse current state and gateway controllers unchanged behind any new UI.
- Reuse chart spec builders as data adapters for richer chart components.
- Reuse validation/reporting modules as acceptance checks after UI replacement.
- Reuse autonomous `InterventionControl` models directly in the future control bar.
- Reuse entity workspace mapping for goals, policies, plans, tasks, agents, and executions to avoid losing repeated governed-entity behavior.

## SECTION F - Rewrite Requirements

- Replace static HTML layout renderers with the new constitution-aligned presentation layer.
- Replace basic section rendering with design-system components.
- Provide browser exposure/routing if future implementation requires an interactive web app; current repository exposes static render functions rather than a routed browser app.
- Preserve all existing page ids, area ids, route intents, gateway operations, context keys, and data loading contracts through adapters.
- Build explicit empty/loading/error states matching current behavior: failed login remains login, unauthorized routes login, prediction/reports can render empty states.

## SECTION G - Implementation Readiness Assessment

Readiness: high for presentation replacement, because existing functionality is already separated into state, gateway/controllers, page/workspace builders, and static renderers.

Primary risk: losing hidden functionality embedded in workspace builders, especially report indexing, lineage/audit verification, workflow stage enrichment, autonomous intervention control metadata, and offline artifact-only loading.

Required implementation guardrails:

- Treat `FRONTEND_SURFACE_MAP.md` as the source of truth for screen coverage.
- Keep backend API calls and snapshot/artifact loaders unchanged.
- Use validation modules before/after replacement to prove no functional loss.
- Do not change workflow behavior while replacing visual components.
