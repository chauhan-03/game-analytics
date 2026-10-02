# Power BI

`GameAnalytics.pbip` is a complete **Power BI Project**. It has the data model, every
measure and six report pages with visuals already bound to the data. Open it in Power BI
Desktop and refresh. `src/run_analysis.py` regenerates it on every run, so it never
drifts from the analysis.

## Open it

1. Run the pipeline once so `outputs/powerbi/` has the CSVs: `python src/run_analysis.py`.
2. In **Power BI Desktop**, open `powerbi/GameAnalytics.pbip`. You need Desktop on Windows, 2024 or later.
3. Go to **Home > Transform data > Edit parameters** and set **DataFolder** to your `outputs\powerbi\`
   folder, ending with a backslash, e.g. `C:\game-analytics\outputs\powerbi\`.
   - DataFolder can also be a URL that serves the CSVs, ending in `/`.
4. Select **Refresh**.

**On a Mac:** Power BI Desktop is Windows-only. You have two options:
- Run it in a Windows VM (Parallels, UTM).
- Publish it to Power BI online with `src/powerbi_publish.py` (next section).

## Power BI online, connected to Claude Code

`src/powerbi_publish.py` publishes this project to Power BI online (no Desktop needed, works
from a Mac). The model reads the CSVs from this GitHub repo, so the service refreshes it
without a gateway. Microsoft's hosted Power BI MCP server then lets Claude Code query the
live model in DAX.

**One-time setup** (needs a Microsoft work or school account; Gmail is not accepted):

1. **Capacity:** at [app.fabric.microsoft.com](https://app.fabric.microsoft.com), start the
   free Fabric trial (account menu > Free trial). Publishing through the API needs a
   workspace on a capacity.
2. **Tenant setting:** in the Power BI admin portal > Tenant settings, enable
   **Users can use the Power BI Model Context Protocol server endpoint (preview)**.
3. **App registration** in the [Entra admin center](https://entra.microsoft.com) > App registrations > New registration:
   - **Account type:** single tenant. Copy the **Application (client) ID** and the **Directory (tenant) ID**.
   - **Authentication** > Add a platform > **Mobile and desktop applications**, with two redirect URIs:
     `http://localhost` (publish script) and `http://localhost:8765/callback` (Claude Code).
   - **API permissions** > Add > **Power BI Service** > Delegated:
     `Workspace.ReadWrite.All`, `Item.ReadWrite.All`, `Dataset.ReadWrite.All`, `Capacity.Read.All`,
     `Dataset.Read.All`, `Workspace.Read.All`, `SemanticModel.ReadWrite.All`, `MLModel.Execute.All`.
     Then **Grant admin consent**.

**Publish** (rerun any time to update the model and report in place):

```bash
python src/powerbi_publish.py --client-id <app-id> --tenant <tenant-id>
```

It signs you in through the browser. It then creates the "Game Analytics" workspace, uploads
the model, sets the GitHub source to anonymous, refreshes, and uploads the report. The report
link and IDs go to `powerbi/online.json`.

**Connect Claude Code** by adding `.mcp.json` at the repo root (git-ignored), then run `/mcp`
in Claude Code to sign in:

```json
{
  "mcpServers": {
    "powerbi": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi",
      "oauth": { "clientId": "<app-id>", "callbackPort": 8765 }
    }
  }
}
```

Claude can then read the model's schema and answer questions by running DAX against the
published semantic model. The ID is in `powerbi/online.json`.

## What's inside

```
GameAnalytics.pbip                  open this
GameAnalytics.SemanticModel/        the data model, as TMDL text files
  definition/tables/*.tmdl          one table per CSV, loaded with Power Query; measures live with their table
  definition/expressions.tmdl       the DataFolder parameter
GameAnalytics.Report/               the report, as PBIR JSON files
  definition/pages/*/visuals/*      every card, chart and table
  StaticResources/                  base theme + "Player Journey" colour theme
measures.dax                        the 37 DAX measures, the source the model is built from
assets/                             theme files
```

| Page | Visuals |
|---|---|
| **Overview** | New players, D1 and D7 retention, stickiness, conversion, ARPU; daily active vs new players; new players by kind |
| **Onboarding** | Never-returned %, back within 7 days %, under-10-rounds %, gate test effect and p-value; first-return day; day-7 return by rounds played and gate |
| **Retention** | D1/D7/D30; Day-N retention curve; weekly cohort matrix |
| **Engagement** | Avg DAU, latest MAU, stickiness, returning share; DAU/WAU/MAU; stickiness over time |
| **Monetization** | ARPU and conversion lift with p-values; offer A vs B table; revenue by spend tier |
| **Player voice** | Reviews analyzed, avg stars, share of 1–2 star reviews; review themes in negative vs positive reviews; each competitor's top pain |

## How it is checked

`tests/test_powerbi_project.py` (99 cases) runs on every test run:
- **Schemas:** every report and project JSON file is validated against Microsoft's published schemas, vendored in `tests/schemas/`.
- **References:** every visual field and every DAX reference resolves to a real column or measure in the model.
- **Names:** no measure shares a name with a column. Names are case-insensitive in Power BI, so a clashing column is renamed in the model, e.g. `revenue (column)`, and the DAX is updated to match.
- **TMDL:** files use tab indentation, and each table has exactly one Power Query source.

`tests/test_powerbi.py` checks that `measures.dax` only references columns and KPI rows that the pipeline exports.

## After opening

Power BI Desktop rewrites the files in its own layout when you save. That's expected. Commit
what it saves. To polish the report, set sort orders for the bucket columns with
**Column tools > Sort by column**: `segment`, `rounds_bucket` and `revenue_tier`. Then
adjust visual formatting to taste.
