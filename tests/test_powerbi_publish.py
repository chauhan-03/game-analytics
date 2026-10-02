"""The cloud copy of the Power BI project: no local-file reads, every table reads from the web
folder, and the report binds to the published model."""
import base64
import json

import pytest

import powerbi_publish as pub
from powerbi_project import TABLES

URL = "https://example.org/data/"


def decoded(parts):
    return {p["path"]: base64.b64decode(p["payload"]).decode("utf-8") for p in parts}


@pytest.fixture(scope="module")
def model():
    return decoded(pub.model_parts(URL))


@pytest.fixture(scope="module")
def report():
    return decoded(pub.report_parts("1234-abcd"))


def test_model_has_required_parts(model):
    for p in ["definition.pbism", "definition/database.tmdl", "definition/model.tmdl", "definition/expressions.tmdl"]:
        assert p in model


@pytest.mark.parametrize("table", TABLES)
def test_table_reads_only_from_web(model, table):
    text = model[f"definition/tables/{table}.tmdl"]
    assert "File.Contents" not in text
    assert f'Web.Contents(DataFolder, [RelativePath = "{table}.csv"]),' in text


def test_data_folder_points_at_url(model):
    assert f'expression DataFolder = "{URL}"' in model["definition/expressions.tmdl"]


def test_local_project_left_untouched():
    assert "File.Contents" in (pub.MODEL_DIR / "definition/tables/daily_activity.tmdl").read_text()


def test_no_local_settings_uploaded(model, report):
    assert not any(p.startswith(".pbi/") or p.endswith(".platform") for p in [*model, *report])


def test_report_binds_to_published_model(report):
    pbir = json.loads(report["definition.pbir"])
    assert pbir["datasetReference"] == {"byConnection": {"connectionString": "semanticmodelid=1234-abcd"}}


def test_report_carries_pages_and_themes(report):
    assert "definition/report.json" in report and "definition/pages/pages.json" in report
    assert sum(p.endswith("/visual.json") for p in report) == 37
    assert any(p.startswith("StaticResources/RegisteredResources/") for p in report)


def test_payloads_are_base64():
    for p in pub.model_parts(URL) + pub.report_parts("x"):
        assert p["payloadType"] == "InlineBase64"
        base64.b64decode(p["payload"], validate=True)
