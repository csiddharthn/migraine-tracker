---
applyTo: "frontend/**"
description: "Frontend agent instructions for the migraine tracker"
---

# Frontend Agent Instructions

## Scope
This folder contains the Streamlit-based frontend for the migraine tracker application.

## Structure
- `components/` — Reusable UI components (`ui.py`, `charts.py`, `filters.py`, `state.py`, `users.py`)
- `forms/` — Form definitions (`entry_form.py`, `ai_intake.py`)
- `pages/` — Page-level views
- `i18n.py` — Internationalization helpers

## Conventions
- Use `frontend.i18n` for formatting dates and numbers.
- Apply UI styling via `frontend.components.ui.apply_ui()`.
- Keep components stateless where possible; use `state.py` for shared state.
- All user-facing text should go through i18n helpers.

## Agent Behavior
- When modifying components, check `components/ui.py` for styling rules.
- When adding forms, reference `forms/entry_form.py` or `forms/ai_intake.py`.
- When working on pages, ensure `i18n.py` is used for any displayed text.
