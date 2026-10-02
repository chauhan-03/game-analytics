"""python src/powerbi_project.py  ->  powerbi/GameAnalytics.pbip

Builds a Power BI Project (PBIP) from the pipeline's exports, so the dashboard opens
in Power BI Desktop with no manual setup:

    GameAnalytics.SemanticModel/   TMDL: one table per CSV in outputs/powerbi (loaded with
                                   Power Query), every measure from powerbi/measures.dax
    GameAnalytics.Report/          PBIR: six report pages with cards, charts and tables
                                   already bound to those measures and columns

The data folder is a Power Query parameter (DataFolder). Point it at your local
outputs/powerbi folder, or at a URL that serves the CSVs.
tests/test_powerbi_project.py validates every JSON file against Microsoft's schemas.
"""

import hashlib
import json
import re
import shutil

import pandas as pd

import data

ROOT = data.ROOT
EXPORTS = ROOT / "outputs" / "powerbi"
PROJECT = ROOT / "powerbi"
NAME = "GameAnalytics"
MODEL = PROJECT / f"{NAME}.SemanticModel"
REPORT = PROJECT / f"{NAME}.Report"
ASSETS = PROJECT / "assets"
DAX_FILE = PROJECT / "measures.dax"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"

TABLES = ["daily_activity", "retention_curve", "cohort_retention", "new_players", "cookie_cats_players",
          "ab_test_players", "kpi_summary", "review_themes", "review_games"]
DATE_COLS = {"date", "reg_date", "cohort_week"}
ID_COLS = {"uid", "user_id", "userid", "day_n", "first_return_day", "game_id"}
RATE_HINTS = ("retention", "share", "conversion", "stickiness")
DEFAULT_FOLDER = "C:\\game-analytics\\outputs\\powerbi\\"


# --------------------------------------------------------------------------- semantic model (TMDL)

def q(name: str) -> str:
    """TMDL object name, single-quoted when it has anything but letters, digits or _."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def column_types(table: str) -> list[tuple[str, str, str]]:
    """(column, TMDL dataType, Power Query type) for each CSV column."""
    sample = pd.read_csv(EXPORTS / f"{table}.csv", nrows=20_000)
    out = []
    for col, dtype in sample.dtypes.items():
        if col in DATE_COLS:
            out.append((col, "dateTime", "type date"))
        elif dtype == bool:
            out.append((col, "boolean", "type logical"))
        elif pd.api.types.is_integer_dtype(dtype):
            out.append((col, "int64", "Int64.Type"))
        elif pd.api.types.is_float_dtype(dtype):
            out.append((col, "double", "type number"))
        else:
            out.append((col, "string", "type text"))
    return out


def column_format(col: str, dtype: str) -> str | None:
    if col in ID_COLS:
        return "0"
    if dtype == "dateTime":
        return "yyyy-mm-dd"
    if dtype == "int64":
        return "#,0"
    if dtype == "double":
        return "0.0%" if any(h in col for h in RATE_HINTS) else "#,0.00"
    return None


def parse_measures() -> list[tuple[str, str]]:
    """(name, DAX) for every measure in measures.dax. Measures are separated by blank lines."""
    out = []
    for block in re.split(r"\n\s*\n", DAX_FILE.read_text()):
        lines = [ln.rstrip() for ln in block.strip().splitlines() if not ln.lstrip().startswith("//")]
        if not lines:
            continue
        name, _, first = lines[0].partition(" =")
        expr = "\n".join([first.strip()] + lines[1:]).strip()
        out.append((name.strip(), expr))
    return out


def measure_format(name: str) -> str:
    n = name.lower()
    if "p-value" in n:
        return "0.000"
    if "(pp)" in n or "lift" in n:
        return "+0.0%;-0.0%;0.0%"
    if "conversion" in n:
        return "0.00%"
    if any(h in n for h in ("%", "retention", "stickiness", "share", "rate")):
        return "0.0%"
    if "arpu" in n or "arppu" in n or "stars" in n:
        return "#,0.00"
    return "#,0"


def home_tables(measures: list[tuple[str, str]]) -> dict[str, str]:
    """Each measure lives in the first table its DAX references (or that of a measure it uses)."""
    home: dict[str, str] = {}
    for _ in range(3):                                   # resolve measure-on-measure chains
        for name, expr in measures:
            if name in home:
                continue
            tables = [t for t in re.findall(r"\b([a-z_]+)\[|\(\s*([a-z_]+)\s*[,)]", expr) for t in t if t in TABLES]
            used = [home[m] for m in re.findall(r"\[([^\]]+)\]", expr) if m in home]
            if tables or used:
                home[name] = (tables or used)[0]
    missing = [n for n, _ in measures if n not in home]
    if missing:
        raise ValueError(f"cannot place measures: {missing}")
    return home


def m_source(table: str, types: list[tuple[str, str, str]]) -> str:
    typed = ",\n".join(f'        {{"{c}", {pq}}}' for c, _, pq in types)
    return f'''let
    Source = Csv.Document(
        if Text.StartsWith(DataFolder, "http")
            then Web.Contents(DataFolder, [RelativePath = "{table}.csv"])
            else File.Contents(DataFolder & "{table}.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
{typed}
    }}, "en-US")
in
    Typed'''


def model_column_name(col: str, measure_names: set[str]) -> str:
    """Tabular names are case-insensitive and a column can't share a measure's name."""
    return f"{col} (column)" if col.lower() in measure_names else col


def table_tmdl(table: str, measures: list[tuple[str, str]], measure_names: set[str]) -> str:
    types = column_types(table)
    out = [f"table {q(table)}", ""]
    for name, expr in measures:
        if "\n" in expr:
            out.append(f"\tmeasure {q(name)} =")
            out += ["\t\t\t" + ln for ln in expr.splitlines()]
        else:
            out.append(f"\tmeasure {q(name)} = {expr}")
        out += [f"\t\tformatString: {measure_format(name)}", ""]
    for col, dtype, _ in types:
        out.append(f"\tcolumn {q(model_column_name(col, measure_names))}")
        out.append(f"\t\tdataType: {dtype}")
        fmt = column_format(col, dtype)
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        numeric = dtype in ("int64", "double") and col not in ID_COLS and not any(h in col for h in RATE_HINTS)
        out.append(f"\t\tsummarizeBy: {'sum' if numeric else 'none'}")
        out += [f"\t\tsourceColumn: {col}", ""]
    out.append(f"\tpartition {q(table)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out += ["\t\t\t\t" + ln for ln in m_source(table, types).splitlines()]
    return "\n".join(out) + "\n"


def write_model() -> None:
    measures = parse_measures()
    home = home_tables(measures)
    d = MODEL / "definition"
    (d / "tables").mkdir(parents=True, exist_ok=True)
    write_json(MODEL / "definition.pbism", {
        "$schema": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}})
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1601\n")
    (d / "model.tmdl").write_text(
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f'annotation PBI_QueryOrder = {json.dumps(["DataFolder"] + TABLES)}\n\n'
        + "".join(f"ref table {q(t)}\n" for t in TABLES))
    (d / "expressions.tmdl").write_text(
        f'expression DataFolder = "{DEFAULT_FOLDER}" meta [IsParameterQuery = true, Type = "Text", '
        f'IsParameterQueryRequired = true]\n\n\tannotation PBI_ResultType = Text\n')
    names = {n.lower() for n, _ in measures}
    if len(names) != len(measures):
        raise ValueError("duplicate measure names in measures.dax")
    # Point DAX at the renamed columns, e.g. ab_test_players[revenue] -> ab_test_players[revenue (column)].
    renamed = {(t, c): model_column_name(c, names) for t in TABLES for c, _, _ in column_types(t)
               if model_column_name(c, names) != c}
    for (t, c), new in renamed.items():
        measures = [(n, re.sub(rf"\b{t}\[{re.escape(c)}\]", f"{t}[{new}]", e)) for n, e in measures]
    for t in TABLES:
        mine = [(n, e) for n, e in measures if home[n] == t]
        (d / "tables" / f"{t}.tmdl").write_text(table_tmdl(t, mine, names))


# --------------------------------------------------------------------------- report (PBIR)

def oid(*parts: str) -> str:
    """Stable 20-character object name, as Power BI uses."""
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]


def field(spec):
    """('m', table, measure) | ('c', table, column) | ('sum'|'avg', table, column) -> projection."""
    kind, table, prop = spec
    src = {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}
    if kind == "m":
        return {"field": {"Measure": src}, "queryRef": f"{table}.{prop}", "nativeQueryRef": prop}
    if kind == "c":
        return {"field": {"Column": src}, "queryRef": f"{table}.{prop}", "nativeQueryRef": prop}
    fn = {"sum": (0, "Sum"), "avg": (1, "Avg")}[kind]
    return {"field": {"Aggregation": {"Expression": {"Column": src}, "Function": fn[0]}},
            "queryRef": f"{fn[1]}({table}.{prop})", "nativeQueryRef": f"{fn[1]} of {prop}"}


def lit(v: str) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def visual(page: str, i: int, vtype: str, box: tuple, title: str, roles: dict) -> dict:
    x, y, w, h = box
    return {
        "$schema": SCHEMA + "item/report/definition/visualContainer/2.0.0/schema.json",
        "name": oid(page, str(i), title),
        "position": {"x": x, "y": y, "z": i * 1000, "width": w, "height": h, "tabOrder": i * 1000},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": {role: {"projections": [field(s) for s in specs]} for role, specs in roles.items()}},
            "visualContainerObjects": {"title": [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]},
            "drillFilterOtherVisuals": True,
        },
    }


def cards(table_measures: list[tuple[str, str]], y=16, h=96):
    """A row of KPI cards across the 1280px page."""
    w = (1280 - 32 - 12 * (len(table_measures) - 1)) / len(table_measures)
    return [("card", (16 + k * (w + 12), y, w, h), m, {"Values": [("m", t, m)]})
            for k, (t, m) in enumerate(table_measures)]


PAGES = {
    "Overview": cards([("daily_activity", "New Players"), ("new_players", "D1 Retention"), ("new_players", "D7 Retention"),
                       ("daily_activity", "Stickiness"), ("ab_test_players", "Conversion"), ("ab_test_players", "ARPU")]) + [
        ("lineChart", (16, 128, 820, 576), "Daily active players and new players, 2020",
         {"Category": [("c", "daily_activity", "date")], "Y": [("sum", "daily_activity", "dau"), ("sum", "daily_activity", "new_players")]}),
        ("clusteredBarChart", (848, 128, 416, 576), "New players by kind (first 30 days)",
         {"Category": [("c", "new_players", "segment")], "Y": [("m", "new_players", "Players (30-day window)")]}),
    ],
    "Onboarding": cards([("new_players", "Never Returned %"), ("new_players", "Returned Within 7 Days %"),
                         ("cookie_cats_players", "CC Under 10 Rounds %"), ("cookie_cats_players", "Gate 40 vs 30 D7 (pp)"),
                         ("kpi_summary", "Gate D7 Test p-value")]) + [
        ("clusteredColumnChart", (16, 128, 616, 576), "When new players first come back (day)",
         {"Category": [("c", "new_players", "first_return_day")], "Y": [("m", "new_players", "Players (30-day window)")]}),
        ("clusteredColumnChart", (648, 128, 616, 576), "Day-7 return by rounds played, gate 30 vs 40",
         {"Category": [("c", "cookie_cats_players", "rounds_bucket")], "Series": [("c", "cookie_cats_players", "version")],
          "Y": [("m", "cookie_cats_players", "CC D7 Retention")]}),
    ],
    "Retention": cards([("new_players", "D1 Retention"), ("new_players", "D7 Retention"), ("new_players", "D30 Retention")]) + [
        ("lineChart", (16, 128, 1248, 260), "Day-N retention curve",
         {"Category": [("c", "retention_curve", "day_n")], "Y": [("m", "retention_curve", "Day-N Retention")]}),
        ("pivotTable", (16, 400, 1248, 304), "Weekly cohorts x day",
         {"Rows": [("c", "cohort_retention", "cohort_week")], "Columns": [("c", "cohort_retention", "day_n")],
          "Values": [("m", "cohort_retention", "Cohort Retention")]}),
    ],
    "Engagement": cards([("daily_activity", "Avg DAU"), ("daily_activity", "Latest MAU"), ("daily_activity", "Stickiness"),
                         ("daily_activity", "Returning Share of DAU")]) + [
        ("lineChart", (16, 128, 820, 576), "Daily, weekly and monthly active players",
         {"Category": [("c", "daily_activity", "date")],
          "Y": [("sum", "daily_activity", "dau"), ("sum", "daily_activity", "wau"), ("sum", "daily_activity", "mau")]}),
        ("lineChart", (848, 128, 416, 576), "Stickiness (DAU / MAU)",
         {"Category": [("c", "daily_activity", "date")], "Y": [("m", "daily_activity", "Stickiness")]}),
    ],
    "Monetization": cards([("ab_test_players", "ARPU Lift B vs A"), ("kpi_summary", "ARPU Test p-value"),
                           ("ab_test_players", "Conversion Lift B vs A"), ("kpi_summary", "Conversion Test p-value")]) + [
        ("tableEx", (16, 128, 620, 300), "Offer set A vs B",
         {"Values": [("c", "ab_test_players", "testgroup"), ("m", "ab_test_players", "AB Players"), ("m", "ab_test_players", "Payers"),
                     ("m", "ab_test_players", "Conversion"), ("m", "ab_test_players", "ARPU"), ("m", "ab_test_players", "ARPPU"),
                     ("m", "ab_test_players", "Share of Revenue from 10k+ Payers")]}),
        ("clusteredColumnChart", (648, 128, 616, 576), "Revenue by payer spend tier",
         {"Category": [("c", "ab_test_players", "revenue_tier")], "Series": [("c", "ab_test_players", "testgroup")],
          "Y": [("m", "ab_test_players", "Revenue")]}),
    ],
    "Player voice": cards([("review_games", "Reviews Analyzed"), ("review_games", "Avg Review Stars"),
                           ("review_games", "Share of 1-2 Star Reviews")]) + [
        ("clusteredBarChart", (16, 128, 700, 576), "Themes in 1-2 star vs 4-5 star reviews",
         {"Category": [("c", "review_themes", "theme")],
          "Y": [("m", "review_themes", "Theme Share of Negative Reviews"), ("m", "review_themes", "Theme Share of Positive Reviews")]}),
        ("tableEx", (728, 128, 536, 576), "Where each competitor is weakest",
         {"Values": [("c", "review_games", "game_name"), ("sum", "review_games", "reviews"), ("avg", "review_games", "avg_stars"),
                     ("c", "review_games", "top_pain")]}),
    ],
}


def write_report() -> None:
    d = REPORT / "definition"
    if d.exists():
        shutil.rmtree(d)
    (d / "pages").mkdir(parents=True)
    write_json(REPORT / "definition.pbir", {
        "$schema": SCHEMA + "item/report/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    write_json(d / "version.json", {"$schema": SCHEMA + "item/report/definition/versionMetadata/1.0.0/schema.json",
                                    "version": "2.0.0"})
    write_json(d / "report.json", {
        "$schema": SCHEMA + "item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": "PlayerJourney.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "PlayerJourney.json", "path": "PlayerJourney.json", "type": "CustomTheme"}]}],
    })
    static = REPORT / "StaticResources"
    (static / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    (static / "RegisteredResources").mkdir(parents=True, exist_ok=True)
    shutil.copy(ASSETS / "CY24SU10.json", static / "SharedResources" / "BaseThemes" / "CY24SU10.json")
    shutil.copy(ASSETS / "PlayerJourney.json", static / "RegisteredResources" / "PlayerJourney.json")

    order = []
    for title, visuals in PAGES.items():
        pid = oid("page", title)
        order.append(pid)
        pdir = d / "pages" / pid
        write_json(pdir / "page.json", {"$schema": SCHEMA + "item/report/definition/page/1.4.0/schema.json",
                                        "name": pid, "displayName": title, "displayOption": "FitToPage",
                                        "height": 720, "width": 1280})
        for i, (vtype, box, vtitle, roles) in enumerate(visuals, start=1):
            v = visual(pid, i, vtype, box, vtitle, roles)
            write_json(pdir / "visuals" / v["name"] / "visual.json", v)
    write_json(d / "pages" / "pages.json", {"$schema": SCHEMA + "item/report/definition/pagesMetadata/1.0.0/schema.json",
                                            "pageOrder": order, "activePageName": order[0]})


def write_json(path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def build() -> None:
    write_model()
    write_report()
    write_json(PROJECT / f"{NAME}.pbip", {
        "$schema": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    (PROJECT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")


if __name__ == "__main__":
    build()
    n_vis = sum(len(v) for v in PAGES.values())
    print(f"Wrote {PROJECT / (NAME + '.pbip')}: {len(TABLES)} tables, {len(parse_measures())} measures, "
          f"{len(PAGES)} pages, {n_vis} visuals")
