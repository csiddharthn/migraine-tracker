# Structured entry import

The migraine tracker can import a versioned JSON draft that was structured outside
the application, for example by ChatGPT after a freely dictated headache
description.

This path does **not** call Groq or OpenRouter. It only parses the JSON locally,
opens the normal entry-review form, and saves through the existing `EntryService`
after the user explicitly submits the reviewed form.

## Import envelope

Schema version 1 uses this top-level structure:

```json
{
  "schema_version": "1",
  "source": "ChatGPT",
  "source_narrative": "Optional original dictated text",
  "draft": {
    "entry_date": "2026-08-29",
    "strength": 6,
    "duration_hours": 4.5,
    "trigger_codes": [],
    "proposed_triggers": ["Unsicher"],
    "pain_type": "Dumpf / drückend",
    "entered_laterality": "Rechts",
    "nausea": true,
    "medications": [
      {
        "name": "Eletriptan",
        "taken_at": "10:15",
        "dose": "40 mg",
        "effectiveness": "Ja"
      }
    ],
    "timeline": [
      {
        "start_time": "08:30",
        "end_time": null,
        "note": "Kopfschmerz begann."
      }
    ],
    "possible_factors": "",
    "symptoms_and_actions": ""
  }
}
```

The `draft` object follows the existing `AIIntakeDraft` schema. Optional fields
may be omitted. `entry_date`, `strength`, and `duration_hours` must be present in
a structured import.

## Trigger handling

External assistants do not need to know the local trigger codes. They can place
human-readable trigger labels in `draft.proposed_triggers`. During import, the
tracker compares those labels case-insensitively with the active local trigger
catalogue and converts exact matches into the corresponding trigger codes.

Unknown codes and unmatched labels are kept as unresolved trigger suggestions.
The review screen warns about them, and the user can choose the appropriate
trigger manually before saving.

## Safety and provenance

- Future entry dates are rejected.
- Unknown top-level fields in the versioned envelope are rejected.
- The normal form validation and `EntryService` trigger validation still apply.
- The import never writes to PostgreSQL before the user submits the review form.
- Imported entries use `source_system = structured_import`.
- Provenance is stored as `ai_provider = structured_import`, `ai_model = source`,
  and `ai_prompt_version = structured-import-v1`.
- The optional original dictation is stored only when the user keeps the
  corresponding checkbox enabled.
