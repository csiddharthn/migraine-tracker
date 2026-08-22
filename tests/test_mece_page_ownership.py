from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGE_SOURCES = {
    path.stem: path.read_text(encoding="utf-8")
    for path in (PROJECT_ROOT / "frontend" / "pages").glob("*.py")
}


def test_domain_specific_charts_have_one_page_owner() -> None:
    expected_owners = {
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

    for chart_name, expected_owner in expected_owners.items():
        owners = {page_name for page_name, source in PAGE_SOURCES.items() if chart_name in source}
        assert owners == {expected_owner}, f"{chart_name} is owned by {owners}, expected {expected_owner}"


def test_navigation_names_reflect_the_mece_domains() -> None:
    app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")

    assert 'tr("Verlauf und Muster", "Trends and patterns")' in app_source
    assert 'tr("Merkmale und Behandlung", "Characteristics and treatment")' in app_source
    assert 'tr("Einträge und Daten", "Entries and data")' in app_source
    assert 'tr("Häufigkeit im Zeitverlauf", "Frequency over time")' in app_source
    assert 'tr("Tagesverlauf der Kopfschmerzen", "Timing of headaches")' in app_source
    assert 'tr("Mögliche Auslöser", "Possible triggers")' in app_source


def test_report_pages_avoid_unexplained_technical_headings() -> None:
    report_source = "\n".join(PAGE_SOURCES.values())

    for cryptic_label in ("Y-Achse", "Spearman-Korrelation", "Muster nach Datenquelle", "Medikamentenübergebrauchs-Orientierung"):
        assert cryptic_label not in report_source


def test_global_sidebar_has_complete_report_settings_before_navigation() -> None:
    app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    filter_source = (PROJECT_ROOT / "frontend" / "components" / "filters.py").read_text(encoding="utf-8")

    assert app_source.index("st.segmented_control") < app_source.index("st.page_link")
    assert app_source.index("render_user_settings(session)") < app_source.index("st.page_link")
    assert app_source.index("render_report_period(active_user)") < app_source.index("st.page_link")
    assert "st.slider" not in filter_source
    assert "st.multiselect" not in filter_source
    assert "Stärkebereich" not in filter_source
    assert "Auslöser auswählen" not in filter_source
