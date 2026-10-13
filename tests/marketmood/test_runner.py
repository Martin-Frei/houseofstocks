# tests/marketmood/test_runner.py
"""
Tests für marketmood/pipeline/runner.py (F-07 Schritt 5, Bezug F-02).

Der Runner rechnet nichts selbst, er verbindet fünf Schritte. Getestet werden
seine Verträge: Datenkette, Reihenfolge, Zusammenfassung, Abbruch bei 0
Artikeln und dass Fehler ungefiltert nach oben gehen (kein try/except).

Alle fünf Schritte werden durch Mocks ersetzt – gepatcht im Modul runner,
weil runner.py die Namen per "from ... import" in seinen eigenen Namensraum holt.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from marketmood.pipeline.runner import run_pipeline

RUNNER = "marketmood.pipeline.runner"

# Absichtlich unterschiedliche Längen: Jede Zahl in der Zusammenfassung
# verrät, aus welcher Variable sie stammt.
ARTICLES = ["a1", "a2", "a3", "a4", "a5"]
ENRICHED = ["e1", "e2", "e3", "e4"]
ANALYZED = ["s1", "s2", "s3"]
SAVE_RESULT = {"saved": 3, "errors": 1}
SNAPSHOTS = ["snap1", "snap2"]


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def steps():
    """Ersetzt alle fünf Pipeline-Schritte für die Dauer eines Tests."""
    with (
        patch(f"{RUNNER}.fetch_all_sources", return_value=ARTICLES) as fetch,
        patch(f"{RUNNER}.enrich_articles", return_value=ENRICHED) as enrich,
        patch(f"{RUNNER}.analyze_all", return_value=ANALYZED) as analyze,
        patch(f"{RUNNER}.save_articles", return_value=SAVE_RESULT) as save,
        patch(f"{RUNNER}.run_aggregator", return_value=SNAPSHOTS) as aggregate,
    ):
        yield SimpleNamespace(
            fetch=fetch, enrich=enrich, analyze=analyze, save=save, aggregate=aggregate
        )
    # Nach yield: with-Block endet → Originale sind wieder da


# ── Normalfall ────────────────────────────────────────────────────────────────

def test_each_step_receives_result_of_previous_step(steps):
    run_pipeline()

    steps.fetch.assert_called_once_with()
    steps.enrich.assert_called_once_with(ARTICLES)
    steps.analyze.assert_called_once_with(ENRICHED)
    steps.save.assert_called_once_with(ANALYZED)
    steps.aggregate.assert_called_once_with(ANALYZED)


def test_steps_run_in_fixed_order(steps):
    # Ein Eltern-Mock zeichnet die Aufrufe aller Kinder in EINER Liste auf
    manager = Mock()
    for name in ("fetch", "enrich", "analyze", "save", "aggregate"):
        manager.attach_mock(getattr(steps, name), name)

    run_pipeline()

    called = [c[0] for c in manager.mock_calls]
    assert called == ["fetch", "enrich", "analyze", "save", "aggregate"]


def test_summary_counts_each_stage(steps):
    summary = run_pipeline()

    assert summary == {
        "fetched": 5,
        "enriched": 4,
        "analyzed": 3,
        "saved": 3,
        "save_errors": 1,
        "snapshots": 2,
    }


def test_summary_defaults_to_zero_when_save_result_is_empty(steps):
    steps.save.return_value = {}

    summary = run_pipeline()

    assert summary["saved"] == 0
    assert summary["save_errors"] == 0


# ── Fehlerpfade ───────────────────────────────────────────────────────────────

def test_aborts_before_enrich_when_no_articles(steps):
    steps.fetch.return_value = []

    with pytest.raises(RuntimeError, match="0 articles"):
        run_pipeline()

    steps.fetch.assert_called_once_with()  # beweist, dass der Mock gegriffen hat
    steps.enrich.assert_not_called()
    steps.analyze.assert_not_called()
    steps.save.assert_not_called()
    steps.aggregate.assert_not_called()


@pytest.mark.parametrize("failing_step", ["enrich", "analyze", "save", "aggregate"])
def test_error_in_step_propagates_unchanged(steps, failing_step):
    error = RuntimeError(f"{failing_step} kaputt")
    getattr(steps, failing_step).side_effect = error

    with pytest.raises(RuntimeError) as excinfo:
        run_pipeline()

    assert excinfo.value is error  # dasselbe Objekt, nicht verpackt oder ersetzt