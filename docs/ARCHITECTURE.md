# Architecture & schema

```
Browser (TypeScript / Vite)
  local File → blob URL → HTMLVideoElement (no upload)
  media clock → annotation time → timeline + SVG pose + locus
  same-origin JSON API
Python loopback HTTP service (standard library)
  serialized writes / validation → SQLite
  EAF parser / serializer → strict supported-subset contract
  motion heuristic → pending suggestions → researcher decision
```

Run from the repository root. `dist/` is generated, not committed. The server serves that directory and supports HTTP byte ranges for video seek. Host checks prevent DNS rebinding to arbitrary hosts; JSON-only and same-origin writes reduce browser-origin attacks. It does not authenticate other local processes. Do not treat it as a production internet service. No telemetry, API credentials, cloud uploads or network inference are included. External documentation links navigate only when clicked.

## Database

| Table | Identity & fields | Relations |
|---|---|---|
| projects | UUID `id`, name, duration (ms), pose JSON, original source_eaf text | Owns tiers / suggestions |
| tiers | UUID `id`, project_id, name, channel, color | Independent aligned interval tier |
| lexicon | UUID `id`, gloss, description | Shared local vocabulary; renaming updates text, never ID |
| annotations | UUID `id`, tier_id, start, end, value, lexicon_id, provenance JSON, start_slot, end_slot | Foreign keys to tier / lexicon; EAF slot identities retained |
| suggestions | UUID `id`, project_id, tier_id, start, end, value, status, provenance JSON, annotation_id | Accepted annotation is distinct from candidate; rejected retained |

`PRAGMA foreign_keys=ON`; indexed `(tier_id,start,end)` interval queries. Intervals are integer, half-open `[start,end)` in annotation time. API validates `0 ≤ start < end ≤ duration`, membership, lexical references and same-tier non-overlap. Overlap SQL is `a.start < query.end AND a.end > query.start`. Cross-tier overlap is intended. Raw SQL can bypass domain checks; use the API or Store. Database values / UI labels use Unicode; UI renders user content through `textContent`, not HTML injection.

Templates: dominant, non-dominant, brows, head, mouth, motion. No automatic assignment of signing dominance or linguistic categories. UUID IDs are independent of gloss strings. EAF original annotation IDs remain in provenance while application IDs stay globally unique across imported documents.

## API

GET `/api/projects`, `/api/project/:id`, `/api/project/:id/eaf`, `/api/project/:id/backup`.

POST JSON: `/api/create-project`, `/api/annotation`, `/api/delete`, `/api/lexicon`, `/api/overlap`, `/api/import-eaf`, `/api/pose`, `/api/propose`, `/api/review`. Include `project_id` for project operations. Review decisions: accepted / rejected / undo. Core methods support edited acceptance parameters; the UI supports editing the resulting annotation after acceptance. EAF import validates before a transaction. Suggestion acceptance writes annotation + review status in one commit.

No multi-user version locks, CRDT, account permissions, background tasks or distributed transactions. Concurrent tabs may overwrite an annotation; do not use them as collaborative editors. A local lock serializes HTTP writes but does not resolve stale edits. Data retention / consent is the researcher's responsibility. SQLite and JSON exports are unencrypted; protect storage and backups. JSON backups include imported EAF media paths and research derivatives. Never commit them to public repositories.
