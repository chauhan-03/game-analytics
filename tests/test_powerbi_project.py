"""The generated Power BI Project must be valid before anyone opens it in Power BI Desktop.

JSON files are validated against Microsoft's published schemas (vendored in tests/schemas).
TMDL files are checked for the structural rules Power BI enforces on load.
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver

import powerbi_project as pp
from conftest import needs_outputs

SCHEMAS = Path(__file__).with_name("schemas")
BASE = "https://developer.microsoft.com/json-schemas/fabric/"


@pytest.fixture(scope="module", autouse=True)
def built():
    if (pp.EXPORTS / "daily_activity.csv").exists():
        pp.build()


def _store():
    store = {}
    for f in SCHEMAS.rglob("*.json"):
        schema = json.loads(f.read_text())
        url = BASE + f.relative_to(SCHEMAS).as_posix()
        store[url] = schema
        if "$id" in schema:
            store[schema["$id"]] = schema
    return store


STORE = _store()
JSON_FILES = sorted(p for p in pp.PROJECT.rglob("*.json") if "$schema" in p.read_text()[:400]) \
    + sorted(pp.PROJECT.glob("*/definition.pb*")) + sorted(pp.PROJECT.glob("*.pbip"))


def _uniq(paths):
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


@needs_outputs
@pytest.mark.parametrize("path", _uniq(JSON_FILES), ids=lambda p: str(p.relative_to(pp.PROJECT)))
def test_json_matches_microsoft_schema(path):
    doc = json.loads(path.read_text())
    url = doc["$schema"]
    assert url in STORE, f"schema not vendored: {url}"
    schema = STORE[url]
    errors = list(Draft7Validator(schema, resolver=RefResolver(url, schema, store=STORE)).iter_errors(doc))
    assert not errors, "\n".join(f"{list(e.absolute_path)}: {e.message[:200]}" for e in errors[:5])


# --------------------------------------------------------------------------- semantic model

def _unq(name: str) -> str:
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def model():
    """{table: {"columns": {...}, "measures": {name: dax}, "text": str}} parsed from the TMDL files."""
    out = {}
    for f in sorted((pp.MODEL / "definition" / "tables").glob("*.tmdl")):
        text = f.read_text()
        table = _unq(re.match(r"table (.+)", text).group(1))
        cols = {_unq(m) for m in re.findall(r"^\tcolumn (.+)$", text, re.M)}
        measures = {}
        for m in re.finditer(r"^\tmeasure ('(?:[^']|'')+'|\S+) =(.*)$((?:\n\t\t\t.*)*)", text, re.M):
            measures[_unq(m.group(1))] = (m.group(2) + m.group(3)).strip()
        out[table] = {"columns": cols, "measures": measures, "text": text}
    return out


@needs_outputs
def test_every_table_and_measure_generated():
    m = model()
    assert set(m) == set(pp.TABLES)
    assert sum(len(t["measures"]) for t in m.values()) == len(pp.parse_measures())


@needs_outputs
@pytest.mark.parametrize("table", pp.TABLES)
def test_table_tmdl_rules(table):
    t = model()[table]
    lines = t["text"].splitlines()
    assert all(not re.match(r"^ +\S", ln) for ln in lines), "indentation must use tabs"
    assert t["text"].count("\tpartition ") == 1 and "DataFolder" in t["text"]
    assert (pp.EXPORTS / f"{table}.csv").exists()
    clash = {c.lower() for c in t["columns"]} & {n.lower() for n in t["measures"]}
    assert not clash, f"column/measure name clash: {clash}"


@needs_outputs
def test_measure_names_unique_across_model():
    names = [n.lower() for t in model().values() for n in t["measures"]]
    assert len(names) == len(set(names))


@needs_outputs
def test_dax_references_resolve():
    m = model()
    all_measures = {n for t in m.values() for n in t["measures"]}
    for table in m.values():
        for name, dax in table["measures"].items():
            for t, c in re.findall(r"\b([a-z_]+)\[([^\]]+)\]", dax):
                assert c in m[t]["columns"], f"{name}: {t}[{c}] is not a column"
            for ref in re.findall(r"(?<![\w\]])\[([^\]]+)\]", dax):
                assert ref in all_measures, f"{name}: [{ref}] is not a measure"


# --------------------------------------------------------------------------- report

VISUALS = sorted((pp.REPORT / "definition" / "pages").glob("*/visuals/*/visual.json"))


@needs_outputs
def test_six_pages_in_order():
    meta = json.loads((pp.REPORT / "definition" / "pages" / "pages.json").read_text())
    names = [json.loads((pp.REPORT / "definition" / "pages" / p / "page.json").read_text())["displayName"]
             for p in meta["pageOrder"]]
    assert names == list(pp.PAGES)


@needs_outputs
@pytest.mark.parametrize("path", VISUALS, ids=lambda p: p.parent.name)
def test_visual_fields_exist_and_fit_page(path):
    m = model()
    v = json.loads(path.read_text())
    pos = v["position"]
    assert pos["x"] >= 0 and pos["y"] >= 0 and pos["x"] + pos["width"] <= 1280.5 and pos["y"] + pos["height"] <= 720.5
    for role in v["visual"]["query"]["queryState"].values():
        for proj in role["projections"]:
            f = proj["field"]
            if "Measure" in f:
                ref = f["Measure"]
                assert ref["Property"] in m[ref["Expression"]["SourceRef"]["Entity"]]["measures"]
            else:
                ref = f["Column"] if "Column" in f else f["Aggregation"]["Expression"]["Column"]
                assert ref["Property"] in m[ref["Expression"]["SourceRef"]["Entity"]]["columns"]
