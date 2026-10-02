"""Numbers quoted in the product documents must match what the pipeline computes today."""

import pytest

from conftest import ROOT, needs_outputs
from experiment import sample_size_two_proportions

DOCS = ROOT / "product"


def _cases(f):
    o, r, e, v = f["onboarding"], f["retention"], f["engagement"], f["player_voice"]
    base = o["returned_within_7d"]
    return [
        ("01-onboarding-funnel-review.md", f"{f['window']['players_with_30_days']:,}"),
        ("01-onboarding-funnel-review.md", f"{o['never_returned_30d'] * 100:.1f}"),
        ("01-onboarding-funnel-review.md", f"{r['d1']:.1%}"),
        ("02-feature-spec-first-week-journey.md", f"{base:.1%}"),
        ("02-feature-spec-first-week-journey.md", f"{sample_size_two_proportions(base, base + 0.02):,}"),
        ("02-feature-spec-first-week-journey.md", f"{sample_size_two_proportions(base, base + 0.01):,}"),
        ("03-campaign-brief-welcome-week.md", f"{v['reviews']:,}"),
        ("04-competitive-review.md", f"{v['reviews']:,}"),
        ("05-player-personas-and-survey.md", f"{e['segments']['Core']['share_of_players']:.1%}"),
        ("05-player-personas-and-survey.md", f"{e['segments']['Regular']['share_of_logins']:.1%}"),
    ]


@needs_outputs
@pytest.mark.parametrize("i", range(10))
def test_doc_number_matches_pipeline(findings, i):
    doc, number = _cases(findings)[i]
    assert number in (DOCS / doc).read_text(), f"{doc} should quote {number}"
