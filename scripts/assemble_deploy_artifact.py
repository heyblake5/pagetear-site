#!/usr/bin/env python3
"""Build deploy-out/ from production dpl_9cU8mBBcMfuL236fgLznYGGhgtw7 plus the in-repo patch.

Does not deploy. The git checkout's index.html is the July homepage and must not be
copied into this directory.
"""
from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy-out"
ORIGIN = "https://www.pagetear.com"
PROD_DEPLOYMENT = "dpl_9cU8mBBcMfuL236fgLznYGGhgtw7"

# SHA1 values are the deployment file ids from list_deployment_files, confirmed
# against public responses for HTML, sitemap, robots, and homepage.
EXPECTED = {
    "index.html": "47dff44aedd2f9290622f9c26fd2c5922fc87c2e",
    "robots.txt": "d0107e0e01d6f2f63a91a0fde12fd13e2ecb2480",
    "sitemap.xml": "8e77370334a1041719f232a2b6a03f4bfd496f18",
    "vercel.json": "72709b7acec3a1fafa0f620223f289059605906a",
    "blog/index.html": "e58dc2554be29b1f86def228ad3def34f6c06501",
    "blog/positioning-framework-for-startups/index.html": "4b34224356011b8c849044fa55b3518a650ab0e9",
    "blog/agency-homepage-copywriting/index.html": "467ae8213ea723d764eb06a66c340dcbbb73a0b0",
    "blog/above-the-fold-copywriting-examples/index.html": "297a038617f21c4543dbc835aeca9cfda653694c",
    "blog/saas-headline-formulas/index.html": "f70ccb6568c21f959bb1ecf51ce4ac8a40fee92c",
    "blog/b2b-value-proposition-examples/index.html": "f22c500c79e78daf63c8484fef6241d8502e50d2",
    "blog/saas-homepage-copy-examples/index.html": "52487d9ba7cf95bb2ac357b27e72e9412e450f29",
    "blog/landing-page-hero-copywriting/index.html": "898c7b08ff421587c280a85bea25d11a59bb10f4",
    "blog/founder-voice-in-copywriting/index.html": "6538ea72ba3dff1e75895b9229e8b605e3fed0ef",
    "favicon.png": "864acd67974126353b2ec1d184a3e4ed6aae1b67",
    "ptmetaicon.png": "864acd67974126353b2ec1d184a3e4ed6aae1b67",
    "pt metaicon.png": "5dd105e04b540711d516be87c9dcc50d63aaeab6",
    "Flo.jpeg": "9ecee1e7ebc13d44ae6ea12cc51c056d8d33140d",
    "g12.svg": "a9bdd12916368639858d437cb6dfcf5df64d84f2",
    "g14.svg": "aa9da37c2592c9e567cd19077234cc814b180b0d",
    "katherinekrug.jpeg": "22e4eb3c2ced23482e2d19bc65aef20965b482ad",
    "stephaniewei.jpeg": "0759b251a29036eb4b729e939bc446e681ea0087",
    "ptblack.svg": "4c7a76404d42a58809a5001b5718244ec3e1c08d",
    "ptwhite.svg": "4b90e4add8eef49359c52376d11779a1dde20efa",
    "VEED.svg": "34175b80dd2d11e2dc462726cf69380523834cbc",
    "Ze92tgzL0.svg": "69cc61377092a3cf6e4e1de97db8c4cdada3384c",
    "Group 1.svg": "9f3953fa8f09e6cbd12ea1df53552f66c2a2fbcd",
    "Group 2.svg": "32a610d519c57344f3e1903458389c02753e46a9",
    "Group 3.svg": "e26f795eb59936085614d15f3eb648c92223ed5d",
    "Group 4.svg": "5a73ebd8659924165a363686a542759c69be930c",
    "Group 5.svg": "3740651862512195ce0628a359b1fdae333b1c2f",
    "Group 6.svg": "29b6be6e09aaf926f6e41e556fb53166e21d15b1",
    "Group 7.svg": "59c3d776bc15acf213c76b76baef247df50c5ad8",
    "Group 8.svg": "e7efaa8a6b2b074710718243918207a2697f532d",
    "Group 9.svg": "14dc11794981a9aa1f285e3b041d96261899a6af",
    "Group 10.svg": "1e209515409f14ba8a0147dab9ee603b732d35db",
    "Group 11.svg": "4dd90accfa47d84336663bf86e625263a4d5c747",
    "Group-1.svg": "57b68a3f0f1d8656a379c225209237c39daa9c3e",
    "Geist-Black.otf": "0b62de12614ae168a27a471ae8132b4eaae50500",
    "Geist-Black.ttf": "fbb063df52e8e8ad7425be11953ad57eeba079e8",
    "Geist-BlackItalic.otf": "92e79a02ac38df5d3227e4353b3e76c689f8ced0",
    "Geist-BlackItalic.ttf": "d8b2db64f853f9818e0ed073e5ede407a5bbd2e1",
    "Geist-Bold.ttf": "27327738220b56b5a6867d8b9d72f24ba0c26b20",
    "Geist-BoldItalic.otf": "f9543b5b0f97021e423266a7e985b3b0d4dbb928",
    "Geist-BoldItalic.ttf": "a46d8cf2183b62c09aaf643091e4bb22952c07f6",
    "Geist-ExtraBold.otf": "97b5a04c807774667e21eb6c96d63aedc176ce04",
    "Geist-ExtraBold.ttf": "873469fe80ea1fd957334a88eb4ae22a9db3c5cb",
    "Geist-ExtraBoldItalic.otf": "c468439f2a921874746d436e034665e9676a5429",
    "Geist-ExtraBoldItalic.ttf": "8dbbe739a7f7473dd614fff882897dbe19dab77a",
    "Geist-ExtraLight.otf": "c3ef0c6e746817adde409b0c127b8ae96093826c",
    "Geist-ExtraLight.ttf": "7b014cbcdf6aabe5167e8cb5fe148c9a2a234a58",
    "Geist-ExtraLightItalic.otf": "f4bc9741311a1a2c66f9638da8e1e1b041fbd5dc",
    "Geist-ExtraLightItalic.ttf": "b7ac52e7cb8a367ab4d9aab6da6e10e478722651",
    "Geist-Italic.otf": "b80c4bf0412231c9fcdbd9a54f4a2ec37f6d0717",
    "Geist-Italic.ttf": "bc1461537d8eaa085079448974db26b297ae1c00",
    "Geist-Light.ttf": "07110c1451f989b8ecb5e25472ceefc438df185a",
    "Geist-LightItalic.otf": "caf7a5c64a0048102d4507985e1c02913dfcfc5d",
    "Geist-LightItalic.ttf": "6a13b276b7a25d2dcc26fb479090bec0571a1b4d",
    "Geist-Medium.ttf": "a3f2152271f92ec2c0bcaeda8b584d2d44729199",
    "Geist-MediumItalic.otf": "f233edb8243ddabc7550d58e004b4a7a33c32a8f",
    "Geist-MediumItalic.ttf": "175acbd7c9508b40db469920f87726492cc1c957",
    "Geist-Regular.otf": "b66d06aca083e1eaf4b52c9b1d71dafdcda05b1b",
    "Geist-Regular.ttf": "c510a4c7f1177da026b37e971b5a05a6d798d8cb",
    "Geist-SemiBold.ttf": "995203879f5ea14d7e72e3ad09a6bc36e79bba4d",
    "Geist-SemiBoldItalic.otf": "435851735a47f14a6efbd846ec7f58dd3c87cd2b",
    "Geist-SemiBoldItalic.ttf": "c1313c55cd8c93119f07cc13f5bb284a365a6167",
    "Geist-Thin.otf": "0f9fb63fdd33f3c99023808e28593d9ab26f3515",
    "Geist-Thin.ttf": "89c652b367ba4481d261a050e8f0a0cfc870773b",
    "Geist-ThinItalic.otf": "bcf83b1128a610aa8d2e446f4c26afcf9525dc2b",
    "Geist-ThinItalic.ttf": "bfb0da77b89f98465aa7cb2b299a4e4306795c67",
    "GeistPixel-Square.otf": "873fceb81451630712a4e63c77e3be4dcf8fef0b",
    "v2r3/Flo.webp": "c256aa34635d6a12f1160bf19a338529cd0c6780",
    "v2r3/Geist-Regular.woff2": "0d077475c4bd3f66538201406de4b1ef564ee429",
    "v2r3/Geist-SemiBold.woff2": "b470813994d4ee98d3b1abe03688042ca8a0e196",
    "v2r3/GeistPixel-Square.woff2": "0e72e170dd771922abb2f6a5a845afbf6e98b0c1",
    "v2r3/katherinekrug.webp": "ce45ff4fc08c69b20ea6d547d840d5079df48d2d",
    "v2r3/stephaniewei.webp": "65de57784145df453cc15694a42ee9b8703a4239",
    "v2r3/logos/betterment.svg": "81afd95bbb3fad1f3420b0ab9548264eb42faa37",
    "v2r3/logos/cal-com.svg": "b633fbc44bc5ffc5dc610aa89c55d1dfa4afd61e",
    "v2r3/logos/creativeone.webp": "b92eec4877d1b677023cb6b89393f0586de52ac4",
    "v2r3/logos/cubby.svg": "1e49f2b4cf57e671441f8552e190b960d64a4e12",
    "v2r3/logos/datarobot.svg": "21fa320b9a419232e609590fb86d17c94920e240",
    "v2r3/logos/figure.svg": "b540f5827c7231d3db655678115eb4a4365e350e",
    "v2r3/logos/gamma.svg": "8ece34e815cc95b21a16107069c42dcde44ca39c",
    "v2r3/logos/globalfy.svg": "35bf99ab71524eaf938c2544400d9f46ad30529d",
    "v2r3/logos/numero.svg": "13f161d184a02182f88eda5effda1e85c9d2c3da",
    "v2r3/logos/openrouter.svg": "68cf2c075b5221b21326883533eb5668fe2dd0ac",
    "v2r3/logos/provable.svg": "3ec85b2e6e2fa3264ea561a6b3a88d84516c92fc",
    "v2r3/logos/salus.svg": "954d03777d283fbec7bc790b6ef93187ec6d9520",
    "v2r3/logos/sirius.svg": "e035d35f74b9630b6602b95ed58d1e51a5e25f08",
    "v2r3/logos/tawkify.svg": "7d74893f21958ec182c8ba1f9c541000707ddea6",
    "v2r3/video/pagetear-explainer-1080.mp4": "d4d4ecec5901edfd94effd8453c721b6dc23f8a7",
    "v2r3/video/pagetear-explainer-720.mp4": "28631811572bd777aff1fb4db9e48276174b41d8",
    "v2r3/video/poster.jpg": "f90c8acad206eb51e1754efdbfc13b86cfd29522",
    "v2r3/video/poster.webp": "da234744dd25bdcca096fa38525001a7e2cd7346",
}

# These repo files replace the production bytes. Everything else is copied
# only when its bytes match the production SHA1.
OVERLAY = [
    "sitemap.xml",
    "vercel.json",
    "llms.txt",
    "blog/index.html",
    "blog/positioning-framework-for-startups/index.html",
    "blog/agency-homepage-copywriting/index.html",
    "blog/above-the-fold-copywriting-examples/index.html",
    "blog/saas-headline-formulas/index.html",
    "blog/b2b-value-proposition-examples/index.html",
    "blog/saas-homepage-copy-examples/index.html",
    "blog/landing-page-hero-copywriting/index.html",
    "blog/founder-voice-in-copywriting/index.html",
    "compare/unlimited-copywriting-subscriptions/index.html",
    "saas-copywriting-subscription/index.html",
    "guides/how-to-hire-a-saas-copywriter/index.html",
    "guides/homepage-explains-the-product/index.html",
]


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def public_url(path: str) -> str:
    return ORIGIN + "/" + "/".join(quote(part) for part in path.split("/"))


def fetch(path: str) -> bytes:
    req = Request(public_url(path), headers={"User-Agent": "pagetear-deploy-assemble"})
    with urlopen(req, timeout=180) as resp:
        if resp.status != 200:
            raise SystemExit(f"{path} HTTP {resp.status}")
        return resp.read()


def main() -> None:
    if OUT.exists():
        # Keep the directory reproducible. Remove only files we own.
        for dirpath, dirnames, filenames in os.walk(OUT, topdown=False):
            for name in filenames:
                Path(dirpath, name).unlink()
            for name in dirnames:
                Path(dirpath, name).rmdir()
    OUT.mkdir(parents=True, exist_ok=True)

    repo_hits = []
    download_paths = []
    for path, expected in EXPECTED.items():
        local = ROOT / path
        if path in OVERLAY:
            download_paths.append(path)
            continue
        if local.is_file() and sha1(local.read_bytes()) == expected:
            dest = OUT / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(local.read_bytes())
            repo_hits.append(path)
        else:
            download_paths.append(path)

    print(f"copied {len(repo_hits)} repo files that match production SHA1")
    print(f"fetching {len(download_paths)} files from {ORIGIN}")

    def grab(path: str):
        if path == "vercel.json":
            data = (ROOT / path).read_bytes()
        else:
            data = fetch(path)
        got = sha1(data)
        exp = EXPECTED.get(path)
        if exp and got != exp:
            raise SystemExit(f"SHA1 mismatch for {path}: got {got} expected {exp}")
        return path, data

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(grab, path) for path in download_paths]
        for fut in as_completed(futures):
            path, data = fut.result()
            if path in OVERLAY:
                # Production baseline verified. The patched file is written below.
                continue
            dest = OUT / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            print(f"fetched {path} {len(data)}")

    for path in OVERLAY:
        src = ROOT / path
        if not src.is_file():
            raise SystemExit(f"overlay missing {path}")
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

    # The July homepage must not be what we ship.
    home = sha1((OUT / "index.html").read_bytes())
    if home != EXPECTED["index.html"]:
        raise SystemExit("deploy homepage is not production")
    if sha1((ROOT / "index.html").read_bytes()) == home:
        raise SystemExit("repo index.html unexpectedly matches production; check the copy")

    files = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        rel = str(path.relative_to(OUT))
        files.append(
            {
                "path": rel,
                "sha1": sha1(path.read_bytes()),
                "size": path.stat().st_size,
                "overlay": rel in OVERLAY,
            }
        )
    manifest = {"baselineDeployment": PROD_DEPLOYMENT, "files": files}
    man_path = ROOT / "deploy-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {OUT} ({len(manifest['files'])} files) and {man_path.name}")


if __name__ == "__main__":
    main()
