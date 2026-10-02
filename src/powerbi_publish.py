"""Publish the Power BI project to Power BI online (a Fabric workspace) and refresh it.

    python src/powerbi_publish.py --client-id <entra-app-id> --tenant <tenant-id-or-domain>

What it does, using the Fabric and Power BI REST APIs as the signed-in user:
  1. Finds or creates the workspace and makes sure it sits on a capacity (a Fabric trial is enough).
  2. Uploads powerbi/GameAnalytics.SemanticModel, with the data source switched from the local
     folder to the CSVs in this repo on GitHub, so the service can refresh it without a gateway.
  3. Sets that web source to anonymous access, and refreshes the model.
  4. Uploads powerbi/GameAnalytics.Report, bound to the published model.
  5. Writes the IDs to powerbi/online.json, for the Power BI MCP server and for reruns.

Rerunning updates the same model and report in place.
"""
import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
MODEL_DIR = PBI / "GameAnalytics.SemanticModel"
REPORT_DIR = PBI / "GameAnalytics.Report"
NAME = "GameAnalytics"
DATA_URL = "https://raw.githubusercontent.com/chauhan-03/game-analytics/main/outputs/powerbi/"
FABRIC = "https://api.fabric.microsoft.com/v1"
POWERBI = "https://api.powerbi.com/v1.0/myorg"
FABRIC_SCOPE = ["https://api.fabric.microsoft.com/.default"]
POWERBI_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]

LOCAL_SOURCE = re.compile(
    r'if Text\.StartsWith\(DataFolder, "http"\)\s*then (Web\.Contents\(DataFolder, \[RelativePath = "[^"]+"\]\))'
    r'\s*else File\.Contents\(DataFolder & "[^"]+"\),')


# ---------------------------------------------------------------- definitions (pure, tested)

def cloud_tmdl(path: str, text: str, data_url: str) -> str:
    """The service can't read C:\\, and a File.Contents branch would make it ask for a gateway,
    so the cloud copy reads only from data_url."""
    if path.endswith("expressions.tmdl"):
        return re.sub(r'(expression DataFolder = )"[^"]*"', lambda m: f'{m.group(1)}"{data_url}"', text)
    return LOCAL_SOURCE.sub(lambda m: m.group(1) + ",", text)


def part(path: str, data: bytes) -> dict:
    return {"path": path, "payload": base64.b64encode(data).decode(), "payloadType": "InlineBase64"}


def files(folder: Path):
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder).as_posix()
        if f.is_file() and not rel.startswith(".pbi/") and rel != ".platform":
            yield rel, f


def model_parts(data_url: str = DATA_URL) -> list[dict]:
    out = []
    for rel, f in files(MODEL_DIR):
        data = f.read_bytes()
        if rel.endswith(".tmdl"):
            data = cloud_tmdl(rel, data.decode("utf-8"), data_url).encode("utf-8")
        out.append(part(rel, data))
    return out


def report_parts(model_id: str) -> list[dict]:
    out = []
    for rel, f in files(REPORT_DIR):
        data = f.read_bytes()
        if rel == "definition.pbir":
            pbir = json.loads(data)
            pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={model_id}"}}
            data = json.dumps(pbir, indent=2).encode()
        out.append(part(rel, data))
    return out


# ---------------------------------------------------------------- service calls

class Api:
    def __init__(self, client_id: str, tenant: str):
        import msal
        self.app = msal.PublicClientApplication(client_id, authority=f"https://login.microsoftonline.com/{tenant}")
        print("Opening a browser to sign in to Microsoft ...")
        first = self.app.acquire_token_interactive(scopes=FABRIC_SCOPE, prompt="select_account")
        if "access_token" not in first:
            sys.exit(f"Sign-in failed: {first.get('error_description', first)}")
        self.account = self.app.get_accounts()[0]

    def token(self, scope) -> str:
        r = self.app.acquire_token_silent(scope, account=self.account) or \
            self.app.acquire_token_interactive(scopes=scope)
        if "access_token" not in r:
            sys.exit(f"Could not get a token for {scope[0]}: {r.get('error_description', r)}")
        return r["access_token"]

    def call(self, method, url, body=None, scope=FABRIC_SCOPE, ok=(200, 201, 202)):
        r = requests.request(method, url, json=body, timeout=120,
                             headers={"Authorization": f"Bearer {self.token(scope)}", "Content-Type": "application/json"})
        if r.status_code not in ok:
            sys.exit(f"{method} {url} -> {r.status_code}\n{r.text[:2000]}")
        return r

    def fabric(self, method, path, body=None):
        """Fabric call that waits for long-running operations; returns the final JSON (or None)."""
        r = self.call(method, FABRIC + path, body)
        if r.status_code != 202:
            return r.json() if r.content else None
        op = r.headers.get("x-ms-operation-id")
        while True:
            time.sleep(int(r.headers.get("Retry-After", 3)))
            r = self.call("GET", f"{FABRIC}/operations/{op}")
            state = r.json().get("status")
            if state == "Succeeded":
                res = self.call("GET", f"{FABRIC}/operations/{op}/result", ok=(200, 400, 404))
                return res.json() if res.status_code == 200 and res.content else None
            if state in ("Failed", "Undefined"):
                sys.exit(f"{method} {path} failed:\n{json.dumps(r.json(), indent=2)[:2000]}")

    def powerbi(self, method, path, body=None, ok=(200, 201, 202)):
        r = self.call(method, POWERBI + path, body, scope=POWERBI_SCOPE, ok=ok)
        return r.json() if r.content else None


def workspace(api: Api, name: str) -> str:
    found = [w for w in api.fabric("GET", "/workspaces")["value"] if w["displayName"] == name]
    ws = found[0] if found else api.fabric("POST", "/workspaces", {"displayName": name})
    ws = api.fabric("GET", f"/workspaces/{ws['id']}")
    if not ws.get("capacityId"):
        caps = [c for c in api.fabric("GET", "/capacities")["value"] if c.get("state") == "Active"]
        if not caps:
            sys.exit("This workspace needs a capacity. Start the free Fabric trial at https://app.fabric.microsoft.com "
                     "(account menu > Free trial), then run this again.")
        api.fabric("POST", f"/workspaces/{ws['id']}/assignToCapacity", {"capacityId": caps[0]["id"]})
        print(f"  Assigned to capacity {caps[0]['displayName']} ({caps[0]['sku']})")
    print(f"Workspace: {name} ({ws['id']})")
    return ws["id"]


def upsert(api: Api, ws: str, kind: str, parts: list[dict], fmt: str | None) -> str:
    definition = {"parts": parts} | ({"format": fmt} if fmt else {})
    existing = [i for i in api.fabric("GET", f"/workspaces/{ws}/{kind}")["value"] if i["displayName"] == NAME]
    if existing:
        item_id = existing[0]["id"]
        api.fabric("POST", f"/workspaces/{ws}/{kind}/{item_id}/updateDefinition", {"definition": definition})
        print(f"Updated {kind[:-1]} {item_id}")
        return item_id
    item = api.fabric("POST", f"/workspaces/{ws}/{kind}", {"displayName": NAME, "definition": definition})
    if not item:
        item = [i for i in api.fabric("GET", f"/workspaces/{ws}/{kind}")["value"] if i["displayName"] == NAME][0]
    print(f"Created {kind[:-1]} {item['id']}")
    return item["id"]


def anonymous_web_credentials(api: Api, ws: str, model: str) -> None:
    for ds in api.powerbi("GET", f"/groups/{ws}/datasets/{model}/datasources")["value"]:
        if ds.get("datasourceType") != "Web":
            continue
        api.powerbi("PATCH", f"/gateways/{ds['gatewayId']}/datasources/{ds['datasourceId']}", {"credentialDetails": {
            "credentialType": "Anonymous", "credentials": json.dumps({"credentialData": ""}),
            "encryptedConnection": "Encrypted", "encryptionAlgorithm": "None", "privacyLevel": "Public"}})
        print(f"  Web source set to anonymous: {ds['connectionDetails'].get('url')}")


def refresh(api: Api, ws: str, model: str) -> None:
    api.powerbi("POST", f"/groups/{ws}/datasets/{model}/refreshes", {"notifyOption": "NoNotification"})
    print("Refreshing the model", end="", flush=True)
    while True:
        time.sleep(10)
        last = api.powerbi("GET", f"/groups/{ws}/datasets/{model}/refreshes?$top=1")["value"][0]
        if last["status"] == "Completed":
            print(" done")
            return
        if last["status"] in ("Failed", "Disabled", "Cancelled"):
            sys.exit(f"\nRefresh {last['status']}:\n{last.get('serviceExceptionJson', '')}")
        print(".", end="", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client-id", required=True, help="Application (client) ID of your Entra app registration")
    ap.add_argument("--tenant", required=True, help="Tenant ID or domain, e.g. contoso.onmicrosoft.com")
    ap.add_argument("--workspace", default="Game Analytics")
    ap.add_argument("--data-url", default=DATA_URL, help="Folder URL holding the outputs/powerbi CSVs")
    a = ap.parse_args()

    api = Api(a.client_id, a.tenant)
    ws = workspace(api, a.workspace)
    model = upsert(api, ws, "semanticModels", model_parts(a.data_url), "TMDL")
    anonymous_web_credentials(api, ws, model)
    refresh(api, ws, model)
    report = upsert(api, ws, "reports", report_parts(model), None)

    info = {"workspace": a.workspace, "workspaceId": ws, "semanticModelId": model, "reportId": report,
            "reportUrl": f"https://app.powerbi.com/groups/{ws}/reports/{report}",
            "mcpServer": "https://api.fabric.microsoft.com/v1/mcp/powerbi"}
    (PBI / "online.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"\nReport: {info['reportUrl']}\nIDs saved to powerbi/online.json")


if __name__ == "__main__":
    main()
