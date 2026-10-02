"""docs/index.html must carry the same numbers as findings.json and stay self-contained."""

import json
import re

import pytest

from conftest import ROOT, needs_outputs

PAGE = ROOT / "docs" / "index.html"


@pytest.fixture(scope="module")
def page():
    return PAGE.read_text()


@pytest.fixture(scope="module")
def payload(page):
    blob = re.search(r"const DATA = (\{.*?\});\n", page, re.S).group(1)
    return json.loads(blob)


@needs_outputs
def test_data_injected(page):
    assert "/*__DATA__*/null" not in page


@needs_outputs
def test_dashboard_findings_match_findings_json(payload, findings):
    assert payload["findings"] == findings


@needs_outputs
@pytest.mark.parametrize("key", ["daily", "curve", "cohorts", "first_return", "segments",
                                 "progress", "d7_rounds", "money", "tiers", "payer_hist"])
def test_dashboard_tables_present(payload, key):
    assert payload[key]


@needs_outputs
def test_payer_histogram_counts_every_payer(payload, findings):
    m = findings["monetization"]
    assert sum(payload["payer_hist"]["a"]) == m["payers_a"]
    assert sum(payload["payer_hist"]["b"]) == m["payers_b"]


@needs_outputs
def test_only_allowed_external_hosts(page):
    hosts = set(re.findall(r'(?:src|href)="https://([^/"]+)', page))
    assert hosts <= {"fonts.googleapis.com", "fonts.gstatic.com", "www.kaggle.com", "github.com"}

