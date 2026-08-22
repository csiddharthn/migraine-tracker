from __future__ import annotations

"""Purpose: Note interpretation and timeline parsing.

Usage: Parses headache descriptions for onset times, triggers, and symptoms.

Functions available:
- parse_timeline_notes
- interpret_context

Classes available:
- None

Call hierarchy:
- interpreter.py -> backend.note_interpretation.structured_notes
"""

import re
from dataclasses import asdict, dataclass
from typing import Any


TIME_PATTERN = re.compile(r"(?<!\d)([0-2]?\d)(?::([0-5]\d))?\s*Uhr", re.IGNORECASE)
SHARED_UHR_RANGE = re.compile(
    r"(?<!\d)([0-2]?\d(?::[0-5]\d)?)\s*[–-]\s*([0-2]?\d(?::[0-5]\d)?)\s*Uhr",
    re.IGNORECASE,
)
ONSET_CONTEXT_PATTERN = re.compile(
    r"beginn|begann|begannen|setzten|eingesetzt|erstmals.{0,25}kopfschmerz|"
    r"kopfschmerzen bemerkt|mit.{0,35}kopfschmerzen aufgewacht|"
    r"aufgewacht.{0,180}kopfschmerz|kopfschmerz.{0,50}(erkennbar|wahrgenommen)",
    re.IGNORECASE,
)

CONTEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Kälte / Zugluft", re.compile(r"\b(kalt|kalte|kalten|kühl|kühle|kühlen|gefroren|frieren|mütze|zugluft|ventilator)\b", re.IGNORECASE)),
    ("Offenes Fenster", re.compile(r"fenster.{0,35}(offen|geöffnet)|(offen|geöffnet).{0,35}fenster", re.IGNORECASE)),
    ("Später Schlaf / Schlafmangel", re.compile(r"schlafmangel|spät.{0,30}(bett|eingeschlafen)|verkürzte schlafdauer|zu wenig schlaf", re.IGNORECASE)),
    ("Unterbrochener Schlaf / Baby", re.compile(r"unterbrochen|unruhig.{0,20}geschlafen|fütterung|baby.{0,30}(gefüttert|versorgt)|kind.{0,30}(gefüttert|weinen)", re.IGNORECASE)),
    ("Hitze / hohe Temperatur", re.compile(r"außentemperatur.{0,12}(3[8-9]|40)|\b3[8-9][–-]40\s*°?c|heißer tag|hohe außentemperatur", re.IGNORECASE)),
    ("Möglicherweise zu wenig getrunken", re.compile(r"zu wenig wasser|zu wenig getrunken|dehyd", re.IGNORECASE)),
    ("Unterbrochener Schlaf / Unruhe", re.compile(r"unruhe|verkehrslärm|schreiendes kind", re.IGNORECASE)),
)


@dataclass(frozen=True)
class InterpretationResult:
    onset_minute: int | None = None
    peak_start_minute: int | None = None
    peak_end_minute: int | None = None
    end_minute: int | None = None
    end_status: str = ""
    laterality: str = "unbekannt"
    side_detail: str = "Nicht dokumentiert"
    contexts: tuple[str, ...] = ()
    symptoms: tuple[str, ...] = ()
    interventions: tuple[str, ...] = ()
    confidence: str = "niedrig"
    extraction_method: str = "regelbasiert"

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("contexts", "symptoms", "interventions"):
            payload[key] = list(payload[key])
        return payload


class NoteInterpreter:
    def interpret(
        self,
        notes: str,
        entered_laterality: str | None = None,
        reviewed_annotation: dict[str, Any] | None = None,
    ) -> InterpretationResult:
        if reviewed_annotation:
            return self._from_reviewed(reviewed_annotation)

        laterality, side_detail = self._infer_laterality(notes, entered_laterality or "")
        onset, peak_start, peak_end, end, end_status = self._infer_times(notes)
        contexts = tuple(label for label, pattern in CONTEXT_PATTERNS if pattern.search(notes))
        symptoms: list[str] = []
        if re.search(r"\bübelkeit\b", notes, re.IGNORECASE) and not re.search(r"keine\s+übelkeit", notes, re.IGNORECASE):
            symptoms.append("Übelkeit")
        evidence = bool(notes and (laterality != "unbekannt" or onset is not None or contexts))
        return InterpretationResult(
            onset_minute=onset,
            peak_start_minute=peak_start,
            peak_end_minute=peak_end,
            end_minute=end,
            end_status=end_status,
            laterality=laterality,
            side_detail=side_detail,
            contexts=contexts,
            symptoms=tuple(symptoms),
            interventions=self._infer_interventions(notes),
            confidence="mittel" if evidence else "niedrig",
        )

    @staticmethod
    def _from_reviewed(data: dict[str, Any]) -> InterpretationResult:
        def minute(key: str) -> int | None:
            value = data.get(key)
            if value is None and key.endswith("Minute"):
                legacy_key = key.removesuffix("Minute") + "Hour"
                legacy = data.get(legacy_key)
                value = None if legacy is None else float(legacy) * 60
            return None if value in (None, "") else int(round(float(value)))

        return InterpretationResult(
            onset_minute=minute("onsetMinute"),
            peak_start_minute=minute("peakStartMinute"),
            peak_end_minute=minute("peakEndMinute"),
            end_minute=minute("endMinute"),
            end_status=str(data.get("endStatus") or ""),
            laterality=str(data.get("laterality") or "unbekannt"),
            side_detail=str(data.get("sideDetail") or "Nicht dokumentiert"),
            contexts=tuple(dict.fromkeys(str(value).strip() for value in data.get("contexts", []) if str(value).strip())),
            symptoms=tuple(dict.fromkeys(str(value).strip() for value in data.get("symptoms", []) if str(value).strip())),
            interventions=tuple(dict.fromkeys(str(value).strip() for value in data.get("interventions", []) if str(value).strip())),
            confidence=str(data.get("confidence") or "mittel"),
            extraction_method="semantisch geprüft",
        )

    @staticmethod
    def _infer_laterality(notes: str, entered_laterality: str) -> tuple[str, str]:
        text = notes.lower()
        if "beidseitig" in text or "beiden augen" in text:
            if re.search(r"links.{0,40}(stärker|ausgeprägter)|linken.{0,40}(stärker|ausgeprägter)", text):
                return "beidseitig_linksbetont", "beidseitig, links stärker"
            return "beidseitig", "beidseitig"
        if re.search(r"rechtsseitig|rechten kopfseite|ausschließlich.{0,25}rechten|rechtem auge|rechten auge", text):
            return "rechts", "rechtsseitig"
        if re.search(r"linksseitig|linken kopfseite|ausschließlich.{0,25}linken|linkem auge|linken auge", text):
            return "links", "linksseitig"
        if re.search(r"\brechts\b", text) and not re.search(r"\blinks\b", text):
            return "rechts", "rechts (aus Notiz abgeleitet)"
        if re.search(r"\blinks\b", text) and not re.search(r"\brechts\b", text):
            return "links", "links (aus Notiz abgeleitet)"

        side = entered_laterality.lower()
        if "rechts" in side:
            return "rechts", entered_laterality
        if "links" in side:
            return "links", entered_laterality
        if "beid" in side:
            return "beidseitig", entered_laterality
        if "einseit" in side:
            return "einseitig_unbekannt", "einseitig, Seite nicht dokumentiert"
        return "unbekannt", "Nicht dokumentiert"

    @staticmethod
    def _infer_times(notes: str) -> tuple[int | None, int | None, int | None, int | None, str]:
        normalized = SHARED_UHR_RANGE.sub(r"\1 Uhr–\2 Uhr", notes)
        onset = peak_start = peak_end = end = None
        end_status = ""
        for line in (line.strip() for line in normalized.splitlines() if line.strip()):
            line_times = [NoteInterpreter._clock_minute(match) for match in TIME_PATTERN.finditer(line)]
            headache_negated = re.search(r"keine.{0,30}kopfschmerz|ohne.{0,30}kopfschmerz", line, re.IGNORECASE)
            if line_times and ONSET_CONTEXT_PATTERN.search(line) and not headache_negated:
                onset = line_times[0]
                break
        segments = [segment.strip() for segment in re.split(r"[\n\r]+|(?<=[.!?])\s+", normalized) if segment.strip()]

        for segment in segments:
            times = [NoteInterpreter._clock_minute(match) for match in TIME_PATTERN.finditer(segment)]
            if not times:
                continue
            lower = segment.lower()
            if onset is None and ONSET_CONTEXT_PATTERN.search(lower):
                onset = times[0]
            if re.search(r"höhepunkt|stärkste intensität|höchsten intensität|sehr starke kopfschmerzen", lower):
                peak_start = times[0]
                if len(times) > 1:
                    peak_end = times[1]
            if re.search(
                r"vollständig.{0,25}(verschwunden|abgeklungen)|ohne kopfschmerzen aufgewacht|"
                r"nahezu vollständig verschwunden|so gut wie verschwunden|\bverschwanden\b|"
                r"klangen.{0,40}(vollständig|von selbst)?.{0,15}ab",
                lower,
            ):
                end = times[-1]
                end_status = "vollständig" if re.search(r"vollständig|ohne kopfschmerzen|verschwanden", lower) else "nahezu vollständig"
            elif re.search(r"\bende\b.{0,18}\b[0-2]?\d(?::[0-5]\d)?\s*uhr|endeten|hörten.{0,25}auf", lower):
                end = times[-1]
                end_status = "dokumentiert"
            elif re.search(r"\bhielt(?:en)?\s+bis(?:\s+(?:etwa|ca\.?))?", lower):
                end = times[-1]
                end_status = "dokumentiert"

        if onset is not None:
            if peak_start is not None and peak_start < onset:
                peak_start += 1440
            if peak_end is not None and peak_start is not None and peak_end < peak_start:
                peak_end += 1440
            if end is not None and end <= onset:
                end += 1440
        return onset, peak_start, peak_end, end, end_status

    @staticmethod
    def _clock_minute(match: re.Match[str]) -> int:
        return int(match.group(1)) * 60 + int(match.group(2) or 0)

    @staticmethod
    def _infer_interventions(notes: str) -> tuple[str, ...]:
        mappings = (
            ("Schlaf", r"geschlafen|eingeschlafen|schlaf"),
            ("Akutmedikation", r"medikament|tablette|eletriptan|paracetamol|parazetamol"),
            ("Wärme", r"wärmebehandlung|warmwasserflasche|heiße dusche|heiß geduscht"),
            ("Bad", r"\bgebadet\b|\bbad\b"),
            ("Tigerbalsam", r"tigerbalsam"),
        )
        return tuple(label for label, pattern in mappings if re.search(pattern, notes, re.IGNORECASE))
