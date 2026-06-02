# NeuroVision Frontend Surface Map

Evidence base: recursive inspection of `frontend/application_frontend/`, `frontend/clinical_workstation/`, `frontend/operational_workstation/`, `frontend/autonomous_operations_workstation/`, and `frontend/offline_research_app/`.

## SECTION A - Frontend Architecture Overview

### Application Frontend

Path: `frontend/application_frontend/`

Purpose: a deterministic static-HTML product frontend over the backend v1 API. It owns presentation state, navigation state, forms, controllers, page builders, and rendering. It does not import backend domain code.

Primary composition:

| Module | Purpose | Inputs | Outputs | Dependencies | Backend integration | Render responsibility | User-facing capabilities |
|---|---|---|---|---|---|---|---|
| `application.py` | `FrontendApp` controller tying state, gateway, controllers, pages, and layout renderer | user action arguments, `BackendGateway` | `ActionResult`, complete HTML strings | auth/uploads/workflows/predictions/reports controllers, pages, layout renderer | all runtime backend calls occur through injected gateway controllers | exposes `render_login`, `render_register`, `render_dashboard`, `render_upload`, `render_analysis`, `render_prediction`, `render_reports`, `render_current` | register, login, logout, dashboard, upload, analysis, prediction, reports |
| `gateway.py` | abstract backend contract | operation string, params dict, bearer token | backend-shaped response dict | `CONSUMES_API_VERSION` | canonical API operation vocabulary | none | defines API boundary |
| `actions.py` | action result normalization | controller response data | `ActionResult` | dataclasses | maps API errors to frontend result | none | user-facing flash/page routing metadata |
| `state/__init__.py` | deterministic UI state | backend response projections, navigation commands | secret-free snapshot, signature | frontend domain models, fingerprint util | stores token only in volatile `_token` | supplies page snapshots | auth/session state, caches uploads/workflows/predictions/reports |
| `auth/__init__.py` | auth controller | username/password/role | `ActionResult`, state updates | forms, gateway, state, domain | `register_user`, `login`, `logout` | supplies form descriptors | register, login, logout, session expiration |
| `uploads/__init__.py` | upload controller | filename/content/upload id | `ActionResult`, upload cache | forms, gateway, state, domain | `upload_eeg`, `list_eeg`, `retrieve_eeg` | supplies upload form | upload EEG, list history, view upload |
| `workflows/__init__.py` | analysis workflow controller | upload id | `ActionResult`, workflow cache, stage view | forms, gateway, state, domain | `start_analysis`, `list_analysis_history` | supplies analysis form/stage progress | start analysis, see backend workflow stages/history |
| `predictions/__init__.py` | prediction display controller | analysis id | cached prediction and normalized view | gateway, state, domain | `retrieve_prediction`, `retrieve_confidence`, `retrieve_explanation` | builds prediction view model | prediction label, class probabilities, confidence, calibration, explanation |
| `reports/__init__.py` | report display/download controller | analysis id/report name | cached reports and report view | gateway, canonical JSON | `list_reports` | builds report sections | report list, validation/audit summary, JSON download content |
| `pages/__init__.py` | page view-model builders | state snapshot, field errors, prediction/report views | page dicts | components, forms | none direct | page composition | login, register, dashboard, upload, analysis, prediction, reports |
| `layouts/__init__.py` | static HTML renderer | page dict | complete deterministic HTML document | `esc`, version | none | renders sections, forms, nav, alerts, CSS | browser-displayable pages |
| `forms/__init__.py` | form descriptors and UX validation | field values | `FieldErrors`, form dicts | dataclasses | action strings match gateway operations | form metadata for renderer | login/register/upload/analysis forms |
| `components/__init__.py` | reusable page fragments | plain values/tables/forms | section dicts/nav dicts | none | none | section view-model fragments | nav, alerts, kv panels, tables, stages, lists, reports, prose |
| `validation/__init__.py` | frontend integrity validator | app/state snapshot | validation report | workflow stage contract | checks operation/state/render consistency, no API calls | none | validates frontend flow/state/UI integrity |
| `reporting.py` | frontend meta-reports | app/state/validation | deterministic reports | gateway op list, fingerprint | documents integration coverage | none | validation/workflow/state/integration reports |
| `domain.py` | presentation projections of backend responses | backend response bodies | typed frontend domain dataclasses | version | response shape projection only | serializable state | user/session/upload/workflow/prediction/report models |
| `util.py` | deterministic helpers | Python values/HTML text | canonical JSON, fingerprints, escaped text | stdlib | none | escaping/fingerprint support | support only |

### Clinical Workstation

Path: `frontend/clinical_workstation/`

Purpose: static, deterministic clinical workstation over a Version 2 snapshot written by `scripts.build_workstation_snapshot`. It imports no backend domain code and reads registered artifacts with stdlib JSON.

Primary architecture: `state.WorkstationState.load/from_snapshot` -> `application.build_workstation_view` -> `navigation.build_areas` -> workspace `*_pages(state)` builders -> `reports.render_workstation_html`.

Primary areas in `navigation/navigation.py`: System Status, Cases, Reviews, Findings, Knowledge, Intelligence, Decision Support, Audit, Lineage, Reports.

### Operational Workstation

Path: `frontend/operational_workstation/`

Purpose: static, deterministic operational workstation over a Version 3 snapshot written by `scripts.build_operational_workstation_snapshot`. It presents registered operational artifacts only.

Primary architecture: `state.WorkstationState.load/from_snapshot` -> `application.build_workstation_view` -> `navigation.build_areas` -> workspace `*_pages(state)` builders -> `reports.render_workstation_html`.

Primary areas in `navigation/navigation.py`: System Health, Events, Timelines, Workflows, Graph, Analytics, Recommendations, Audit, Lineage, Reports.

### Autonomous Operations Workstation

Path: `frontend/autonomous_operations_workstation/`

Purpose: static, deterministic human-oversight workstation over a Version 4 autonomous operations snapshot written by `scripts.build_autonomous_operations_workstation_snapshot`.

Primary architecture: `state.WorkstationState.load/from_snapshot` -> `application.build_workstation_view` with controls -> `navigation.build_areas` -> workspace page builders -> `reports.render_workstation_html`.

Primary areas in `navigation/navigation.py`: System Health, Goals, Policies, Plans, Tasks, Agents, Executions, Governance, Audit, Lineage, Reports.

### Offline Research App

Path: `frontend/offline_research_app/`

Purpose: offline static research application over a registered inference run directory. It reads `inference_index.json` plus registered output/report/registry artifacts and renders a deterministic HTML report.

Primary architecture: `state.AppState.load(run_dir)` -> `pages.build_app_view` -> `workflows.all_workflows` -> `reports.render_app_html`.

Primary workflows in `workflows/workflows.py`: Upload, Dataset Intelligence, Inference, Benchmark, Audit.

## SECTION B - Screen Inventory

| Screen | Renderer | Route intent | Current functionality | State dependencies | Backend dependencies | Completeness | Reuse potential |
|---|---|---|---|---|---|---|---|
| Login | `FrontendApp.render_login` -> `pages.login_page` -> `layouts.render` | `login`; anonymous entry; session-expired fallback | login form, session-expired alert, register pointer | `current_page`, `session_expired`, `flash` | `AuthController.login` -> `login` | Complete static HTML | preserve auth action/state; replace presentation |
| Register | `FrontendApp.render_register` -> `pages.register_page` | `register`; anonymous account creation | registration form with role selector | `flash`, navigation | `AuthController.register` -> `register_user` | Complete static HTML | preserve form contract and controller |
| Dashboard | `FrontendApp.render_dashboard` -> `pages.dashboard_page` | `dashboard`; authenticated landing | user summary, system status, recent uploads/analyses/predictions | user, session, uploads, workflows, predictions | `dashboard()` refreshes uploads and analysis history through gateway | Complete static HTML | preserve data panels; redesign shell/cards only |
| Upload EEG | `FrontendApp.render_upload` -> `pages.upload_page` | `upload` | upload form, supported formats copy, upload history | uploads cache, flash | `upload_eeg`, `list_eeg`, `retrieve_eeg` | Complete static HTML | preserve upload form/action/history |
| Analysis | `FrontendApp.render_analysis` -> `pages.analysis_page` | `analysis` | workflow progress for latest workflow, analysis history | workflows cache, optional stage view | `start_analysis`, `list_analysis_history`, reports used to enrich stages | Complete static HTML | preserve workflow stage semantics |
| Prediction | `FrontendApp.render_prediction` -> `pages.prediction_page` | `prediction` | selected/latest prediction, confidence, calibration, probabilities, explanation summary, empty state | predictions cache | `retrieve_prediction`, `retrieve_confidence`, `retrieve_explanation`; auto-loaded after analysis | Complete static HTML when prediction exists; empty state otherwise | preserve uncertainty display |
| Reports | `FrontendApp.render_reports` -> `pages.reports_page` | `reports` | report list, validation summary, audit summary, report JSON content | reports cache | `list_reports` | Complete static HTML when reports exist; empty state otherwise | preserve report names/content/download path |
| Clinical System Status | `clinical_workstation.workspaces.dashboards.dashboard_pages` | `dashboard` area | cross-subsystem status, counts, lineage/system metrics | clinical snapshot | snapshot only | Complete static HTML via workstation renderer | preserve as clinical dashboard workspace |
| Clinical Cases | `case_pages` | `cases` area | overview plus per-case details, reports, related reviews/findings | cases, reviews, findings, registries | snapshot only | Complete | preserve case detail pages |
| Clinical Reviews | `review_pages` | `reviews` area | review overview/details, assignments/reports | reviews snapshot | snapshot only | Complete | preserve review artifact browser |
| Clinical Findings | `finding_pages` | `findings` area | finding overview/details/evidence/reports | findings snapshot | snapshot only | Complete | preserve evidence/report model |
| Clinical Knowledge | `knowledge_pages` | `knowledge` area | knowledge artifacts and relationship visualization | knowledge snapshot | snapshot only | Complete | preserve knowledge graph data |
| Clinical Intelligence | `intelligence_pages` | `intelligence` area | analytics/trend/quality artifacts | intelligence snapshot | snapshot only | Complete | preserve intelligence summaries |
| Clinical Decision Support | `decision_pages` | `decision` area | decision support overview and bundle details | decision_support snapshot | snapshot only | Complete | preserve decision bundle display |
| Clinical Audit | `audit_pages` | `audit` area | unified immutable audit log browser | all clinical audit logs | snapshot only | Complete | preserve audit integrity presentation |
| Clinical Lineage | `lineage_pages` | `lineage` area | provenance graph and representative chain | lineage, representative_chain | snapshot only | Complete | preserve chain coverage |
| Clinical Reports | `report_pages` | `reports` area | report center indexing registered reports | all clinical reports | snapshot only | Complete | preserve report index |
| Operational System Health | `system_health_pages` | `system-health` area | health/risk headline and subsystem status | analytics/meta/audits | snapshot only | Complete | preserve operational landing |
| Operational Events | `event_pages` | `events` area | event registry, taxonomy, relationships | events block | snapshot only | Complete | preserve event browser |
| Operational Timelines | `timeline_pages` | `timelines` area | timeline/history/evolution/temporal analytics | timelines block | snapshot only | Complete | preserve temporal analytics |
| Operational Workflows | `workflow_pages` | `workflows` area | registry, transitions, dependencies, bottlenecks, efficiency | workflows block | snapshot only | Complete | preserve workflow detail |
| Operational Graph | `graph_pages` | `graph` area | node/edge registry and projection | graph block | snapshot only | Complete | preserve graph registry |
| Operational Analytics | `analytics_pages` | `analytics` area | metrics, health, performance, quality, trend, risk | analytics blocks | snapshot only | Complete | preserve analytics dimensions |
| Operational Recommendations | `recommendation_pages` | `recommendations` area | guidance/optimization/escalation suggestions and human-review framing | recommendations block | snapshot only | Complete | preserve non-clinical/non-execution constraints |
| Operational Audit | `audit_pages` | `audit` area | unified audit log browser | audit logs across subsystems | snapshot only | Complete | preserve audit chronology |
| Operational Lineage | `lineage_pages` | `lineage` area | Patient-to-Recommendations provenance ordering | lineage, representative_chain | snapshot only | Complete | preserve chain ordering |
| Operational Reports | `report_pages` | `reports` area | report center for V3 subsystems | reports in events/timelines/workflows/graph/analytics/recommendations | snapshot only | Complete | preserve report inventory |
| Autonomous System Health | `system_health_pages` | `system-health` area | governed platform overview, human oversight, controls summary | meta, audit logs, governance, controls | snapshot only | Complete | preserve oversight landing |
| Autonomous Goals | `goal_pages` | `goals` area | governed entity workspace via shared `entity_pages` | goals block | snapshot only | Complete | preserve entity registry/lifecycle/governance/audit/lineage/reports |
| Autonomous Policies | `policy_pages` | `policies` area | policy entity workspace plus constraints details | policies block | snapshot only | Complete | preserve policy constraints |
| Autonomous Plans | `plan_pages` | `plans` area | plan entity workspace | plans block | snapshot only | Complete | preserve dependency/approval data |
| Autonomous Tasks | `task_pages` | `tasks` area | task entity workspace | tasks block | snapshot only | Complete | preserve task assignments/dependencies |
| Autonomous Agents | `agent_pages` | `agents` area | agent entity workspace plus governed controls | agents block | snapshot only | Complete | preserve agent controls |
| Autonomous Executions | `execution_pages` | `executions` area | execution entity workspace, monitoring, governed controls | executions/governance monitoring | snapshot only | Complete | preserve intervention semantics |
| Autonomous Governance | `governance_pages` | `governance` area | approvals, violations, escalations, risks, metrics | governance block | snapshot only | Complete | preserve governance intelligence |
| Autonomous Audit | `audit_pages` | `audit` area | unified V4 immutable audit log browser | entity/governance audit logs | snapshot only | Complete | preserve audit integrity |
| Autonomous Lineage | `lineage_pages` | `lineage` area | end-to-end traceability explorer | lineage, representative_chain | snapshot only | Complete | preserve autonomous lineage |
| Autonomous Reports | `report_pages` | `reports` area | report center across Version 4 subsystems | reports_blocks | snapshot only | Complete | preserve report center |
| Offline Upload Workflow | `upload_workflow` | first research workflow page | registered artifact/input overview and EEG metadata/channel layout | run directory artifacts | none; registered files only | Complete | preserve offline workflow |
| Offline Dataset Intelligence | `dataset_intelligence_workflow` | research workflow page | dataset profile/statistics/classes | dataset_intelligence, outputs/reports | none | Complete | preserve profile display |
| Offline Inference | `inference_workflow` | research workflow page | prediction/probability/calibration/conformal/coverage/risk preview | outputs/reports/index | none | Complete | preserve uncertainty/risk data |
| Offline Benchmark | `benchmark_workflow` | research workflow page | benchmark and patient-disjoint split details | registries/reports | none | Complete | preserve benchmark evidence |
| Offline Audit | `audit_workflow` | research workflow page | lineage, audit, version history | registries/reports/manifest | none | Complete | preserve audit trail |

## SECTION C - Rendering Inventory

| Renderer | Output | HTML generation path | Layout/page composition path | State dependencies | Render dependencies | Complete HTML today? | Evidence |
|---|---|---|---|---|---|---|---|
| `layouts.render(page)` | complete `<!doctype html>` document with inline CSS | `_render_section`, `_render_form`, nav/flash/sections | `pages.*_page` returns page dict | page dict from `ApplicationState.snapshot` | `util.esc`, version | YES | `layouts/__init__.py` returns full document string |
| `FrontendApp.render_login` | login HTML | `pages.login_page` -> `layouts.render` | form section and optional alert | state snapshot | pages/layouts | YES | method calls `render_html(...)` |
| `FrontendApp.render_register` | register HTML | `pages.register_page` -> `layouts.render` | form section | state snapshot | pages/layouts | YES | method calls `render_html(...)` |
| `FrontendApp.render_dashboard` | dashboard HTML | `pages.dashboard_page` -> `layouts.render` | kv/tables | state snapshot | pages/layouts/components | YES | method calls `render_html(...)` |
| `FrontendApp.render_upload` | upload HTML | `pages.upload_page` -> `layouts.render` | upload form/history | state snapshot | pages/layouts/components | YES | method calls `render_html(...)` |
| `FrontendApp.render_analysis` | analysis HTML | `pages.analysis_page` -> `layouts.render` | stage view/history table | workflows cache | `AnalysisController.stage_progress` | YES | method builds optional stage view then renders |
| `FrontendApp.render_prediction` | prediction HTML | `pages.prediction_page` -> `layouts.render` | prediction view or empty state | predictions cache | `build_prediction_view` | YES | empty-state page when no prediction |
| `FrontendApp.render_reports` | reports HTML | `pages.reports_page` -> `layouts.render` | report list/summary/content | reports cache | `build_reports_view` | YES | empty-state page when no reports |
| `FrontendApp.render_current` | current page HTML | dispatch map to renderers | current page route | `current_page` | all app renderers | YES | fallback to login |
| `clinical_workstation.reports.render_workstation_html(view)` | complete workstation HTML | inline CSS/SVG plus areas/pages/sections | `build_workstation_view` -> `build_areas` -> workspace pages | `WorkstationView` | chart render helpers | YES | renderer returns `<!doctype html>` |
| `clinical_workstation.reports.render_from_snapshot_path(path)` | complete HTML from snapshot path | loads `WorkstationState` then render | `WorkstationState.load` -> `build_workstation_view` | snapshot JSON | stdlib JSON | YES | direct wrapper |
| `clinical_workstation.reports.write_workstation_html(path, out)` | writes HTML file | `render_from_snapshot_path` | same as above | snapshot path | os/file I/O | YES | writes default `clinical_workstation.html` |
| `operational_workstation.reports.render_workstation_html(view)` | complete workstation HTML | inline CSS/SVG plus areas/pages/sections | `build_workstation_view` -> `build_areas` -> workspace pages | `WorkstationView` | chart render helpers | YES | renderer returns `<!doctype html>` |
| `operational_workstation.reports.render_from_snapshot_path(path)` | complete HTML from snapshot path | loads `WorkstationState` then render | `WorkstationState.load` -> `build_workstation_view` | snapshot JSON | stdlib JSON | YES | direct wrapper |
| `operational_workstation.reports.write_workstation_html(path, out)` | writes HTML file | `render_from_snapshot_path` | same as above | snapshot path | os/file I/O | YES | writes default `operational_workstation.html` |
| `autonomous_operations_workstation.reports.render_workstation_html(view)` | complete workstation HTML | static workstation renderer package exported from `reports` | `build_workstation_view` -> `build_areas` -> workspace pages/controls | `WorkstationView` | schemas/components/controls | YES | exported in package `__init__.py` and application builder |
| `offline_research_app.reports.render_app_html(view)` | complete offline app HTML | inline CSS/SVG | `build_app_view` -> `all_workflows` | `AppView` | chart render helpers | YES | renderer returns full HTML document |
| `offline_research_app.reports.render_from_run_dir(dir)` | complete HTML from run dir | loads `AppState` then render | `AppState.load` -> `build_app_view` | run directory files | stdlib JSON/os | YES | direct wrapper |
| `offline_research_app.reports.write_app_html(dir, path)` | writes `research_app.html` | `render_from_run_dir` | same as above | run directory | os/file I/O | YES | writes default `research_app.html` |

## SECTION D - Navigation Inventory

### Current Navigation Graph

Application frontend navigation is state-string based. `components.NAV_AREAS` exposes Dashboard, Upload, Analysis, Prediction, and Reports only when authenticated, plus Login/Register for anonymous users. `FrontendApp._handle` navigates to the `ActionResult.page`. Unauthorized responses clear auth state and route to login.

Clinical, operational, and autonomous workstations build all primary areas every render through `navigation.build_areas(state)`. Each area receives `context_snapshot()` so selections are preserved in a presentation-only context dictionary.

Offline research app navigation is static page order in `all_workflows(state)`: Upload -> Dataset Intelligence -> Inference -> Benchmark -> Audit.

### Anonymous User Flow

`login` -> `AuthController.login` -> `dashboard` on success; `register` -> `AuthController.register` -> `login` on successful registration. Failed login stays on `login`. Session expiration sets `session_expired=True` and routes to `login`.

### Authenticated User Flow

After `sign_in`, `current_page` becomes `dashboard`. The authenticated nav can move across Dashboard, Upload, Analysis, Prediction, and Reports. `logout` calls gateway logout when authenticated, clears state, and returns to login.

### Upload Flow

`render_upload` displays `UPLOAD_FORM`. `FrontendApp.upload(filename, content)` delegates to `UploadController.upload`; success caches a `FrontendUpload` and routes to upload. `refresh_uploads` calls `list_eeg`. `view_upload(upload_id)` calls `retrieve_eeg`.

### Analysis Flow

`start_analysis(upload_id)` calls `AnalysisController.start_analysis`. Success caches a workflow, loads prediction and reports for the resulting analysis id, enriches workflow stages from `workflow_report`, enriches prediction summary, and routes to analysis.

### Prediction Flow

`load_prediction(analysis_id)` retrieves prediction, confidence, and explanation facets and caches a `FrontendPrediction`. `render_prediction` uses explicit analysis id or latest cached prediction. No prediction produces a complete empty-state HTML page.

### Report Flow

`load_reports(analysis_id)` calls `list_reports` and caches `FrontendReport` records. `render_reports` uses explicit analysis id or latest cached report set. `ReportController.download(report_name)` returns canonical JSON for a cached report.

## SECTION E - State Inventory

| State object | Stored state | Session/auth state | Workflow state | Prediction state | Report state | Persistence behavior |
|---|---|---|---|---|---|---|
| `ApplicationState` | current page, flash, user/session, uploads, workflows, predictions, reports | `FrontendUser`, `FrontendSession`, volatile `_token`, `session_expired`; token excluded from `snapshot()` | `FrontendWorkflow` list with stages/status/ids | dict keyed by analysis id | dict keyed by analysis id | in-memory only; `snapshot()` is secret-free and deterministic |
| Clinical `WorkstationState` | loaded snapshot plus context | none | cases/reviews/findings/knowledge/intelligence/decision support from snapshot | none | registered reports in artifacts | loads JSON snapshot; no mutation except presentation context |
| Operational `WorkstationState` | loaded snapshot plus context | none | event/timeline/workflow/graph/analytics/recommendation blocks from snapshot | none | reports in V3 subsystem blocks | loads JSON snapshot; no mutation except presentation context |
| Autonomous `WorkstationState` | loaded snapshot plus context | none | goals/policies/plans/tasks/agents/executions/governance blocks | none | reports in entity/governance blocks | loads JSON snapshot; no mutation except presentation context |
| Offline `AppState` | run dir, index, outputs, reports, registries, dataset intelligence, manifest | none | five research workflows from registered artifacts | inference outputs/reports | report dicts from index | loads registered JSON files from run directory; read-only |

## SECTION F - Gateway/API Mapping

Only `frontend/application_frontend/` defines a runtime backend gateway. Workstations and offline research app consume snapshots/artifacts, not APIs.

| Frontend action | Controller/method | Gateway operation | Params | Token | Output/cache |
|---|---|---|---|---|---|
| Register | `AuthController.register` | `register_user` | `username`, `password`, `role` | no | success routes to login |
| Login | `AuthController.login` | `login` | `username`, `password` | no | caches user/session/token, routes dashboard |
| Logout | `AuthController.logout` | `logout` | `{}` | yes | clears auth state |
| Upload EEG | `UploadController.upload` | `upload_eeg` | `filename`, `content` | yes | caches `FrontendUpload` |
| List uploads | `UploadController.refresh_history` | `list_eeg` | `{}` | yes | replaces upload cache |
| Retrieve upload | `UploadController.retrieve` | `retrieve_eeg` | `upload_id` | yes | returns upload details, routes upload |
| Start analysis | `AnalysisController.start_analysis` | `start_analysis` | `upload_id` | yes | caches `FrontendWorkflow`; app auto-loads prediction/reports |
| List analysis history | `AnalysisController.refresh_history` | `list_analysis_history` | `{}` | yes | replaces workflow cache |
| Retrieve prediction | `PredictionController.load` | `retrieve_prediction` | `analysis_id` | yes | prediction facet |
| Retrieve confidence | `PredictionController.load` | `retrieve_confidence` | `analysis_id` | yes | confidence facet |
| Retrieve explanation | `PredictionController.load` | `retrieve_explanation` | `analysis_id` | yes | explanation facet |
| List reports | `ReportController.load` | `list_reports` | `analysis_id` | yes | caches report list |

Response status vocabulary interpreted by the UI: `ok`, `created`, `bad_request`, `unauthorized`, `forbidden`, `not_found`, `error`. `unauthorized` triggers session clearing and login navigation.

## SECTION G - Reuse Assessment

High reuse:

- Backend gateway contract and controller methods in `application_frontend` should remain intact.
- Domain projection dataclasses should remain the source of typed frontend state.
- Workstation and offline app state loaders should remain the data boundary.
- Workspace page builders already encode complete capability coverage and should be used as the authoritative functional map.
- Validation/reporting modules should be preserved as guardrails for future UI replacement.

Partial reuse:

- Page builders and component builders can be used as intermediate adapters to a new design system, but their current section shape may need a visual adapter layer.
- Static HTML renderers prove full browser renderability today but are likely presentation-rewrite candidates.
- Chart spec builders are reusable as data-transform layers even if the final chart renderer changes.

Rewrite candidates:

- `application_frontend/layouts/__init__.py` visual CSS/HTML output.
- Section rendering in workstation/offline HTML report renderers.
- Current basic components (`kv_panel`, `table`, `badges`, etc.) as visual widgets, while preserving their data contracts.

## SECTION H - Missing Browser Exposure Assessment

Application frontend can generate complete static HTML pages today through `FrontendApp.render_*`, but there is no browser server/router implementation inside `frontend/application_frontend/`; scripts are the sanctioned live seam.

Clinical, operational, autonomous, and offline apps can generate complete static HTML documents from snapshots/run directories. Their browser exposure is file/static-report oriented, not an interactive routed web app.

No React/Tailwind/browser component tree exists in the inspected frontend folders. Current browser exposure is deterministic static HTML, inline CSS, and inline SVG.
