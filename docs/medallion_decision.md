# Medallion architecture decision

Bronze/Silver/Gold layers are not implemented.

The application has one small, stable transactional source after migration: manually maintained migraine and daily treatment records for multiple people in PostgreSQL. It does not have recurring heterogeneous ingestion, late-arriving batches or separately governed analytical products that would justify three persistent data lifecycles.

Instead the design uses:

- `migration_source_rows` as an immutable-style import audit for exact Excel source payloads;
- constrained transactional tables for migraine entries, triggers and daily treatment status;
- a separate interpretation table for automatically derived and manually reviewed note information;
- an audit log for user changes;
- deterministic analytical functions over PostgreSQL records;
- database views or materialised views only if data volume or query latency later makes them useful.

This gives the useful Bronze property (source traceability) without making the application maintain three copies of a small clinical diary dataset.
