# Kopfschmerz-Tracker

[![Tests](https://github.com/csiddharthn/migraine-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/csiddharthn/migraine-tracker/actions/workflows/tests.yml)

Mehrseitige Streamlit-Anwendung zur Erfassung und Auswertung von Kopfschmerz- und Migräneeinträgen. Die gesamte Oberfläche kann auf Deutsch oder Englisch verwendet werden; PostgreSQL ist die einzige Datenquelle im laufenden Betrieb.

## Datenschutz im Repository

Dieses Repository enthält absichtlich keine Gesundheitsdaten, Personennamen, Quelldokumente, Datenbankdateien, Sicherungen, Audioaufnahmen oder API-Schlüssel. Solche Dateien bleiben ausschließlich lokal und werden durch `.gitignore` ausgeschlossen. `.env.example` enthält nur Platzhalter.

## Voraussetzungen

- Python 3.11 oder neuer
- Windows PowerShell für die mitgelieferten Hilfsskripte
- Internetzugang für die einmalige Installation

Docker Desktop ist optional. Das mitgelieferte Installationsskript richtet die offizielle portable PostgreSQL-Distribution lokal im Projekt ein, ohne eine systemweite Installation vorzunehmen.

## 1. Python-Umgebung installieren

Im Projektordner:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 2. PostgreSQL lokal installieren

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install_portable_postgres.ps1
```

Das Skript lädt die offizielle Windows-Binärdistribution, legt Haupt- und Testdatenbank an und erzeugt eine lokale `.env` mit zufälligem Passwort. `.env`, Datenbankdateien und Laufzeitdateien werden von Git ignoriert. Passwörter und echte Datenbank-URLs dürfen nicht in YAML-, JSON- oder Quelldateien eingetragen werden.

Alternativ kann `MIGRAINE_DATABASE_URL` in `.streamlit/secrets.toml` als Streamlit Secret hinterlegt werden.

## 3. PostgreSQL starten und Ersteinrichtung ausführen

Danach kann der gesamte Erstlauf mit einem Befehl ausgeführt werden:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\initial_setup.ps1
```

Das Skript startet PostgreSQL, wartet auf die Datenbank und bringt das Schema mit Alembic auf den aktuellen Stand. Personen und Kopfschmerzeinträge werden anschließend direkt in der Anwendung angelegt.

Die portable Datenbank lässt sich später separat starten und beenden:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_postgres.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\stop_postgres.ps1
```

PostgreSQL ist lokal über Port `5433` erreichbar, damit eine bestehende Standardinstallation auf `5432` nicht gestört wird.

Als optionale Alternative kann PostgreSQL mit `docker compose up -d` gestartet werden; dazu `.env.example` nach `.env` kopieren und ein eigenes Passwort einsetzen.

## 4. Datenbankmigrationen ausführen

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Alembic erstellt Tabellen mit Constraints und Indizes sowie Auslöserdefinitionen, getrennte Notizinterpretationen und ein Änderungsprotokoll.

## 5. Streamlit starten

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternativ `Kopfschmerz-Tracker starten.cmd` doppelt anklicken. Das Skript öffnet anschließend `http://localhost:8501`.

## Bereiche

Die Detailseiten sind nach analytischer Fragestellung überschneidungsfrei gegliedert. Die Übersicht ist bewusst nur eine verdichtete Zusammenfassung und enthält keine Detaildiagramme.

1. Übersicht: zentrale Kennzahlen
2. Häufigkeit im Zeitverlauf: Kopfschmerztage pro Monat, durchschnittlicher Abstand und Wochentage
3. Tagesverlauf der Kopfschmerzen: Beginn, stärkster Zeitpunkt und Ende
4. Stärke und Dauer: zeitlicher Verlauf, Verteilungen und Zusammenhang beider Kennzahlen
5. Mögliche Auslöser: ausgewählte Auslöser und in Notizen erwähnte Begleitumstände
6. Schmerzart und Symptome: Schmerzseite, Schmerzart, Aura und Begleitsymptome
7. Medikamente und Behandlung: mehrere Einnahmen pro Kopfschmerztag, jeweilige Uhrzeit, Dosis, Wirkung und Behandlungszeiträume
8. Einträge: Erfassung, Bearbeitung und Verwaltung möglicher Auslöser
9. Gespeicherte Daten: schreibgeschützte Ansicht der gespeicherten Angaben
10. Datenprüfung und Berechnung: Vollständigkeit, Definitionen und Grenzen

Sprache, aktive Person und Auswertungszeitraum stehen oberhalb der Seitennavigation. Dort kann auch eine neue Person samt Beginn ihres Beobachtungszeitraums angelegt werden. Alle Formulare, Listen, Kennzahlen und Diagramme sind strikt auf diese Person begrenzt; zwei Personen dürfen daher auch am selben Datum jeweils einen eigenen Eintrag besitzen. Der Zeitraum ist der einzige globale Berichtsfilter. Stärke und Auslöser werden nicht global ausgeschlossen, damit die Berichte stets alle Migränefälle im gewählten Zeitraum berücksichtigen.

Die Sprache wird über `Sprache / Language` in der Seitenleiste gewechselt. Navigation, Formulare, Diagramme, Tabellen, Kategorien, Datums- und Zahlenformate wechseln unmittelbar zwischen Deutsch und Englisch. Gespeicherte Originalnotizen und frei eingegebene Inhalte werden bewusst nicht verändert.

Im Bereich `Einträge` werden Datensätze für die ausgewählte Person erstellt und bearbeitet. Datum, Auslöser, Stärke und Dauer sind Pflichtangaben; das Datum ist mit dem heutigen Tag vorbelegt. Bestehende Einträge werden am selben Datensatz aktualisiert. Automatische Notizinterpretationen lassen sich getrennt von der unveränderten Originalnotiz prüfen und korrigieren.

### KI-gestützten Eintrag einrichten

Der Reiter `KI-gestützter Eintrag` wandelt einen frei formulierten deutschen oder englischen Text in einen vorausgefüllten Entwurf um. Er erkennt unter anderem Datum, Stärke, Dauer, Auslöser, Schmerzbild, Begleitsymptome, Zeitverlauf, Höhepunkt sowie mehrere Medikamenteneinnahmen. Offene Pflichtangaben oder wesentliche Mehrdeutigkeiten werden als Rückfragen angezeigt. Die KI speichert nie selbst: Erst der ausdrücklich geprüfte und über die normale Formularschaltfläche gespeicherte Entwurf wird in PostgreSQL geschrieben.

Unabhängig von der Sprache der Eingabe wird der strukturierte Formularentwurf auf Deutsch vereinheitlicht. Das gilt auch für frei formulierte Zeitverlaufsnotizen, mögliche Auslöser, Dosis/Form, Begleitumstände sowie Symptome und Maßnahmen. Medikamentennamen, Zahlen, Einheiten und Uhrzeiten bleiben unverändert. Der ursprüngliche englische oder gemischtsprachige Eingabetext wird nicht überschrieben und kann getrennt vom deutschen Entwurf gespeichert werden. Übersetzung und Strukturierung erfolgen gemeinsam in derselben Groq-Anfrage; dadurch entsteht kein zusätzlicher API-Aufruf.

Alternativ kann die Beschreibung direkt im Browser eingesprochen werden. Die Aufnahme wird nach Einwilligung über Groq transkribiert und als vollständig bearbeitbarer Text in dasselbe Eingabefeld übernommen; die Audiodatei selbst wird nicht in PostgreSQL gespeichert. Für höchste Genauigkeit wird zuerst `whisper-large-v3` verwendet. Falls dieses Modell vorübergehend nicht verfügbar oder durch ein Nutzungslimit blockiert ist, folgt automatisch `whisper-large-v3-turbo`. Die Sprache kann automatisch erkannt oder ausdrücklich als Deutsch beziehungsweise Englisch angegeben werden.

Für die Funktion wird ein eigener Groq-API-Schlüssel benötigt. Er kann in der [Groq Console](https://console.groq.com/keys) angelegt werden. Den Schlüssel nicht in den Quellcode und nicht in `backend/config/app.yaml` eintragen. Stattdessen lokal eine der folgenden Zeilen ergänzen und Streamlit anschließend neu starten:

```dotenv
# .env
GROQ_API_KEY=gsk_...
```

oder:

```toml
# .streamlit/secrets.toml
GROQ_API_KEY = "gsk_..."
```

Das Werkzeug verwendet ausschließlich Groq. Im Eingabereiter kann das bevorzugte Modell gewählt werden. Standardmäßig wird zuerst `openai/gpt-oss-120b` verwendet; bei einem vorübergehenden Fehler oder Nutzungslimit probiert die Anwendung automatisch `openai/gpt-oss-20b`. Beide Modelle unterstützen die hier verwendeten strikt strukturierten Ausgaben. Der Präfix `openai/` ist dabei nur Bestandteil der von Groq vorgegebenen Modell-ID; alle Anfragen gehen ausschließlich an Groq. Die Modelllisten für Texterkennung und Sprache, die Standardmodelle, das Zeitlimit und die Promptversion stehen als nicht geheime Einstellungen unter `ai_intake` in `backend/config/app.yaml`. Welche Modelle im kostenlosen Tarif verfügbar sind und welche Limits gelten, bestimmt Groq; die aktuellen Grenzen stehen im Groq-Konto.

Der Gesundheitstext wird erst nach einer sichtbaren Einwilligung an die Groq-API gesendet. Die KI erstellt ausschließlich einen prüfpflichtigen Entwurf. Der ursprüngliche Eingabetext kann beim Speichern wahlweise getrennt vom erzeugten Notiztext in PostgreSQL aufbewahrt werden; Groq als Anbieter, das tatsächlich verwendete Modell, Promptversion, strukturierter Entwurf und Prüfzeitpunkt werden zur Nachvollziehbarkeit protokolliert.

Der Bereich `Gespeicherte Daten` bietet einen schreibgeschützten Einblick in die vorhandenen Angaben. Personenbezogene Tabellen folgen der in der Seitenleiste ausgewählten Person; technische IDs und Referenzfelder können bei Bedarf eingeblendet werden.

## Sicherung

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup_database.ps1
```

Sicherungen werden unter `backups/` abgelegt. Das Skript lehnt absichtlich Ziele außerhalb dieses Ordners ab.

## Wiederherstellung

Zuerst Streamlit beenden, anschließend ausführen:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\restore_database.ps1 `
  -InputFile "backups\migraine_tracker_YYYYMMDD_HHMMSS.sql"
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Die Standardsuite verwendet eine isolierte SQLAlchemy-Datenbank. PostgreSQL-Integrationstests verwenden die konfigurierte Variable `MIGRAINE_TEST_DATABASE_URL`. Visuelle Prüfungen benötigen eine laufende Testinstanz.

GitHub Actions führt die vollständige im Repository enthaltene Testsuite bei jedem Push und jedem Pull Request aus. Der Workflow startet dafür PostgreSQL 17, prüft die Alembic-Migrationen und lädt den Pytest-Bericht für 14 Tage als Workflow-Artefakt hoch. Private Gesundheitsdaten sind nicht Bestandteil des Repositorys.

## Abhängigkeiten aktualisieren

Änderungen vor der Installation prüfen:

```powershell
.\.venv\Scripts\python.exe -m pip list --outdated
.\.venv\Scripts\python.exe -m pip install --upgrade -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Nach Änderungen am Datenmodell eine Alembic-Migration erstellen und prüfen; `Base.metadata.create_all` nicht gegen die produktive PostgreSQL-Datenbank ausführen:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Beschreibung"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Architektur

- `frontend/`: Streamlit-Seiten, Formulare und wiederverwendbare Diagrammkomponenten
- `backend/models/`: SQLAlchemy-Modelle und Constraints
- `backend/repositories/`: Datenbankabfragen
- `backend/services/`: Erstellen, Aktualisieren, Analysen und Änderungsprotokoll
- `backend/analytics/`: deterministische Berechnungen für Seiten und Tests
- `backend/note_interpretation/`: regelbasierte Extraktion von Uhrzeiten, Seite, Kontexten und Maßnahmen
- `backend/ai_intake/`: strukturierte, prüfpflichtige KI-Entwürfe aus frei formulierten Beschreibungen
- `migrations/`: Alembic-Schemahistorie
- `scripts/`: lokale Einrichtung, Start, Sicherung und Wiederherstellung
- `docs/`: Methodik und Architekturentscheidungen

Die Entscheidung gegen zusätzliche Bronze-, Silver- und Gold-Schichten ist in `docs/medallion_decision.md` dokumentiert. Fachliche Bezugspunkte stehen in `docs/methodology_references.md`.
