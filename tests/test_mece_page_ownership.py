"""Purpose: Tests for MECE page ownership and chart assignments.

Usage: Verifies charts are assigned to correct pages.

Functions available:
- test_chart_ownership_matches_navigation

Classes available:
- None

Call hierarchy:
- test_mece_page_ownership.py -> frontend.components.charts
"""

from pathlib import Path

EXPECTED_OWNERS = {
    "observation_days_bar": "overview",
    "monthly_frequency_chart": "trends",
    "rolling_line": "trends",
    "weekday_rate_chart": "trends",
    "attack_timeline": "attack_timeline",
    "monthly_metric_scatter": "strength_duration",
    "duration_by_date_bar": "strength_duration",
    "histogram": "strength_duration",
    "strength_duration_scatter": "strength_duration",
    "pattern_source_chart": "triggers_context",
    "medication_effectiveness_chart": "medication",
    "completeness_chart": "data_quality",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE_PATH = PROJECT_ROOT / "app.py"
FILTER_SOURCE_PATH = PROJECT_ROOT / "frontend" / "components" / "filters.py"
PAGES_DIR = PROJECT_ROOT / "frontend" / "pages"
NAVIGATION_LABELS = [
    'tr(cfg, "Verlauf und Muster", "Trends and patterns")',
    'tr(cfg, "Merkmale und Behandlung", "Characteristics and treatment")',
    'tr(cfg, "Einträge und Daten", "Entries and data")',
    'tr(cfg, "Häufigkeit im Zeitverlauf", "Frequency over time")',
    'tr(cfg, "Tagesverlauf der Kopfschmerzen", "Timing of headaches")',
    'tr(cfg, "Mögliche Auslöser", "Possible triggers")',
]
CRYPTIC_LABELS = (
    "Y-Achse",
    "Spearman-Korrelation",
    "Muster nach Datenquelle",
    "Medikamentenübergebrauchs-Orientierung",
)


def test_domain_specific_charts_have_one_page_owner() -> None:
    page_sources = {
        path.stem: path.read_text(encoding="utf-8")
        for path in PAGES_DIR.glob("*.py")
        if path.stem != "__init__"
    }
    for chart_name, expected_owner in EXPECTED_OWNERS.items():
        owners = {page_name for page_name, source in page_sources.items() if chart_name in source}
        assert owners == {expected_owner}, f"{chart_name} is owned by {owners}, expected {expected_owner}"


def test_navigation_names_reflect_the_mece_domains() -> None:
    app_source = APP_SOURCE_PATH.read_text(encoding="utf-8")
    for label in NAVIGATION_LABELS:
        assert label in app_source


def test_report_pages_avoid_unexplained_technical_headings() -> None:
    page_sources = {
        path.stem: path.read_text(encoding="utf-8")
        for path in PAGES_DIR.glob("*.py")
    }
    report_source = "\n".join(page_sources.values())
    for cryptic_label in CRYPTIC_LABELS:
        assert cryptic_label not in report_source


def test_global_sidebar_has_complete_report_settings_before_navigation() -> None:
    app_source = APP_SOURCE_PATH.read_text(encoding="utf-8")
    filter_source = FILTER_SOURCE_PATH.read_text(encoding="utf-8")

    assert app_source.index("st.segmented_control") < app_source.index("st.page_link")
    assert app_source.index("render_user_settings(session)") < app_source.index("st.page_link")
    assert app_source.index("render_report_period(active_user)") < app_source.index("st.page_link")
    assert "st.slider" not in filter_source
    assert "st.multiselect" not in filter_source
    assert "Stärkebereich" not in filter_source
    assert "Auslöser auswählen" not in filter_source
