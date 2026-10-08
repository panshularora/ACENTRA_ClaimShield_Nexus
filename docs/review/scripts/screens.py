"""Baseline screenshots of every ClaimShield route at 1440x900 + console/network errors per page."""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

WEB = "http://127.0.0.1:5173"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/claimshield-review/screens/baseline")
OUT.mkdir(parents=True, exist_ok=True)
CASES = json.loads(Path("/workspace/claimshield-review/logs/screen_cases.json").read_text())
report: dict[str, dict] = {}
n = 0

def attach(page, bucket):
    page.on("console", lambda m: bucket["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: bucket["console"].append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: bucket["failed"].append(f"FAILED {r.method} {r.url} {r.failure}"))
    page.on("response", lambda r: bucket["failed"].append(f"{r.status} {r.request.method} {r.url}") if r.status >= 400 else None)

def snap(page, name, full=False, settle=600, locator=None):
    global n
    n += 1
    path = OUT / f"{n:02d}_{name}.png"
    page.wait_for_timeout(settle)
    if locator is not None:
        locator.screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=full)
    print("saved", path.name, flush=True)
    return path

def new_page(browser, key):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    bucket = report.setdefault(key, {"console": [], "failed": []})
    attach(page, bucket)
    return ctx, page, bucket

def ui_login(page, email, pw):
    page.goto(f"{WEB}/login", wait_until="networkidle")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", pw)
    page.click("button[type=submit]")
    page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
    page.wait_for_load_state("networkidle")

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])

    # Landing
    ctx, page, b = new_page(browser, "landing")
    page.goto(WEB + "/", wait_until="networkidle")
    snap(page, "landing_top", settle=2500)
    total = page.evaluate("document.documentElement.scrollHeight")
    for frac in (0.2, 0.4, 0.6, 0.8, 1.0):
        page.evaluate(f"window.scrollTo(0, {int((total - 900) * frac)})")
        snap(page, f"landing_scroll_{int(frac*100)}", settle=1500)
    b["scroll_height"] = total
    ctx.close()

    # Login page
    ctx, page, b = new_page(browser, "login")
    page.goto(WEB + "/login", wait_until="networkidle")
    snap(page, "login", settle=2000)
    ctx.close()

    # Manager
    ctx, page, b = new_page(browser, "manager_queue")
    ui_login(page, "manager@demo.claimshield", "demo-manager")
    page.goto(WEB + "/manager/queue", wait_until="networkidle")
    snap(page, "manager_queue_top", settle=2500)
    snap(page, "manager_queue_full", full=True, settle=300)
    # open first case drawer if rows exist
    rows = page.locator("table tbody tr")
    if rows.count():
        rows.first.click()
        snap(page, "manager_queue_case_drawer", settle=1200)
    b["url"] = page.url
    # wiki
    report.setdefault("wiki_proposals", {"console": [], "failed": []})
    page.goto(WEB + "/wiki/proposals", wait_until="networkidle")
    snap(page, "wiki_proposals", full=True, settle=1200)
    links = page.locator("a[href*='/wiki/proposals/']")
    if links.count():
        links.first.click()
        page.wait_for_load_state("networkidle")
        snap(page, "wiki_proposal_detail", full=True, settle=1200)
    ctx.close()

    # Investigator
    ctx, page, b = new_page(browser, "investigator_cases")
    ui_login(page, "investigator@demo.claimshield", "demo-investigator")
    page.goto(WEB + "/investigator/cases", wait_until="networkidle")
    snap(page, "investigator_cases", settle=2500)
    snap(page, "investigator_cases_full", full=True, settle=300)
    ctx.close()

    for label, cid in CASES.items():
        ctx, page, b = new_page(browser, f"workspace_{label}")
        ui_login(page, "investigator@demo.claimshield", "demo-investigator")
        page.goto(f"{WEB}/investigator/workspace/{cid}", wait_until="networkidle")
        snap(page, f"ws_{label}_overview", full=True, settle=2000)
        for tab in ("Findings", "Brief", "Claims", "Timeline", "Network", "Decide"):
            page.locator("nav.ws-menu button", has_text=tab).first.click()
            page.wait_for_load_state("networkidle")
            snap(page, f"ws_{label}_{tab.lower()}", full=True, settle=1200)
            if tab == "Network":
                svg = page.locator("svg.net-map")
                if svg.count():
                    snap(page, f"ws_{label}_network_svg", locator=svg.first, settle=200)
                    nodes = page.locator("g.net-node")
                    b["svg_nodes"] = nodes.count()
                    b["svg_edges"] = page.locator("svg.net-map line").count()
                    b["svg_labels"] = page.locator("svg.net-map text").count()
                    if nodes.count() > 2:
                        nodes.nth(2).click()
                        snap(page, f"ws_{label}_network_node_clicked", full=True, settle=1200)
                        b["drawer_after_node_click"] = page.locator(".evidence-drawer").count()
                        if b["drawer_after_node_click"]:
                            page.locator(".evidence-drawer button", has_text="Close").click()
            if tab == "Brief":
                cite = page.locator("button.cite, .cite").first
                if cite.count():
                    cite.click()
                    snap(page, f"ws_{label}_brief_cite_drawer", settle=1200)
                    page.locator(".evidence-drawer button", has_text="Close").click()
        ctx.close()

    # Auditor
    ctx, page, b = new_page(browser, "audit")
    ui_login(page, "auditor@demo.claimshield", "demo-auditor")
    page.goto(WEB + "/audit", wait_until="networkidle")
    snap(page, "audit", settle=2000)
    snap(page, "audit_full", full=True, settle=300)
    ctx.close()

    # Analyst landing (role with no queue/case access)
    ctx, page, b = new_page(browser, "analyst_home")
    ui_login(page, "analyst@demo.claimshield", "demo-analyst")
    snap(page, "analyst_home_after_login", settle=1500)
    b["url"] = page.url
    ctx.close()
    browser.close()

Path("/workspace/claimshield-review/logs/browser_report.json").write_text(json.dumps(report, indent=1))
print(json.dumps({k: {"console": len(v["console"]), "failed": len(v["failed"])} for k, v in report.items()}, indent=1))
