# Iteration 1 — Wiki (LiqiWiki): Implementation Plan

Status: ready to follow; implementation tasks unchecked.

Goal: crawl Arena of Valor Fandom, normalize heroes, skills, equipment, maps, and game modes into PostgreSQL, expose read APIs, display wiki content, and keep data updated.

## 1. Source documents and working decisions

- [Liqi milestone](../Liqi.md): Iteration 1 scope and deliverables.
- [Architecture](../Liqi-Architecture.md): service boundaries, monorepo, schema ownership, raw storage, and deployment.
- [Crawling](../Liqi-crawling.md): Fandom source selection.
- [Fandom endpoints](../Liqiwiki-Fandom-endpoint.md): discovery, extraction, images, and update APIs.

Repository currently contains documentation and a minimal README. All application paths, commands, schemas, and contracts below are proposed implementation targets, not existing functionality.

Source correction: Cargo is unsupported at the target Fandom API endpoint, as confirmed by the user. This plan supersedes Cargo recommendations in the source documents; extraction uses standard MediaWiki APIs and wikitext parsing.

Implementation decisions:

| Area           | Iteration 1 decision                                                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Runtime        | Next.js web → NestJS public API → PostgreSQL; Python CLI performs crawl and ETL.                                                         |
| FastAPI        | Scaffold internal service and health endpoint; crawler runs as a separate CLI process.                                                   |
| Tooling        | pnpm workspace for TypeScript; uv for Python; pin supported runtime and dependency versions during setup.                                |
| Data ownership | SQLAlchemy + Alembic own schema `data`; NestJS uses parameterized PostgreSQL queries with read-only access.                              |
| Raw storage    | Persistent volume containing source responses and manifests; replay without recrawling.                                                  |
| Extraction     | Fetch revision-backed wikitext through MediaWiki APIs; parse infoboxes, templates, and sections. Use rendered sections only as fallback. |
| Scheduling     | Scheduled Python CLI, initially hourly incremental sync and weekly reconciliation; prevent overlapping jobs.                             |
| Content        | Preserve source language and names; add aliases only when verified. Unknown values remain null.                                          |
| Search         | Query normalized local data through NestJS; web requests do not trigger Fandom calls.                                                    |

This iteration delivers core wiki data plus update tracking. Gems, enchantments, emblems, skins, match datasets, mining, predictions, draft tools, accounts, admin job UI, and Celery/Redis belong to later work.

## 2. Execution order and checkpoints

Follow steps in order. Complete each acceptance gate before marking that step done. Record source discoveries and unresolved fields alongside fixtures.

| Step | Deliverable                                  | Depends on               |
| ---- | -------------------------------------------- | ------------------------ |
| 1    | Runnable monorepo and local infrastructure   | —                        |
| 2    | Verified source inventory and raw fixtures   | 1                        |
| 3    | Database migrations and normalized contracts | 2                        |
| 4    | Resumable crawler and raw archive            | 2–3                      |
| 5    | Parsers and transactional ETL                | 3–4                      |
| 6    | First complete, audited dataset              | 5                        |
| 7    | NestJS catalog API                           | 3, 6 for live acceptance |
| 8    | Next.js wiki pages                           | 7                        |
| 9    | Incremental updates and revision tracking    | 6–8                      |
| 10   | Reproducible deployment and final acceptance | 1–9                      |

Checkpoint A: one verified hero, its skills, and one equipment item reach PostgreSQL through raw snapshots (step 5).

Checkpoint B: full core dataset browsable through API and web (step 8).

Checkpoint C: scheduled updates, recovery, and clean-start deployment verified (step 10).

## Step 1 — Bootstrap monorepo and infrastructure

Target structure:

```text
apps/web/                         # Next.js App Router
apps/api/src/catalog/             # NestJS CatalogModule
services/data/src/liqi_data/
  api/                            # FastAPI health endpoint
  cli.py                          # Discovery, crawl, replay, sync commands
  sources/fandom/                  # HTTP client, discovery, parsers
  schemas/                        # Pydantic normalized models
  db/                             # SQLAlchemy models and repositories
  jobs/                           # Crawl, ETL, reconciliation
services/data/migrations/          # Alembic migrations for data schema
services/data/tests/fixtures/      # Small checked-in source samples
contracts/wiki/                   # OpenAPI export and response examples
infra/compose.yaml
infra/postgres/                    # Local database roles/bootstrap
docs/plans/
docs/runbooks/liqiwiki.md
```

- [x] **1.1** Create root workspace, TypeScript configuration, Python project, lockfiles, runtime version files, and `.gitignore` for local secrets, raw archives, and generated builds.
- [x] **1.2** Scaffold Next.js, NestJS, and FastAPI. Add `/health` for each backend and a simple web landing page.
- [x] **1.3** Add `.env.example`: database connections for migrations/worker/API, `FANDOM_API_URL`, `FANDOM_USER_AGENT`, request rate, raw storage path, and internal NestJS URL used by web.
- [x] **1.4** Add Compose services `postgres`, `api`, `web`, `data-api`, and one-shot `data-worker`. Mount persistent database and raw-data volumes.
- [x] **1.5** Configure PostgreSQL owner/migration credentials, worker write permissions on `data`, and API read-only permissions, including grants for future tables. Keep `app` ownership reserved for NestJS.
- [x] **1.6** Add install, dev, lint, typecheck, test, and build scripts; configure CI to run relevant TypeScript/Python checks and migration smoke checks against PostgreSQL.
- [x] **1.7** Document startup order: database → migration job → API/FastAPI/web; expose readiness failures clearly.

**Acceptance gate:** clean dependency install succeeds; Compose starts services; backend health checks pass; data persists across container restarts; API database role cannot insert into `data`.

## Step 2 — Verify Fandom capabilities and capture fixtures

Base URL: `https://arenaofvalor.fandom.com/api.php`. Every API request uses `format=json`, an explicit descriptive User-Agent, and a configurable rate starting at one request/second.

- [x] **2.1** Implement an initial `discover` CLI command. Save HTTP status, source URL/parameters, fetch time, and response body for each probe.
- [ ] **2.2** Enumerate `action=query&list=allcategories&aclimit=500`, following all continuation fields. Confirm actual categories for heroes, equipment, maps, and game modes.
- [ ] **2.3** Verify standard MediaWiki revision, parse, section, and image APIs against sample pages. Record response shapes, supported revision selectors, and template/subpage dependencies needed for extraction.
- [ ] **2.4** Enumerate representative category members. Identify namespace rules, redirects, subcategories, subpages, and pages that are indexes rather than entities. Configure recursive category traversal with a visited set where needed.
- [ ] **2.5** Capture at least three structurally different hero pages, three equipment pages including a recipe, one map, and one game mode. Verify examples such as `Airi` and `Sonic_Boots` before selecting them.
- [ ] **2.6** Request revisions with `rvprop=ids|timestamp|content` and `rvslots=main`; save page ID, revision ID, source timestamp, and main-slot content together.
- [ ] **2.7** Inspect hero infoboxes, ability sections/subtemplates, item stats/recipes, and image references. Fetch `action=parse&prop=sections` when section discovery is necessary and `imageinfo` for referenced files.
- [ ] **2.8** Write `docs/runbooks/fandom-discovery.md` and `services/data/src/liqi_data/sources/fandom/config.yaml`: verified categories, templates, field mappings, standard API capabilities, sample pages, and discovery date.
- [ ] **2.9** Store small successful responses as fixtures; include missing fields, redirects, nested templates, and unavailable images. Record actual attribution/license information for page content and media separately.

**Acceptance gate:** each entity type has an observed extraction path and fixture. No unverified template field, skill count, or filename is treated as a guaranteed source contract. If source access is blocked, record the blocker; fixture-only progress does not count as live crawl acceptance.

## Step 3 — Define normalized data and migrations

Use stable internal IDs and unique `(source, source_page_id)` page identity. Titles and URL slugs can change without creating new entities. Wiki revision timestamps are not game patch identifiers.

| Table in `data`                        | Minimum contents / constraints                                                                                                                                |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source_pages`                         | Source, page ID, title, canonical URL, entity kind, latest successfully imported revision, source timestamp, crawl time, availability; unique source/page ID. |
| `page_revisions`                       | Page FK, revision ID, parent ID when available, timestamp, raw path/checksum, parser version, import status; unique page/revision ID.                         |
| `heroes`                               | Source page FK, unique slug, name, description, damage/attack types, base stats JSONB, image metadata, nullable patch reference.                              |
| `hero_aliases`                         | Hero FK, alias, language/source; no duplicate alias for the same hero/source.                                                                                 |
| `roles`, `hero_roles`                  | Canonical roles and many-to-many hero assignments.                                                                                                            |
| `skills`                               | Hero FK, stable source key within hero, display order, name, type, description, cooldown/cost values, icon; unique hero/source key.                           |
| `items`                                | Source page FK, unique slug, name, price, category, stats JSONB, passive/active descriptions, image metadata.                                                 |
| `item_components`                      | Parent item FK, component item FK, quantity; unique parent/component; prevent self-reference.                                                                 |
| `maps`, `game_modes`, `map_game_modes` | Source-backed entities and verified many-to-many relationships.                                                                                               |
| `patches`                              | Optional verified patch identifier; unknown patch remains null.                                                                                               |
| `crawl_runs`, `crawl_run_pages`        | Mode, timestamps, status, counts, page attempts/errors, raw manifest, parser version; support retrying failed pages.                                          |
| `sync_state`                           | Source/stream checkpoint, continuation/window state, last successful completion.                                                                              |

- [ ] **3.1** Define Pydantic models for all five entity types and shared provenance/image metadata; map actual source fields from step 2.
- [ ] **3.2** Define representation for stats and ranked skill values: typed numbers/arrays when reliably parsed, units and original text alongside them, null for unknowns. Never convert missing values to zero.
- [ ] **3.3** Define deterministic skill keys from verified source slots/template identifiers; document reconciliation when source structure changes. Do not require a fixed number of skills.
- [ ] **3.4** Create SQLAlchemy models and an initial Alembic migration, foreign keys, uniqueness constraints, and indexes for slugs, page/revision identity, roles, and item categories.
- [ ] **3.5** Add UTC timestamps and provenance to normalized records or their linked source page; distinguish latest observed revision from latest successfully imported revision.
- [ ] **3.6** Define slug generation and collision handling, rename behavior, and aliases. Persist stable slugs where possible.
- [ ] **3.7** Add documented example JSON for hero list/detail, item detail/recipe, map, and mode in `contracts/wiki/`.
- [ ] **3.8** Verify migrations on an empty database and check grants/constraints with representative records.

**Acceptance gate:** all five entity types fit the schema; duplicate source identities are rejected; records trace back to a raw revision; an unknown patch or stat can be stored without invented data.

## Step 4 — Build reliable extraction and raw storage

- [ ] **4.1** Build a shared HTTP client with timeout, descriptive User-Agent, rate limiter, bounded exponential backoff with jitter, and `Retry-After` support. Retry transient failures/429/5xx; surface persistent access failures and MediaWiki JSON errors.
- [ ] **4.2** Implement generic continuation handling for category lists, revisions, and recent changes, preserving all continuation fields returned by MediaWiki.
- [ ] **4.3** Implement category traversal and page deduplication by page ID. Keep exclusion reasons for non-entity pages.
- [ ] **4.4** Implement revision, section, referenced-template/subpage, and image fetchers. Pin parse requests to the captured revision where supported. Archive dependency revisions and rendered fallback responses with their retrieval times; record when rendering depends on current templates rather than historical template versions.
- [ ] **4.5** Archive successful responses before transformation under `raw/fandom/<run-id>/...`; write manifests containing request parameters, timestamps, page/revision IDs when available, checksums, and response paths.
- [ ] **4.6** Implement `crawl --full`, `crawl --page-id`, `crawl --resume`, and `replay --run-id`. Persist completed/failed pages; retries must not lose prior successful work.
- [ ] **4.7** Track each run as queued/running/succeeded/partial/failed with discovered, fetched, imported, unchanged, excluded, and failed counts. Use a database job lock to prevent overlapping source syncs.
- [ ] **4.8** Test multiple continuation pages, duplicate discovery, API-level errors, throttling, timeout, interrupted runs, and replay from raw data with network disabled.

**Acceptance gate:** an interrupted sample crawl resumes; requests stay within the configured rate; every fetched page has raw provenance; one failing page does not hide failures or abort unrelated successful pages.

## Step 5 — Implement parsers and transactional ETL

- [ ] **5.1** Implement verified infobox/template/section-to-normalized mappings for each entity type. Prefer revision-backed structured template fields, then wikitext sections; use rendered sections only for fields those paths cannot extract. Record field provenance and precedence when extraction paths disagree.
- [ ] **5.2** Parse nested wikitext with `mwparserfromhell`, not broad regular expressions. Normalize whitespace, links, lists, numbers, and units while retaining useful descriptions.
- [ ] **5.3** Extract heroes: name, aliases, roles, damage/attack types, base stats, description, and actual icon references.
- [ ] **5.4** Extract skills from hero sections/subtemplates: name, ordering, passive/active/ultimate type, description, cooldown, cost, and icon. Resolve referenced templates/subpages where necessary and record dependencies.
- [ ] **5.5** Extract equipment: name, price, category, stats, passive/active effects, icon, and recipe references. Resolve components after all items exist; report unresolved references and invalid recipe cycles.
- [ ] **5.6** Extract maps and game modes, preserving descriptions and verified associations. Keep unresolved associations visible in the run report.
- [ ] **5.7** Resolve images through `imageinfo`, storing file title, URL, attribution, license, and retrieval time when available. Provide a missing-image representation.
- [ ] **5.8** Validate each page before writing. Quarantine malformed payloads with raw paths and actionable errors; preserve the last valid normalized version on failure.
- [ ] **5.9** Upsert a hero and its skills/roles/aliases in one transaction; replace stale child records only after complete successful parsing. Apply the same atomicity to item relationships.
- [ ] **5.10** Skip already imported revisions unless parser version changes or replay is explicitly requested. Only advance the page's successful revision after transaction commit; prevent older replays from overwriting newer current data by default.
- [ ] **5.11** Add parser fixture tests and PostgreSQL integration tests for null handling, nested templates, repeated imports, renamed pages, changed/removed skills, and rollback on malformed updates.

**Acceptance gate:** checkpoint A passes. Reimporting identical raw data creates no duplicate entities or relationships. A failed hero update leaves its existing skills intact. Maps and modes pass fixture-based normalization too.

## Step 6 — Produce and audit the initial dataset

- [ ] **6.1** Record a source timestamp before starting the full crawl so changes during the crawl can be caught by the first incremental sync.
- [ ] **6.2** Run full discovery → archive → normalize → load for every verified core category, including all continuation pages.
- [ ] **6.3** Generate a coverage report per type: discovered candidates, explicit exclusions, imported entities, quarantined pages, missing fields/images, and unresolved relationships. Counts must reconcile.
- [ ] **6.4** Manually compare at least three heroes with all extracted skills, three equipment items including recipes, one map, and one mode against archived source content.
- [ ] **6.5** Fix parser defects and replay affected raw snapshots. Track unsupported source structures explicitly; do not silently omit pages.
- [ ] **6.6** Repeat the full import and verify stable entity/relationship counts and no duplicate source identities.
- [ ] **6.7** Save a run manifest, quality report, parser version, database backup reference, and initial sync checkpoint for the accepted dataset.

**Acceptance gate:** every discovered candidate is imported or explicitly accounted for; valid core entity pages have no unresolved import failures; sample review passes; missing source fields are reported rather than fabricated.

## Step 7 — Build NestJS read APIs

Implement inside `apps/api/src/catalog/`. Lists use `page` (default 1), `pageSize` (default 24, maximum 100), deterministic ordering, and `{ items, page, pageSize, total }` responses.

| Endpoint                                   | Response / filters                                                  |
| ------------------------------------------ | ------------------------------------------------------------------- |
| `GET /heroes`                              | Hero summaries; `q` matches names/aliases; `role` filters roles.    |
| `GET /heroes/:slug`                        | Hero details, roles, stats, ordered skills, images, and provenance. |
| `GET /heroes/:slug/revisions`              | Paginated locally captured revision metadata and import status.     |
| `GET /items`                               | Item summaries; `q` and `category` filters.                         |
| `GET /items/:slug`                         | Stats, price, effects, component recipe, image, provenance.         |
| `GET /maps`, `GET /maps/:slug`             | Map list/details with linked modes.                                 |
| `GET /game-modes`, `GET /game-modes/:slug` | Mode list/details with linked maps.                                 |
| `GET /roles`                               | Available role filter values.                                       |

- [ ] **7.1** Implement DTO validation and parameterized repository queries using the read-only database role.
- [ ] **7.2** Implement pagination/filtering, deterministic sorting, and detail joins without per-record query loops. Define unavailable-page behavior consistently: exclude from default lists, return 404 for unavailable details.
- [ ] **7.3** Return source URL, source revision timestamp, last successful import time, and content attribution on details. Do not expose filesystem paths from raw archives.
- [ ] **7.4** Return consistent 400 validation, 404 missing entity, and 503 database-unavailable responses. Generate OpenAPI and save response examples in `contracts/wiki/`.
- [ ] **7.5** Test list boundaries, alias search, role/category filters, absent entities, null values, nested skills/recipes, and read-only operation against seeded PostgreSQL.
- [ ] **7.6** Verify endpoints respond using only PostgreSQL when Fandom is unavailable.

**Acceptance gate:** every documented route returns validated data from the accepted dataset; hero detail includes skills; source attribution survives the API boundary; invalid input produces predictable errors.

## Step 8 — Build the Next.js wiki experience

- [ ] **8.1** Add shared navigation for heroes, equipment, maps, and modes. Create a typed NestJS API client and shared loading, error, empty, and not-found components.
- [ ] **8.2** Build `/heroes`: icon/name/role cards, name/alias search, role filter, pagination. Keep filter/page state in URL query parameters; reset page when filters change.
- [ ] **8.3** Build `/heroes/[slug]`: image, roles, stats, descriptions, ordered skill panels, cooldown/cost values, source link, and update timestamps.
- [ ] **8.4** Build `/items` and `/items/[slug]`: search/category filter, price, stats, passive/active descriptions, and linked recipe components.
- [ ] **8.5** Build `/maps`, `/maps/[slug]`, `/game-modes`, and `/game-modes/[slug]` using shared list/detail components and cross-links.
- [ ] **8.6** Use Server Components for initial reads and Client Components for interactive controls. Start with uncached detail requests so accepted imports appear on refresh.
- [ ] **8.7** Render descriptions as plain text or sanitized limited markup. Configure allowed image hosts from discovery, alt text, and a fallback image; show source/content and media attribution where applicable.
- [ ] **8.8** Add revision metadata to hero detail, clearly labeling it as captured wiki history rather than game patch history.
- [ ] **8.9** Verify mobile/desktop layouts and keyboard navigation. Add browser checks covering hero search → hero skills, equipment → recipe component, map → mode, missing image, empty result, and API failure.

**Acceptance gate:** checkpoint B passes. Every core entity type is browsable; skills and equipment details match the API; deep links and filter URLs survive refresh; unavailable fields have readable fallback states.

## Step 9 — Add incremental sync and revision history

- [ ] **9.1** Implement `sync --recent`: query `recentchanges` using a saved UTC checkpoint, fixed upper bound, chronological direction, and all continuation tokens. Include edits, new pages, and relevant log events.
- [ ] **9.2** Use an overlapping time window and deduplicate by event/revision identity. Determine category membership for new/changed pages before treating them as catalog entities.
- [ ] **9.3** Refetch affected source pages, archive new revisions, and run the same validation/upsert path as full import. Refetch dependent heroes/items when tracked templates or subpages change; trigger broader reconciliation for dependencies that cannot be resolved safely.
- [ ] **9.4** Advance the durable checkpoint only after the bounded window is handled successfully or failed events are durably queued for retry. Retain retry records until import succeeds; expose partial runs.
- [ ] **9.5** Retrieve revision history with `rvprop=timestamp|user|comment|ids` and pagination as needed. Persist metadata separately from whether revision content has been archived/imported; API must not imply complete historical snapshots.
- [ ] **9.6** Process move/delete logs: preserve page identity and aliases on rename; mark confirmed deleted pages unavailable. Treat temporary request failures as errors, not deletions.
- [ ] **9.7** Implement `reconcile --full`: rediscover category membership, compare active records with the source, retry failed pages, refresh dependencies, and confirm removals. Use this after outages exceeding recent-change retention.
- [ ] **9.8** Schedule hourly recent sync and weekly reconciliation with explicit environment/volume configuration and the shared source lock. Log last success, source lag, counts, and actionable failures.
- [ ] **9.9** Test duplicated events, tied timestamps, multiple pages of changes, edit during full crawl, interruption before checkpoint save, malformed update, rename/delete, template changes, and an expired checkpoint.
- [ ] **9.10** Run one observed live update if available; otherwise replay a controlled changed-revision fixture end to end and label that evidence accurately.

**Acceptance gate:** unchanged sync creates no duplicates; changed content reaches API/web after refresh; failed parsing preserves previous content and remains retryable; restart loses no events; locally captured revision metadata is readable.

## Step 10 — Deployment, runbook, and final verification

Implement these command targets with CLI help and nonzero exit codes for incomplete/failed jobs. Commands run from repository root after setup:

```bash
docker compose -f infra/compose.yaml up -d postgres
docker compose -f infra/compose.yaml run --rm data-worker uv run alembic upgrade head
docker compose -f infra/compose.yaml run --rm data-worker uv run liqi-data discover
docker compose -f infra/compose.yaml run --rm data-worker uv run liqi-data crawl --full
docker compose -f infra/compose.yaml up -d api data-api web
docker compose -f infra/compose.yaml run --rm data-worker uv run liqi-data sync --recent
```

- [ ] **10.1** Configure production builds, health checks, persistent mounts, and environment examples; document ports, service URLs, migrations, and scheduling in `docs/runbooks/liqiwiki.md`.
- [ ] **10.2** Document full crawl, single-page retry, resume, raw replay after parser changes, recent sync, and reconciliation, including run-ID selection and expected output.
- [ ] **10.3** Document database/raw-volume backup and restore; perform a restore smoke check and verify source provenance remains resolvable.
- [ ] **10.4** Run CI checks: lint/typecheck/build, fixture parser tests, database/migration integration tests, API contract tests, and core browser journeys. Keep routine CI independent of live Fandom availability.
- [ ] **10.5** Execute clean-start Compose instructions on an empty database, import real source data, browse the core pages, and run recent sync twice to confirm idempotency.
- [ ] **10.6** Record dataset counts, quality report, test results, verified source capabilities, remaining source limitations, and update evidence in the runbook.
- [ ] **10.7** Update Iteration 1 checkboxes in `docs/Liqi.md` only after the corresponding acceptance gates below pass.

## Final definition of done

- [ ] Monorepo runs Next.js, NestJS, FastAPI, Python worker, and PostgreSQL using documented commands.
- [ ] MediaWiki category/revision/image extraction and wikitext parsing work for every core entity type; rendered-section fallback is tested where needed.
- [ ] Heroes, skills, equipment, maps, and modes are normalized in schema `data` with source identity, revision provenance, and replayable raw data.
- [ ] Full import accounts for all discovered candidates; repeated import is idempotent; malformed updates preserve last valid data.
- [ ] NestJS serves validated, paginated read APIs with read-only database permissions.
- [ ] Web supports hero browsing, skill details, equipment/recipes, maps/modes, search/filtering, attribution, and failure states.
- [ ] Recent changes, captured revision history, retries, scheduled execution, and periodic reconciliation work end to end.
- [ ] Clean-start deployment, meaningful automated checks, and backup/restore verification pass; runbook contains reproducible evidence.
