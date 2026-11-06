#!/usr/bin/env python3
"""Browser checks for the production-based deploy-out at 1440 and 390."""
from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy-out"
SHOTS = Path("/opt/cursor/artifacts")
SHOTS.mkdir(parents=True, exist_ok=True)

REWRITES = {
    "/js/pt.js": "https://plausible.io/js/script.file-downloads.outbound-links.tagged-events.js",
}
REDIRECTS = {
    "/roast": "/#audit",
    "/audit": "/#audit",
    "/pricing": "/#pricing",
    "/book": "https://cal.com/heyblake/pagetear",
    "/call": "https://cal.com/heyblake/pagetear",
    "/index_v1_backup.html": "/",
    "/landing-page": "/#audit",
}
POSTS = [
    "positioning-framework-for-startups",
    "agency-homepage-copywriting",
    "above-the-fold-copywriting-examples",
    "saas-headline-formulas",
    "b2b-value-proposition-examples",
    "saas-homepage-copy-examples",
    "landing-page-hero-copywriting",
    "founder-voice-in-copywriting",
]
BLOG = ["/blog/"] + [f"/blog/{slug}/" for slug in POSTS]
GUIDES = [
    "/compare/unlimited-copywriting-subscriptions/",
    "/saas-copywriting-subscription/",
    "/guides/how-to-hire-a-saas-copywriter/",
    "/guides/homepage-explains-the-product/",
]
BANNED = ("$995", "$1,500", "$6,000", "$20,000", "Most B2B homepages", "40%")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUT), **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in REDIRECTS:
            self.send_response(307)
            self.send_header("Location", REDIRECTS[path])
            self.end_headers()
            return
        if path in REWRITES:
            try:
                with urlopen(Request(REWRITES[path], headers={"User-Agent": "pagetear-local"}), timeout=20) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type", "application/javascript")
            except HTTPError as exc:
                self.send_error(exc.code)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path != "/" and path.endswith("/"):
            candidate = OUT / path.strip("/") / "index.html"
            if candidate.is_file():
                self.path = path + "index.html"
        elif path != "/" and not Path(path).suffix:
            candidate = OUT / path.strip("/") / "index.html"
            if candidate.is_file():
                self.path = path + "/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        return


def serve():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def main():
    if not (OUT / "index.html").is_file():
        raise SystemExit("deploy-out missing; run scripts/assemble_deploy_artifact.py")
    httpd, base = serve()
    failures = []
    console = []

    def check(ok, msg):
        print(("ok  " if ok else "FAIL") + " " + msg)
        if not ok:
            failures.append(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        for width, height, label in ((1440, 900, "desktop"), (390, 844, "mobile")):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("pageerror", lambda err, label=label: console.append(f"{label} pageerror {err}"))
            page.on(
                "console",
                lambda msg, label=label: console.append(f"{label} {msg.type} {msg.text}") if msg.type == "error" else None,
            )
            failed_urls = []

            def on_response(res, bucket=failed_urls):
                if res.status >= 400 and res.url.startswith(base):
                    bucket.append(res.url)

            page.on("response", on_response)

            page.goto(base + "/", wait_until="load", timeout=60000)
            check("$2,000" in page.content() and "$5,000" in page.content(), f"{label} homepage live prices")
            check(page.locator("#car").count() == 1, f"{label} #car exists")
            check("We've been working with Pagetear" in page.locator("#car").inner_text(), f"{label} Flo quote in carousel")
            page.locator('button[data-a="ads"]').click()
            page.wait_for_timeout(600)
            areas = page.locator("#res li").evaluate_all("els => els.filter(el => !el.hidden).map(el => el.dataset.area)")
            check(areas and set(areas) == {"ads"}, f"{label} ads filter {areas}")
            page.locator('button[data-a="all"]').click()
            page.wait_for_timeout(600)
            shown = page.locator("#res li").evaluate_all("els => els.filter(el => !el.hidden).length")
            check(shown == 12, f"{label} all 12 results return ({shown})")
            page.evaluate("() => { const v=document.querySelector('#vv'); if (v && v.paused) v.play(); }")
            page.wait_for_timeout(1500)
            played = page.evaluate("() => { const v=document.querySelector('#vv'); return !!(v && v.currentTime>0 && !v.error) }")
            check(played, f"{label} explainer video advanced")
            if label == "desktop":
                page.screenshot(path=str(SHOTS / "homepage_desktop_video_filter.png"))
            page.locator('a[data-pos="Hero"]').click()
            page.wait_for_timeout(2500)
            modal = page.locator("iframe").evaluate_all("els => els.map(e => e.src).filter(s => s.includes('cal.com') || s.includes('cal.eu'))")
            stayed = page.url.startswith(base)
            check(stayed and len(modal) > 0, f"{label} homepage cal modal {modal[:1]} url {page.url}")
            if label == "desktop":
                page.screenshot(path=str(SHOTS / "homepage_desktop_cal_modal.png"))
            page.keyboard.press("Escape")

            for path in BLOG:
                page.goto(base + path, wait_until="domcontentloaded")
                html = page.content()
                check("Client reviews" in html and 'href="/#car"' in html, f"{label} {path} reviews nav")
                check("See recent work" not in html, f"{label} {path} no misleading label")
                check('cal.com/heyblake/pagetear"' not in html, f"{label} {path} no bare cal")
                check("utm_source=blog" in html, f"{label} {path} blog utm")
                if path != "/blog/":
                    link = page.locator("a.btn-secondary")
                    check(link.inner_text().strip() == "Read client reviews", f"{label} {path} secondary label")
                    check("/#car" in (link.get_attribute("href") or ""), f"{label} {path} secondary href")
                    check("Book+Call" not in (link.get_attribute("class") or ""), f"{label} {path} secondary untracked")
            page.goto(base + "/blog/saas-headline-formulas/", wait_until="domcontentloaded")
            page.locator("a.btn-secondary").click()
            page.wait_for_load_state("load")
            check(page.url.endswith("/#car"), f"{label} reviews click landed {page.url}")
            page.locator("#car").scroll_into_view_if_needed()
            box = page.locator("#car").bounding_box()
            check(box is not None and box["y"] < height and box["y"] + min(box["height"], 80) > 0, f"{label} #car in view {box}")
            check("We've been working with Pagetear" in page.locator("#car").inner_text(), f"{label} carousel quote")
            if label == "desktop":
                page.screenshot(path=str(SHOTS / "reviews_click_desktop_carousel.png"))
            else:
                page.screenshot(path=str(SHOTS / "reviews_click_mobile_carousel.png"))

            page.goto(base + "/blog/saas-headline-formulas/", wait_until="domcontentloaded")
            if label == "desktop":
                page.screenshot(path=str(SHOTS / "blog_post_desktop_ctas.png"), full_page=False)
            else:
                page.screenshot(path=str(SHOTS / "blog_post_mobile_ctas.png"), full_page=False)
            with page.expect_navigation(timeout=20000):
                page.locator("a.btn-primary").click()
            check("cal.com/heyblake/pagetear" in page.url and "utm_content=cta-primary" in page.url, f"{label} cal url {page.url}")
            check("Copywriting" in page.title(), f"{label} cal title {page.title()}")
            check("utm_source=blog" in page.url and "utm_campaign=saas-headline-formulas" in page.url, f"{label} cal utms")
            page.screenshot(path=str(SHOTS / f"cal_event_{label}.png"))

            for path in GUIDES:
                page.goto(base + path, wait_until="domcontentloaded")
                text = page.locator("body").inner_text()
                html = page.content()
                for banned in BANNED:
                    check(banned not in text and banned not in html, f"{label} {path} lacks {banned}")
                check("noindex" not in html.lower(), f"{label} {path} indexable")
            page.goto(base + "/guides/homepage-explains-the-product/", wait_until="domcontentloaded")
            check(page.locator('input[type="checkbox"]').count() == 7, f"{label} seven checkboxes")
            page.locator('input[type="checkbox"]').first.check()
            check("score" not in page.locator("body").inner_text().lower().replace("no score", ""), f"{label} ticking does not create a score")
            check(page.locator("a.cta").inner_text().strip() == "Book a call", f"{label} guide CTA")
            if label == "mobile":
                page.screenshot(path=str(SHOTS / "homepage_guide_mobile_checks.png"), full_page=False)
            else:
                page.screenshot(path=str(SHOTS / "homepage_guide_desktop_checks.png"), full_page=False)

            # These 404 on current production too. Blog asks for a woff2 that was never deployed at the root, and the avatar file is absent.
            allowed_404 = ("blake-avatar.png", "/GeistPixel-Square.woff2")
            unexpected = [u for u in failed_urls if not any(bit in u for bit in allowed_404)]
            check(not unexpected, f"{label} unexpected failed assets {unexpected[:8]}")
            page.close()
        browser.close()
    httpd.shutdown()
    real_errors = [
        line for line in console
        if "favicon" not in line.lower()
        and "blake-avatar" not in line.lower()
        and "GeistPixel-Square.woff2" not in line
        and "404" not in line
    ]
    print("console errors:")
    for line in real_errors[:30]:
        print(" ", line)
    check(not real_errors, f"console errors {len(real_errors)}")
    print(f"\n{len(failures)} failures")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
