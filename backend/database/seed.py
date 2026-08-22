from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import TriggerDefinition


TRIGGERS = (
    ("1", "Aufregung / Stress", "DMKG-Auslöser"),
    ("2", "Erholungsphase", "DMKG-Auslöser"),
    ("3", "Änderung im Schlaf-Wach-Rhythmus", "DMKG-Auslöser"),
    ("4", "Menstruation", "DMKG-Auslöser"),
    ("5", "Kalte Schlafumgebung / Fenster offen", "Persönlich: ca. 17–18 °C"),
    ("6", "Hitze / hohe Außentemperatur", "Persönlich: >38 °C tagsüber"),
    ("7", "Spät und zu wenig Schlaf", "Persönlicher Auslöser"),
    ("8", "Unsicher", "Auslöser nicht sicher zuordenbar"),
)


def seed_reference_data(session: Session) -> None:
    existing = {item.code for item in session.query(TriggerDefinition).all()}
    for order, (code, label, description) in enumerate(TRIGGERS, start=1):
        if code not in existing:
            session.add(
                TriggerDefinition(
                    code=code,
                    label=label,
                    description=description,
                    sort_order=order,
                    active=True,
                )
            )
    if "ND" not in existing:
        session.add(
            TriggerDefinition(
                code="ND",
                label="Nicht dokumentiert (Altbestand)",
                description="Nur für migrierte Excel-Einträge ohne ausgefüllten Auslöser.",
                sort_order=99,
                active=False,
            )
        )
    session.flush()
