# Excel-to-database mapping

The Excel workbook is used only for the optional one-time migration. It is not a runtime data source. The original workbook, migration reports, source-specific reconciliation figures and personal records are intentionally excluded from the repository.

| Excel field | PostgreSQL target |
|---|---|
| Datum | `migraine_entries.entry_date` and `daily_records.record_date` |
| Auslöser | `entry_triggers.trigger_code` |
| Stärke | `migraine_entries.strength` |
| Dauer | `migraine_entries.duration_hours` |
| Schmerzart | `migraine_entries.pain_type` |
| Schmerzseite | `migraine_entries.entered_laterality` |
| Vorboten / Aura | `migraine_entries.aura_codes` |
| Begleitsymptome | Boolean symptom fields and `other_symptom_codes` |
| Akutmedikation | `medication_intakes` |
| Vorbeugende Behandlung | `daily_records` treatment fields |
| Hat geholfen? | `medication_intakes.effectiveness` |
| Notizen | `migraine_entries.notes`, preserved unchanged |

Information derived from notes, including onset, peak, end, laterality and recurring contexts, is stored separately in `note_interpretations`. Automatic interpretations never overwrite the original note and can be reviewed or corrected.

Every person has a stable `user_profiles` record. Dates are unique per person, allowing different people to have entries on the same day. All analytical and repository queries are scoped to the selected person.

The migration utility is idempotent, detects duplicates, retains raw source rows for local audit purposes and produces a local migration report. None of those source rows or reports should be committed.
