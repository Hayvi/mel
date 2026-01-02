import argparse
import asyncio
import csv
import json
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request
import http.cookiejar

try:
    from playwright.async_api import async_playwright  # type: ignore

    _HAS_PLAYWRIGHT = True
except Exception:
    async_playwright = None
    _HAS_PLAYWRIGHT = False


@dataclass(frozen=True)
class Game:
    id: int
    name: str
    brand_id: Optional[int]
    brand_name: Optional[str]
    provider_id: Optional[int]
    product_id: Optional[int]
    categories: List[int]
    has_demo: Optional[bool]
    is_new: Optional[bool]
    is_promo: Optional[bool]
    is_hot: Optional[bool]
    img: Optional[str]
    img_url: Optional[str]
    game_url: Optional[str]


def _to_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _build_api_url(base_url: str, path: str, params: Dict[str, Any]) -> str:
    base_url = base_url.rstrip("/")
    qs = urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    return f"{base_url}{path}?{qs}" if qs else f"{base_url}{path}"


def _cap_reached(current: int, max_games: int) -> bool:
    return max_games > 0 and current >= max_games


def _make_http_opener(base_url: str, lang: str):
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    opener.addheaders = [
        (
            "User-Agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ),
        ("Accept", "application/json, text/plain, */*"),
        ("Accept-Language", f"{lang},{lang};q=0.9,en;q=0.8"),
        ("Referer", f"{base_url.rstrip('/')}/{lang}/slots"),
        ("X-Requested-With", "XMLHttpRequest"),
    ]

    warm_url = f"{base_url.rstrip('/')}/{lang}/slots"
    try:
        with opener.open(warm_url, timeout=30) as r:
            r.read(1)
    except Exception:
        pass
    return opener


def _http_get_text(opener, url: str, timeout_s: float) -> str:
    req = Request(url, method="GET")
    with opener.open(req, timeout=timeout_s) as r:
        data = r.read()
    return data.decode("utf-8", errors="replace")


def _get_demo_link_http(
    base_url: str,
    lang: str,
    game_id: int,
    retries: int,
    backoff_s: float,
) -> str:
    base_url = base_url.rstrip("/")
    opener = _make_http_opener(base_url, lang)

    warm_url = f"{base_url}/{lang}/slots?game={int(game_id)}"
    try:
        with opener.open(warm_url, timeout=30) as r:
            r.read(1)
    except Exception:
        pass

    api_url = _build_api_url(
        base_url,
        "/web-api/tpgamesopening/getgameurl",
        {
            "demo": "true",
            "id": int(game_id),
            "withGameInfo": "true",
            "sectionId": 1,
            "launchDomain": "melbet-tn.com/",
        },
    )
    j = _http_get_json_with_retries(opener, api_url, retries=retries, backoff_s=backoff_s)
    if not isinstance(j, dict) or not isinstance(j.get("link"), str) or not j.get("link"):
        raise RuntimeError("Demo link not found in response")
    return str(j["link"])


def _http_get_json_with_retries(opener, url: str, retries: int, backoff_s: float) -> Any:
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            text = _http_get_text(opener, url, timeout_s=30)
            if text:
                return json.loads(text)
            last_err = f"empty_response text_len={len(text)}"
        except (HTTPError, URLError, TimeoutError) as e:
            last_err = str(e)
        except Exception as e:
            last_err = str(e)

        if attempt < retries:
            time.sleep(backoff_s * (2**attempt))

    raise RuntimeError(f"Failed to fetch JSON: {url} ({last_err})")


async def _fetch_json_via_page_fetch(page, url: str) -> Any:
    return await page.evaluate(
        """async (url) => {
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'accept': 'application/json, text/plain, */*',
      'x-requested-with': 'XMLHttpRequest'
    }
  });
  const status = res.status;
  const text = await res.text();
  return { status, text };
}""",
        url,
    )


async def _get_json_with_retries(page, url: str, retries: int, backoff_s: float) -> Any:
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            payload = await _fetch_json_via_page_fetch(page, url)
            status = int(payload.get("status") or 0)
            text = payload.get("text") or ""
            if status == 200 and text:
                return json.loads(text)
            last_err = f"status={status} text_len={len(text)}"
        except Exception as e:
            last_err = str(e)

        if attempt < retries:
            await asyncio.sleep(backoff_s * (2**attempt))

    raise RuntimeError(f"Failed to fetch JSON: {url} ({last_err})")


async def _get_options(page, base_url: str, retries: int, backoff_s: float) -> Dict[str, Any]:
    url = _build_api_url(
        base_url,
        "/web-api/tpmodels/options/1",
        {"optionsKeys": "brands,subcategories,banners"},
    )
    api_json = await _get_json_with_retries(page, url, retries=retries, backoff_s=backoff_s)
    if isinstance(api_json, dict):
        return api_json
    return {}


def _get_options_http(opener, base_url: str, retries: int, backoff_s: float) -> Dict[str, Any]:
    url = _build_api_url(
        base_url,
        "/web-api/tpmodels/options/1",
        {"optionsKeys": "brands,subcategories,banners"},
    )
    api_json = _http_get_json_with_retries(opener, url, retries=retries, backoff_s=backoff_s)
    if isinstance(api_json, dict):
        return api_json
    return {}


def _parse_games(api_json: Any, base_url: str, lang: str) -> List[Game]:
    games = (api_json or {}).get("games")
    if not isinstance(games, list):
        return []

    out: List[Game] = []
    base_url = base_url.rstrip("/")
    for g in games:
        if not isinstance(g, dict):
            continue
        game_id = _to_int(g.get("id"))
        if game_id is None:
            continue
        img = g.get("img")
        img_url = f"{base_url}{img}" if isinstance(img, str) and img.startswith("/") else None
        game_url = f"{base_url}/{lang}/slots?game={game_id}"

        categories_val = g.get("categories")
        categories: List[int] = []
        if isinstance(categories_val, list):
            categories = [c for c in (_to_int(x) for x in categories_val) if c is not None]

        out.append(
            Game(
                id=game_id,
                name=str(g.get("name") or ""),
                brand_id=_to_int(g.get("brandId")),
                brand_name=(str(g.get("brandName")) if g.get("brandName") is not None else None),
                provider_id=_to_int(g.get("provider_id")),
                product_id=_to_int(g.get("product_id")),
                categories=categories,
                has_demo=(bool(g.get("has_demo")) if g.get("has_demo") is not None else None),
                is_new=(bool(g.get("is_new")) if g.get("is_new") is not None else None),
                is_promo=(bool(g.get("is_promo")) if g.get("is_promo") is not None else None),
                is_hot=(bool(g.get("is_hot")) if g.get("is_hot") is not None else None),
                img=(str(img) if img is not None else None),
                img_url=img_url,
                game_url=game_url,
            )
        )

    return out


def _dedupe(games: Iterable[Game]) -> List[Game]:
    seen = set()
    out: List[Game] = []
    for g in games:
        if g.id in seen:
            continue
        seen.add(g.id)
        out.append(g)
    return out


def _write_json(path: str, games: List[Game]) -> None:
    payload = [asdict(g) for g in games]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_csv(path: str, games: List[Game]) -> None:
    rows = [asdict(g) for g in games]
    fieldnames = list(rows[0].keys()) if rows else [k for k in asdict(Game(0, "", None, None, None, None, [], None, None, None, None, None, None, None)).keys()]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["categories"] = json.dumps(r.get("categories") or [])
            w.writerow(r)


def list_categories_http(base_url: str, lang: str, retries: int, backoff_s: float) -> List[Dict[str, Any]]:
    base_url = base_url.rstrip("/")
    opener = _make_http_opener(base_url, lang)
    api_json = _get_options_http(opener, base_url=base_url, retries=retries, backoff_s=backoff_s)

    subs = api_json.get("subcategories") if isinstance(api_json, dict) else None
    if not isinstance(subs, list):
        subs = []

    out: List[Dict[str, Any]] = []
    for s in subs:
        if not isinstance(s, dict):
            continue
        out.append(
            {
                "id": _to_int(s.get("id")),
                "name": s.get("name") or s.get("title") or s.get("caption"),
                "parentId": _to_int(s.get("parentId")),
            }
        )
    return out


def scrape_games_http(
    base_url: str,
    lang: str,
    category_ids: Optional[List[int]],
    all_categories: bool,
    brand_ids: Optional[List[int]],
    title_search: Optional[str],
    limit: int,
    max_games: int,
    sleep_s: float,
    retries: int,
    backoff_s: float,
) -> List[Game]:
    base_url = base_url.rstrip("/")
    opener = _make_http_opener(base_url, lang)

    resolved_category_ids: List[Optional[int]]
    if all_categories:
        options = _get_options_http(opener, base_url=base_url, retries=retries, backoff_s=backoff_s)
        subs = options.get("subcategories")
        if not isinstance(subs, list):
            subs = []
        ids: List[int] = []
        for s in subs:
            if not isinstance(s, dict):
                continue
            cid = _to_int(s.get("id"))
            if cid is not None and cid > 0 and cid not in (998, 999):
                ids.append(cid)
        resolved_category_ids = sorted(set(ids))
    elif category_ids:
        resolved_category_ids = category_ids
    else:
        resolved_category_ids = [None]

    collected: List[Game] = []
    try:
        for cid in resolved_category_ids:
            offset = 0
            while not _cap_reached(len(collected), max_games):
                params: Dict[str, Any] = {
                    "brandIds": ",".join(str(x) for x in (brand_ids or [])) if brand_ids else "",
                    "categoriesId": str(cid) if cid is not None else "",
                    "limit": int(limit),
                    "offset": int(offset),
                    "titleSearch": title_search or "",
                    "withoutCdn": "true",
                    "filterType": "or",
                }
                url = _build_api_url(base_url, "/web-api/tpmodels/games/1", params)
                api_json = _http_get_json_with_retries(opener, url, retries=retries, backoff_s=backoff_s)
                page_games = _parse_games(api_json, base_url=base_url, lang=lang)

                if not page_games:
                    break

                collected.extend(page_games)
                collected = _dedupe(collected)

                offset += limit
                if sleep_s > 0:
                    time.sleep(sleep_s)
    except KeyboardInterrupt:
        pass

    return collected if max_games <= 0 else collected[:max_games]


async def scrape_games(
    base_url: str,
    lang: str,
    category_ids: Optional[List[int]],
    all_categories: bool,
    brand_ids: Optional[List[int]],
    title_search: Optional[str],
    limit: int,
    max_games: int,
    sleep_s: float,
    retries: int,
    backoff_s: float,
) -> List[Game]:
    base_url = base_url.rstrip("/")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(f"{base_url}/{lang}/slots", wait_until="domcontentloaded")

        collected: List[Game] = []

        resolved_category_ids: List[Optional[int]]
        if all_categories:
            options = await _get_options(page, base_url=base_url, retries=retries, backoff_s=backoff_s)
            subs = options.get("subcategories")
            if not isinstance(subs, list):
                subs = []
            ids: List[int] = []
            for s in subs:
                if not isinstance(s, dict):
                    continue
                cid = _to_int(s.get("id"))
                if cid is not None and cid > 0 and cid not in (998, 999):
                    ids.append(cid)
            resolved_category_ids = sorted(set(ids))
        elif category_ids:
            resolved_category_ids = category_ids
        else:
            resolved_category_ids = [None]

        try:
            for cid in resolved_category_ids:
                offset = 0
                while not _cap_reached(len(collected), max_games):
                    params: Dict[str, Any] = {
                        "brandIds": ",".join(str(x) for x in (brand_ids or [])) if brand_ids else "",
                        "categoriesId": str(cid) if cid is not None else "",
                        "limit": int(limit),
                        "offset": int(offset),
                        "titleSearch": title_search or "",
                        "withoutCdn": "true",
                        "filterType": "or",
                    }

                    url = _build_api_url(base_url, "/web-api/tpmodels/games/1", params)
                    api_json = await _get_json_with_retries(page, url, retries=retries, backoff_s=backoff_s)
                    page_games = _parse_games(api_json, base_url=base_url, lang=lang)

                    if not page_games:
                        break

                    collected.extend(page_games)
                    collected = _dedupe(collected)

                    offset += limit
                    if sleep_s > 0:
                        await asyncio.sleep(sleep_s)
        except KeyboardInterrupt:
            pass

        await browser.close()

    return collected if max_games <= 0 else collected[:max_games]


async def list_categories(base_url: str, lang: str, retries: int, backoff_s: float) -> List[Dict[str, Any]]:
    base_url = base_url.rstrip("/")

    if not _HAS_PLAYWRIGHT or async_playwright is None:
        raise RuntimeError("Playwright is not installed. Use --mode http or install playwright.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(f"{base_url}/{lang}/slots", wait_until="domcontentloaded")

        api_json = await _get_options(page, base_url=base_url, retries=retries, backoff_s=backoff_s)

        subs = api_json.get("subcategories") if isinstance(api_json, dict) else None
        if not isinstance(subs, list):
            subs = []

        out: List[Dict[str, Any]] = []
        for s in subs:
            if not isinstance(s, dict):
                continue
            out.append(
                {
                    "id": _to_int(s.get("id")),
                    "name": s.get("name") or s.get("title") or s.get("caption"),
                    "parentId": _to_int(s.get("parentId")),
                }
            )
        await browser.close()

    return out


def _parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://melbet-tn.com")
    ap.add_argument("--lang", default="en")

    ap.add_argument("--mode", choices=["auto", "http", "playwright"], default="auto")

    ap.add_argument("--game-id", type=int, default=None)
    ap.add_argument("--open-game", action="store_true")
    ap.add_argument("--demo", action="store_true")

    ap.add_argument("--category-id", type=int, action="append", dest="category_ids")
    ap.add_argument("--all-categories", action="store_true")
    ap.add_argument("--brand-id", type=int, action="append", dest="brand_ids")
    ap.add_argument("--search", default=None)

    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--max", type=int, default=1000, dest="max_games")
    ap.add_argument("--sleep", type=float, default=0.2)

    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--backoff", type=float, default=0.75)

    ap.add_argument("--out", default="games.json")
    ap.add_argument("--format", choices=["json", "csv"], default="json")

    ap.add_argument("--list-categories", action="store_true")

    return ap.parse_args(argv)


def main(argv: List[str]) -> int:
    args = _parse_args(argv)

    mode = args.mode
    if mode == "auto":
        mode = "playwright" if _HAS_PLAYWRIGHT else "http"

    if args.game_id is not None:
        if args.demo:
            url = _get_demo_link_http(
                base_url=args.base_url,
                lang=args.lang,
                game_id=int(args.game_id),
                retries=args.retries,
                backoff_s=args.backoff,
            )
        else:
            url = f"{args.base_url.rstrip('/')}/{args.lang}/slots?game={int(args.game_id)}"
        sys.stdout.write(url + "\n")
        if args.open_game:
            webbrowser.open(url, new=2)
        return 0

    if args.list_categories:
        if mode == "http":
            cats = list_categories_http(args.base_url, args.lang, retries=args.retries, backoff_s=args.backoff)
        else:
            cats = asyncio.run(list_categories(args.base_url, args.lang, retries=args.retries, backoff_s=args.backoff))
        sys.stdout.write(json.dumps(cats, ensure_ascii=False, indent=2) + "\n")
        return 0

    t0 = time.time()
    if mode == "http":
        games = scrape_games_http(
            base_url=args.base_url,
            lang=args.lang,
            category_ids=args.category_ids,
            all_categories=bool(args.all_categories),
            brand_ids=args.brand_ids,
            title_search=args.search,
            limit=args.limit,
            max_games=args.max_games,
            sleep_s=args.sleep,
            retries=args.retries,
            backoff_s=args.backoff,
        )
    else:
        games = asyncio.run(
            scrape_games(
                base_url=args.base_url,
                lang=args.lang,
                category_ids=args.category_ids,
                all_categories=bool(args.all_categories),
                brand_ids=args.brand_ids,
                title_search=args.search,
                limit=args.limit,
                max_games=args.max_games,
                sleep_s=args.sleep,
                retries=args.retries,
                backoff_s=args.backoff,
            )
        )

    if args.format == "json":
        _write_json(args.out, games)
    else:
        _write_csv(args.out, games)

    dt = time.time() - t0
    sys.stdout.write(f"Wrote {len(games)} games to {args.out} in {dt:.2f}s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
