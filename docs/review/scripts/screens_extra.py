"""Extra baseline captures: proposal detail, findings evidence drawer, unmasked claims, ring-only network filter."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
WEB = "http://127.0.0.1:5173"
OUT = Path("/workspace/claimshield-review/screens/baseline")
log = {"console": [], "failed": []}
def attach(page):
    page.on("console", lambda m: log["console"].append(f"{page.url} {m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: log["console"].append(f"{page.url} pageerror: {e}"))
    page.on("response", lambda r: log["failed"].append(f"{r.status} {r.request.method} {r.url}") if r.status >= 400 else None)
def login(page, email, pw):
    page.goto(f"{WEB}/login", wait_until="networkidle")
    page.fill("input[type=email]", email); page.fill("input[type=password]", pw)
    page.click("button[type=submit]"); page.wait_for_url(lambda u: "/login" not in u); page.wait_for_load_state("networkidle")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); page = ctx.new_page(); attach(page)
    login(page, "manager@demo.claimshield", "demo-manager")
    page.goto(f"{WEB}/wiki/proposals", wait_until="networkidle"); page.wait_for_timeout(800)
    page.locator("table tbody tr").first.click(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "5X_wiki_proposal_detail.png"), full_page=True); print("url", page.url)
    ctx.close()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); page = ctx.new_page(); attach(page)
    login(page, "investigator@demo.claimshield", "demo-investigator")
    cid = json.loads(Path("/workspace/claimshield-review/logs/screen_cases.json").read_text())["ring_backlog"]
    page.goto(f"{WEB}/investigator/workspace/{cid}#findings", wait_until="networkidle"); page.wait_for_timeout(1000)
    page.locator("button.finding-card").first.click(); page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "5X_ws_ring_backlog_finding_evidence_drawer.png"))
    page.locator(".evidence-drawer button", has_text="Close").click()
    page.locator("nav.ws-menu button", has_text="Network").click(); page.wait_for_timeout(800)
    for kind in ("rendered", "billed", "referral"):
        page.locator(".edge-filters label", has_text=kind).locator("input").uncheck()
    page.wait_for_timeout(600)
    page.locator("svg.net-map").screenshot(path=str(OUT / "5X_ws_ring_backlog_network_structural_only.png"))
    page.locator("label.unmask input").check(); page.wait_for_load_state("networkidle")
    page.locator("nav.ws-menu button", has_text="Claims").click(); page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "5X_ws_ring_backlog_claims_unmasked.png"))
    ctx.close()
    # unknown case + unknown route
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); page = ctx.new_page(); attach(page)
    login(page, "investigator@demo.claimshield", "demo-investigator")
    page.goto(f"{WEB}/investigator/workspace/CASE-DOESNOTEXIST", wait_until="networkidle"); page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "5X_ws_unknown_case.png"))
    page.goto(f"{WEB}/no-such-route", wait_until="networkidle"); page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / "5X_unknown_route.png"))
    ctx.close(); b.close()
Path("/workspace/claimshield-review/logs/browser_report_extra.json").write_text(json.dumps(log, indent=1))
print(json.dumps(log, indent=1)[:3000])
