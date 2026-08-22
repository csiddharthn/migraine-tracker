"""Purpose: Namespace configuration for labels and constants.

Usage: Provides cfg class with weekday names and laterality labels
used in UI rendering and data interpretation.

Functions available:
- None

Classes available:
- cfg

Call hierarchy:
- name_space.py -> frontend.i18n (indirect usage)
"""

class cfg:
    WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
    LATERALITY_LABELS = {
        "rechts": "Rechts",
        "links": "Links",
        "beidseitig": "Beidseitig",
        "beidseitig_linksbetont": "Beidseitig, linksbetont",
        "einseitig_unbekannt": "Einseitig, Seite offen",
        "unbekannt": "Nicht dokumentiert",
    }
