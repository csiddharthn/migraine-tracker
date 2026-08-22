# Medallion architecture decision

Bronze/Silver/Gold layers are not implemented.

The application has one small, stable transactional source: manually maintained migraine and daily treatment records for multiple people in PostgreSQL. It does not have recurring heterogeneous ingestion, late-arriving batches or separately governed analytical products that would justify three persistent data lifecycles.

Instead the design uses:

- constrained transactional tables for migraine entries, triggers and daily treatment status;
- a separate interpretation table for automatically derived and manually reviewed note information;
- an audit log for user changes;
- deterministic analytical functions over PostgreSQL records;
- database views or materialised views only if data volume or query latency later makes them useful.

The historical `migration_source_rows` table and source-reference columns remain in the schema solely to preserve existing provenance data. The application has no importer and does not read that table during normal operation. Keeping the historical rows avoids a destructive database migration while PostgreSQL remains the sole runtime source of truth.
