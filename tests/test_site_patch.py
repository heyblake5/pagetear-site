#!/usr/bin/env python3
"""Static checks for the blog attribution patch and the three SEO pages."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BARE = "https://cal.com/heyblake/pagetear"
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
PLACEMENTS = ["pill", "cta-primary", "footer-1", "footer-2"]
OLD_SEC = (
    '<a class="btn-secondary plausible-event-name=Book+Call '
    'plausible-event-position=Article+CTA+Secondary" '
    'href="https://cal.com/heyblake/pagetear">See recent work</a>'
)
NEW_SEC = '<a class="btn-secondary" href="/#car">Read client reviews</a>'
OLD_NAV = '<a href="https://www.pagetear.com#results">Results</a>'
NEW_NAV = '<a href="/#car">Client reviews</a>'
FLO = (
    "We've been working with Pagetear for a couple of months now at VEED.IO and "
    "we're super super happy. The workflow is incredibly easy to manage, he always "
    "delivers above and beyond on the brief, he's very easy to communicate with and "
    "the quality of the work is fantastic. Highly recommended!"
)
STEPH = "Blake is the best. He actually makes it difficult to want to work with anybody else."
KATH = (
    "I've LOVED your writing. You're doing a killer job. Specifically I've "
    "appreciated how good the writing is and all the detailed examples you're using. "
    "Really great work."
)
BANNED_PRICE = re.compile(
    r"\$995|\$1,500|\$1,995|\$2,495|\$2,995|\$3,250|\$3,495|\$5,850|"
    r"\$6,000|\$10,000|\$15,000|\$20,000|\$30,000|\$1\.5K|\$500 to|\$1,200|\$3,100"
)


def tagged(campaign: str, content: str) -> str:
    return (
        f"{BARE}?utm_source=blog&amp;utm_medium=owned"
        f"&amp;utm_campaign={campaign}&amp;utm_content={content}"
    )


def fetch(url: str) -> str:
    local = {
        "https://www.pagetear.com/": Path("/tmp/live/home.html"),
        "https://www.pagetear.com/blog/": Path("/tmp/live/blog/index.html"),
    }
    for slug in POSTS:
        local[f"https://www.pagetear.com/blog/{slug}/"] = Path(f"/tmp/live/blog/{slug}/index.html")
    cached = local.get(url)
    if cached and cached.is_file():
        return cached.read_text()
    req = Request(url, headers={"User-Agent": "pagetear-patch-test"})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def revert_blog(text: str, campaign: str, placements: list[str], secondary: bool) -> str:
    for place in placements:
        text = text.replace(tagged(campaign, place), BARE)
    if secondary:
        text = text.replace(NEW_SEC, OLD_SEC)
    text = text.replace(NEW_NAV, OLD_NAV)
    guide = (
        '\n      <p>Guides: <a href="/guides/how-to-hire-a-saas-copywriter">How to hire a SaaS copywriter</a>, '
        'the <a href="/saas-copywriting-subscription">copywriting subscription</a>, and '
        '<a href="/compare/unlimited-copywriting-subscriptions">unlimited plans compared</a>.</p>'
    )
    text = text.replace(guide, "")
    extra_links = (
        '      <a href="/guides/how-to-hire-a-saas-copywriter">Hiring guide</a>\n'
        '      <a href="/saas-copywriting-subscription">Subscription</a>\n'
        '      <a href="/compare/unlimited-copywriting-subscriptions">Unlimited plans</a>\n'
    )
    text = text.replace(extra_links, "")
    text = text.replace("url('/v2r3/GeistPixel-Square.woff2')", "url('/GeistPixel-Square.woff2')")
    text = text.replace(
        "    footer.site-footer .footer-links {\n      display: flex;\n      flex-wrap: wrap;\n      gap: 28px;\n    }",
        "    footer.site-footer .footer-links {\n      display: flex;\n      gap: 28px;\n    }",
    )
    return text


def main() -> int:
    failures = []

    def check(ok: bool, msg: str) -> None:
        print(("ok  " if ok else "FAIL") + " " + msg)
        if not ok:
            failures.append(msg)

    live_home = fetch("https://www.pagetear.com/")
    decoded_home = html.unescape(live_home)
    check(FLO in decoded_home and STEPH in decoded_home and KATH in decoded_home, "live homepage quotes")
    check('id="car"' in live_home and 'id="res"' in live_home, "live #car and #res exist")
    check("$2,000 a month for 1 project a week, $3,000 for 2, $4,000 for 3 and $5,000 for 4." in live_home, "live price sentence")

    pages = {"blog/index.html": ("blog-index", ["pill-1", "pill-2", "footer-1"], False)}
    for slug in POSTS:
        pages[f"blog/{slug}/index.html"] = (slug, PLACEMENTS, True)

    booking = 0
    for rel, (campaign, places, secondary) in pages.items():
        text = (ROOT / rel).read_text()
        live = fetch("https://www.pagetear.com/" + rel[: -len("index.html")])
        reverted = revert_blog(text, campaign, places, secondary)
        check(reverted == live, f"{rel} reverts to live bytes")
        check("See recent work" not in text, f"{rel} no See recent work")
        check(f'{BARE}"' not in text, f"{rel} no bare cal href")
        check("#results" not in text and "/#res" not in text, f"{rel} no #results or #res")
        check(text.count(NEW_NAV) == 1, f"{rel} Client reviews nav")
        found = re.findall(r'href="(https://cal\.com/heyblake/pagetear\?[^"]+)"', text)
        check(len(found) == len(places), f"{rel} booking count {len(found)}")
        contents = []
        for href in found:
            check("utm_source=blog&amp;utm_medium=owned" in href, f"{rel} utm pair")
            check(f"utm_campaign={campaign}" in href, f"{rel} campaign")
            m = re.search(r"utm_content=([^&]+)", href)
            contents.append(m.group(1) if m else "")
            check("&amp;" in href and "&utm_" not in href.replace("&amp;", ""), f"{rel} escaped {href[-40:]}")
        check(contents == places, f"{rel} placements {contents}")
        booking += len(found)
        if secondary:
            check(text.count(NEW_SEC) == 1, f"{rel} reviews button")
            check("Article+CTA+Secondary" not in text, f"{rel} secondary tracking removed")
            check(text.count("plausible-event-name=Book+Call") == 4, f"{rel} four book classes")
        else:
            check("Read client reviews" not in text, f"{rel} index has no secondary label")
            check(text.count("plausible-event-name=Book+Call") == 3, f"{rel} three book classes")
    check(booking == 35, f"35 booking links ({booking})")

    seo = [
        ROOT / "compare/unlimited-copywriting-subscriptions/index.html",
        ROOT / "saas-copywriting-subscription/index.html",
        ROOT / "guides/how-to-hire-a-saas-copywriter/index.html",
        ROOT / "llms.txt",
    ]
    for path in seo:
        text = path.read_text()
        check(not BANNED_PRICE.search(text), f"{path.name} no unsourced competitor prices")
        check("noindex" not in text.lower(), f"{path.name} no noindex")
        check("/tools/" not in text and "checker" not in text.lower(), f"{path.name} no checker")
        check("/#res" not in text and "#results" not in text, f"{path.name} no ROI anchor")
        if path.suffix == ".html":
            decoded = html.unescape(text)
            check(FLO in decoded or path.parent.name.startswith("how-to"), f"{path.parent.name} quote policy")
            if "Flo Schirmer" in decoded:
                check(FLO in decoded, f"{path.parent.name} Flo verbatim")
            if "Stephanie Wei" in decoded:
                check(STEPH in decoded, f"{path.parent.name} Stephanie verbatim")
            if "Katherine Krug" in decoded:
                check(KATH in decoded, f"{path.parent.name} Katherine verbatim")
            check("$2,000" in text and "$5,000" in text, f"{path.parent.name} keeps live price bounds")
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
                json.loads(block)
            check('href="/#car"' in text, f"{path.parent.name} links to reviews")

    check((ROOT / "seo/hire-guide/content.py").exists() is False, "stale hire-guide content.py absent")
    sm = (ROOT / "sitemap.xml").read_text()
    for loc in (
        "https://www.pagetear.com/",
        "https://www.pagetear.com/blog",
        "https://www.pagetear.com/compare/unlimited-copywriting-subscriptions",
        "https://www.pagetear.com/saas-copywriting-subscription",
        "https://www.pagetear.com/guides/how-to-hire-a-saas-copywriter",
        "https://www.pagetear.com/blog/saas-headline-formulas/",
    ):
        check(loc in sm, f"sitemap has {loc}")
    check("2026-10-28" in sm, "homepage lastmod preserved from production")
    vj = json.loads((ROOT / "vercel.json").read_text())
    sources = {item["source"] for item in vj["redirects"]}
    check(sources == {"/roast", "/audit", "/pricing", "/book", "/call", "/index_v1_backup.html", "/landing-page"}, "production redirects kept")
    check((ROOT / "index.html").read_text().find('id="car"') < 0, "repo homepage still the July file, not overwritten")
    guide = (ROOT / "guides/homepage-explains-the-product/index.html").read_text()
    check(guide.count('type="checkbox"') == 7, "homepage guide has 7 checkboxes")
    check("Most B2B homepages" not in guide, "ungrounded most-homepages claim removed")
    check("40%" not in guide and "10 to 15" not in guide, "no conflicting hour percentages")
    check("Reconcile the definitions and the time windows" in guide, "reconcile definitions before comparing figures")
    check("not a universally wrong headline" in guide, "category headline is qualified")
    check("not a proven defect" in guide, "name mismatch is a check, not an accusation")
    check("most mentions of the old name were intentional" in guide, "rename example does not invent a defect")
    check("Some search engines render JavaScript" in guide, "crawler advice does not claim none can render JS")
    check("not a validated pass mark" in guide and "does not prove a lift in demos" in guide, "read test is an informal heuristic")
    check("four of the five" not in guide, "4/5 is not stated as a pass rule")
    check("15-minute" not in guide and "Free page teardown" not in guide, "no free teardown claim")
    check(guide.count(">Book a call<") == 2, "both CTAs say Book a call")
    check("utm_source=guide&amp;utm_medium=owned&amp;utm_campaign=homepage-explains" in guide, "guide cal links escaped")
    check("localStorage" in guide and "mailto:" not in guide and "score" not in guide.lower().replace("no score", ""), "manual ticks, no score or email")
    check('href="/guides/homepage-explains-the-product"' in (ROOT / "guides/how-to-hire-a-saas-copywriter/index.html").read_text(), "hire guide links the checklist")
    check("homepage-explains-the-product" in sm, "sitemap lists the homepage guide")
    robots = (ROOT / "robots.txt").read_text()
    check("Allow: /" in robots and "Sitemap: https://www.pagetear.com/sitemap.xml" in robots, "robots allows crawl and points at sitemap")
    check("noindex" not in robots.lower(), "robots has no noindex")
    for rel in pages:
        text = (ROOT / rel).read_text()
        check("url('/GeistPixel-Square.woff2')" not in text, f"{rel} no root pixel woff2")
        check("url('/v2r3/GeistPixel-Square.woff2')" in text, f"{rel} pixel font uses existing v2r3 file")
        check('rel="canonical" href="https://www.pagetear.com/' in text, f"{rel} www canonical")
        check('name="robots"' not in text and "noindex" not in text.lower(), f"{rel} no noindex")
        if rel != "blog/index.html":
            check('src="/blog/_assets/blake-avatar.png"' in text, f"{rel} keeps missing avatar path")
    for path in seo:
        if path.suffix != ".html":
            continue
        text = path.read_text()
        check('rel="canonical" href="https://www.pagetear.com/' in text, f"{path.parent.name} www canonical")
        check("noindex" not in text.lower(), f"{path.parent.name} html has no noindex")
        check("/v2r3/GeistPixel-Square.woff2" in text, f"{path.parent.name} loads pixel font from v2r3")
    home = ROOT / "deploy-out" / "index.html"
    if home.is_file():
        import hashlib
        check(hashlib.sha1(home.read_bytes()).hexdigest() == "47dff44aedd2f9290622f9c26fd2c5922fc87c2e", "deploy homepage sha")

    print(f"\n{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
