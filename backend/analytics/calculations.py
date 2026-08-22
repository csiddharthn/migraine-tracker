from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median
from typing import Any, Callable, Iterable

from backend.models import DailyRecord, MigraineEntry


WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
LATERALITY_LABELS = {
    "rechts": "Rechts",
    "links": "Links",
    "beidseitig": "Beidseitig",
    "beidseitig_linksbetont": "Beidseitig, linksbetont",
    "einseitig_unbekannt": "Einseitig, Seite offen",
    "unbekannt": "Nicht dokumentiert",
}


@dataclass(frozen=True)
class AnalyticsDataset:
    entries: tuple[MigraineEntry, ...]
    daily_records: tuple[DailyRecord, ...]
    first_day: date
    analysis_end: date

    @classmethod
    def build(
        cls,
        entries: Iterable[MigraineEntry],
        daily_records: Iterable[DailyRecord],
        *,
        first_day: date | None = None,
        analysis_end: date | None = None,
    ) -> AnalyticsDataset:
        entry_items = tuple(sorted(entries, key=lambda item: item.entry_date))
        daily_items = tuple(sorted(daily_records, key=lambda item: item.record_date))
        dates = [item.record_date for item in daily_items] or [item.entry_date for item in entry_items]
        resolved_first = first_day or (min(dates) if dates else date.today())
        resolved_end = analysis_end or (max(dates) if dates else resolved_first)
        if resolved_end < resolved_first:
            resolved_end = resolved_first
        return cls(entry_items, daily_items, resolved_first, resolved_end)

    @property
    def period_days(self) -> int:
        return (self.analysis_end - self.first_day).days + 1


def summary_stats(data: AnalyticsDataset) -> dict[str, Any]:
    strengths = [entry.strength for entry in data.entries]
    durations = [float(entry.duration_hours) for entry in data.entries]
    intervals = [
        (later.entry_date - earlier.entry_date).days
        for earlier, later in zip(data.entries, data.entries[1:])
        if later.entry_date > earlier.entry_date
    ]
    headache_days = len({entry.entry_date for entry in data.entries})
    medication_entries = [entry for entry in data.entries if entry.medications]
    medication_intakes = [item for entry in medication_entries for item in entry.medications]
    return {
        "period_days": data.period_days,
        "headache_days": headache_days,
        "headache_free_days": max(0, data.period_days - headache_days),
        "days_per_headache": data.period_days / headache_days if headache_days else None,
        "rate_per_30": headache_days / data.period_days * 30 if data.period_days else 0,
        "avg_strength": mean(strengths) if strengths else None,
        "median_strength": median(strengths) if strengths else None,
        "max_strength": max(strengths) if strengths else None,
        "intensity_8_to_10_days": sum(value >= 8 for value in strengths),
        "avg_duration": mean(durations) if durations else None,
        "median_duration": median(durations) if durations else None,
        "total_duration": sum(durations),
        "intensity_hours": sum(entry.strength * float(entry.duration_hours) for entry in data.entries),
        "acute_med_days": len(medication_entries),
        "helped_yes": sum((item.effectiveness or "").lower() == "ja" for item in medication_intakes),
        "helped_no": sum((item.effectiveness or "").lower() == "nein" for item in medication_intakes),
        "median_interval": median(intervals) if intervals else None,
        "longest_headache_free_streak": longest_headache_free_streak(data),
    }


def monthly_summaries(data: AnalyticsDataset) -> list[dict[str, Any]]:
    by_month_entries: dict[str, list[MigraineEntry]] = defaultdict(list)
    by_month_days: Counter[str] = Counter()
    current = data.first_day
    while current <= data.analysis_end:
        by_month_days[current.strftime("%Y-%m")] += 1
        current += timedelta(days=1)
    for entry in data.entries:
        by_month_entries[entry.entry_date.strftime("%Y-%m")].append(entry)
    result = []
    for month_key in sorted(by_month_days):
        items = by_month_entries.get(month_key, [])
        observed = by_month_days[month_key]
        result.append(
            {
                "key": month_key,
                "label": format_month_key(month_key),
                "observed_days": observed,
                "headache_days": len(items),
                "rate_per_30": len(items) / observed * 30 if observed else 0,
                "avg_strength": mean(entry.strength for entry in items) if items else None,
                "avg_duration": mean(float(entry.duration_hours) for entry in items) if items else None,
                "total_duration": sum(float(entry.duration_hours) for entry in items),
            }
        )
    return result


def rolling_frequency(data: AnalyticsDataset, window_days: int = 14) -> list[dict[str, Any]]:
    episode_days = {entry.entry_date for entry in data.entries}
    result = []
    current = data.first_day
    while current <= data.analysis_end:
        start = max(data.first_day, current - timedelta(days=window_days - 1))
        result.append({"date": current, "count": sum(start <= day <= current for day in episode_days)})
        current += timedelta(days=1)
    return result


def rolling_interval(data: AnalyticsDataset, window_days: int = 28) -> list[dict[str, Any]]:
    episode_days = {entry.entry_date for entry in data.entries}
    result = []
    current = data.first_day
    while current <= data.analysis_end:
        start = max(data.first_day, current - timedelta(days=window_days - 1))
        observed = (current - start).days + 1
        count = sum(start <= day <= current for day in episode_days)
        result.append({"date": current, "days_per_headache": observed / count if count else None})
        current += timedelta(days=1)
    return result


def correlation_summary(entries: Iterable[MigraineEntry]) -> dict[str, Any]:
    items = list(entries)
    if len(items) < 3:
        return {"n": len(items), "pearson": None, "spearman": None, "slope": None, "intercept": None}
    strengths = [float(entry.strength) for entry in items]
    durations = [float(entry.duration_hours) for entry in items]
    slope, intercept = linear_regression(strengths, durations)
    return {
        "n": len(items),
        "pearson": pearson(strengths, durations),
        "spearman": pearson(rank_values(strengths), rank_values(durations)),
        "slope": slope,
        "intercept": intercept,
    }


def group_summary(entries: Iterable[MigraineEntry], key: Callable[[MigraineEntry], str]) -> list[dict[str, Any]]:
    groups: dict[str, list[MigraineEntry]] = defaultdict(list)
    for entry in entries:
        groups[key(entry) or "Nicht dokumentiert"].append(entry)
    result = []
    for label, items in groups.items():
        result.append(
            {
                "label": label,
                "count": len(items),
                "avg_strength": mean(item.strength for item in items),
                "avg_duration": mean(float(item.duration_hours) for item in items),
                "total_duration": sum(float(item.duration_hours) for item in items),
            }
        )
    return sorted(result, key=lambda item: (-item["count"], item["label"]))


def trigger_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    expanded: dict[str, list[MigraineEntry]] = defaultdict(list)
    labels: dict[str, str] = {}
    for entry in entries:
        for trigger in entry.triggers:
            expanded[trigger.trigger_code].append(entry)
            labels[trigger.trigger_code] = trigger.definition.label
    result = _expanded_summary(expanded)
    for item in result:
        item["code"] = item["label"]
        item["label"] = labels[item["code"]]
    return result


def context_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    entry_items = list(entries)
    expanded: dict[str, list[MigraineEntry]] = defaultdict(list)
    for entry in entry_items:
        if entry.interpretation:
            for context in entry.interpretation.contexts:
                expanded[context].append(entry)
    result = _expanded_summary(expanded)
    for item in result:
        item["share"] = item["count"] / max(1, len(entry_items))
    return result


def laterality_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    def laterality(entry: MigraineEntry) -> str:
        derived = entry.interpretation.laterality if entry.interpretation else None
        if derived:
            return LATERALITY_LABELS.get(derived, derived)
        entered = (entry.entered_laterality or "").lower()
        if "rechts" in entered:
            return "Rechts"
        if "links" in entered:
            return "Links"
        if "beid" in entered:
            return "Beidseitig"
        if "einseit" in entered:
            return "Einseitig, Seite offen"
        return "Nicht dokumentiert"

    return group_summary(entries, laterality)


def weekday_summary(data: AnalyticsDataset) -> list[dict[str, Any]]:
    observed: Counter[int] = Counter()
    current = data.first_day
    while current <= data.analysis_end:
        observed[current.weekday()] += 1
        current += timedelta(days=1)
    headaches = Counter(entry.entry_date.weekday() for entry in data.entries)
    return [
        {
            "label": WEEKDAYS[index],
            "observed_days": observed[index],
            "headache_days": headaches[index],
            "rate": headaches[index] / observed[index] if observed[index] else 0,
        }
        for index in range(7)
    ]


def onset_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    bins = (
        ("Nacht (00–05:59)", 0, 360),
        ("Morgen (06–11:59)", 360, 720),
        ("Nachmittag (12–17:59)", 720, 1080),
        ("Abend (18–23:59)", 1080, 1440),
    )
    values = [entry.interpretation.onset_minute % 1440 for entry in entries if entry.interpretation and entry.interpretation.onset_minute is not None]
    return [{"label": label, "count": sum(start <= value < end for value in values)} for label, start, end in bins]


def pain_type_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    return group_summary(entries, lambda entry: entry.pain_type or "Nicht dokumentiert")


def symptom_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for entry in entries:
        if entry.vomiting:
            counter["Erbrechen"] += 1
        if entry.nausea:
            counter["Übelkeit"] += 1
        if entry.phonophobia:
            counter["Lärmscheu"] += 1
        if entry.photophobia:
            counter["Lichtscheu"] += 1
        if entry.osmophobia:
            counter["Geruchsempfindlichkeit"] += 1
        for code in entry.aura_codes:
            counter[f"Vorboten: {code}"] += 1
        for code in entry.other_symptom_codes:
            counter[f"Andere Symptome: {code}"] += 1
        if entry.interpretation:
            counter.update(entry.interpretation.symptoms)
    return [{"label": label, "count": count} for label, count in counter.most_common()]


def medication_summary(entries: Iterable[MigraineEntry]) -> list[dict[str, Any]]:
    groups: dict[str, list[tuple[MigraineEntry, Any]]] = defaultdict(list)
    for entry in entries:
        for intake in entry.medications:
            label = intake.name + (f" ({intake.dose})" if intake.dose else "")
            groups[label].append((entry, intake))
    result = []
    for label, items in groups.items():
        unique_entries = {entry.id: entry for entry, _ in items}.values()
        result.append(
            {
                "label": label,
                "days": len(list(unique_entries)),
                "helped_yes": sum((intake.effectiveness or "").lower() == "ja" for _, intake in items),
                "helped_partial": sum((intake.effectiveness or "").lower() == "teilweise" for _, intake in items),
                "helped_no": sum((intake.effectiveness or "").lower() == "nein" for _, intake in items),
                "avg_strength": mean(entry.strength for entry in {entry.id: entry for entry, _ in items}.values()),
            }
        )
    return sorted(result, key=lambda item: (-item["days"], item["label"]))


def data_quality(data: AnalyticsDataset) -> dict[str, Any]:
    total = len(data.entries)
    medication_days = [entry for entry in data.entries if entry.medications]
    return {
        "total": total,
        "notes": sum(bool(entry.notes) for entry in data.entries),
        "onset": sum(bool(entry.interpretation and entry.interpretation.onset_minute is not None) for entry in data.entries),
        "peak": sum(bool(entry.interpretation and entry.interpretation.peak_start_minute is not None) for entry in data.entries),
        "end": sum(bool(entry.interpretation and entry.interpretation.end_minute is not None) for entry in data.entries),
        "specific_side": sum(bool(entry.interpretation and entry.interpretation.laterality in {"rechts", "links", "beidseitig", "beidseitig_linksbetont"}) for entry in data.entries),
        "reviewed_interpretation": sum(bool(entry.interpretation and entry.interpretation.is_reviewed) for entry in data.entries),
        "medication_days": len(medication_days),
        "medication_response": sum(any(item.effectiveness for item in entry.medications) for entry in medication_days),
    }


def longest_headache_free_streak(data: AnalyticsDataset) -> int:
    episode_days = {entry.entry_date for entry in data.entries}
    longest = current_streak = 0
    current = data.first_day
    while current <= data.analysis_end:
        if current in episode_days:
            longest = max(longest, current_streak)
            current_streak = 0
        else:
            current_streak += 1
        current += timedelta(days=1)
    return max(longest, current_streak)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x, mean_y = mean(xs), mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    return numerator / denominator if denominator else None


def rank_values(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1][1] == ordered[index][1]:
            end += 1
        average_rank = (index + end + 2) / 2
        for position in range(index, end + 1):
            ranks[ordered[position][0]] = average_rank
        index = end + 1
    return ranks


def linear_regression(xs: list[float], ys: list[float]) -> tuple[float | None, float | None]:
    mean_x, mean_y = mean(xs), mean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if not denominator:
        return None, None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return slope, mean_y - slope * mean_x


def format_month_key(value: str) -> str:
    names = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
    year, month = value.split("-", 1)
    return f"{names[int(month) - 1]} {year}"


def _expanded_summary(groups: dict[str, list[MigraineEntry]]) -> list[dict[str, Any]]:
    result = []
    for label, items in groups.items():
        result.append(
            {
                "label": label,
                "count": len(items),
                "avg_strength": mean(item.strength for item in items),
                "avg_duration": mean(float(item.duration_hours) for item in items),
            }
        )
    return sorted(result, key=lambda item: (-item["count"], item["label"]))
