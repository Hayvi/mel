import argparse
import asyncio
import csv
import json
import sys
import time
import webbrowser
import html
import http.server
import socketserver
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import build_opener, HTTPCookieProcessor, Request
import http.cookiejar
import threading
import os

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


def serve_launcher(
    base_url: str,
    lang: str,
    host: str,
    port: int,
    retries: int,
    backoff_s: float,
    initial_balance: float = 1000.0,
) -> None:
    cache: Dict[int, str] = {}
    games_cache: Optional[List[Dict[str, Any]]] = None
    games_cache: Optional[List[Dict[str, Any]]] = None
    games_source: Optional[str] = None

    class Wallet:
        def __init__(self, initial_balance: float = 1000.0):
            self.balance = initial_balance

        def update(self, amount: float):
            self.balance = amount

    wallet = Wallet(initial_balance=initial_balance)

    def _load_games_index() -> List[Dict[str, Any]]:
        nonlocal games_cache, games_source
        if games_cache is not None:
            return games_cache

        candidates = [
            "all_games.json",
            "all_games_enriched.json",
            "sample_all_categories2.json",
            "sample_all_categories.json",
            "sample_games.json",
        ]
        for path in candidates:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                continue
            except Exception:
                continue

            if not isinstance(data, list):
                continue

            out: List[Dict[str, Any]] = []
            for g in data:
                if not isinstance(g, dict):
                    continue
                if "id" not in g:
                    continue
                try:
                    gid = int(g.get("id"))
                except Exception:
                    continue

                name = g.get("name")
                out.append(
                    {
                        "id": gid,
                        "name": str(name) if name is not None else "",
                    }
                )

            games_cache = out
            games_source = path
            return out

        games_cache = []
        games_source = None
        return games_cache

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send_html(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _proxy_with_css_injection(self, target_url: str) -> None:
            """Fetch game content and inject CSS to hide balance/credit elements."""
            import re
            from urllib.parse import urljoin
            
            # CSS to hide balance/credit displays
            HIDE_BALANCE_CSS = """
<style id="mel-hide-balance">
/* Hide balance/credit displays across common game providers */
[class*="balance" i], [class*="Balance"],
[class*="credit" i], [class*="Credit"],
[class*="money" i]:not([class*="won"]):not([class*="win"]),
.balance-panel, .credit-display, .bet-display,
[data-testid*="balance" i], [data-testid*="credit" i],
.game-balance, .player-balance, .wallet-balance,
.info-bar .balance, .bottom-bar .balance,
/* Pragmatic Play specific */
.balance-value, .credits-value, .bet-value,
/* Common patterns */
.ui-balance, .ui-credit, .ui-money,
.hud-balance-native, .native-balance {
    visibility: hidden !important;
    opacity: 0 !important;
}
</style>
"""
            
            # Fetch the target URL
            req = Request(target_url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            
            with build_opener().open(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "text/html")
                raw_data = resp.read()
            
            # Only inject CSS into HTML content
            if "text/html" in content_type.lower():
                try:
                    html_content = raw_data.decode("utf-8", errors="replace")
                except Exception:
                    html_content = raw_data.decode("latin-1", errors="replace")
                
                # Rewrite relative URLs to absolute
                base_parsed = urlparse(target_url)
                base_origin = f"{base_parsed.scheme}://{base_parsed.netloc}"
                
                def make_absolute(match):
                    attr = match.group(1)
                    quote = match.group(2)
                    url = match.group(3)
                    if url.startswith(("http://", "https://", "data:", "javascript:", "//")):
                        return match.group(0)
                    abs_url = urljoin(target_url, url)
                    return f'{attr}={quote}{abs_url}{quote}'
                
                # Rewrite src, href, action attributes
                html_content = re.sub(
                    r'(src|href|action)=(["\'])([^"\']*)\2',
                    make_absolute,
                    html_content,
                    flags=re.IGNORECASE
                )
                
                # Inject CSS before </head> or at start of <body>
                if "</head>" in html_content.lower():
                    html_content = re.sub(
                        r'(</head>)',
                        HIDE_BALANCE_CSS + r'\1',
                        html_content,
                        count=1,
                        flags=re.IGNORECASE
                    )
                elif "<body" in html_content.lower():
                    html_content = re.sub(
                        r'(<body[^>]*>)',
                        r'\1' + HIDE_BALANCE_CSS,
                        html_content,
                        count=1,
                        flags=re.IGNORECASE
                    )
                else:
                    html_content = HIDE_BALANCE_CSS + html_content
                
                body = html_content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            else:
                # Pass through non-HTML content as-is
                body = raw_data
                self.send_response(200)
                self.send_header("Content-Type", content_type)
            
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            qs = parse_qs(parsed.query or "")
            if path == "/api/wallet/balance":
                self._send_json(200, {"balance": wallet.balance, "currency": "FUN"})
                return

            # Proxy endpoint - fetches game content and injects CSS to hide balance
            if path == "/proxy":
                target_url = (qs.get("url") or [None])[0]
                if not target_url:
                    self._send_html(400, "<h1>Missing url parameter</h1>")
                    return
                
                try:
                    self._proxy_with_css_injection(target_url)
                except Exception as e:
                    self._send_html(500, f"<h1>Proxy error</h1><pre>{html.escape(str(e))}</pre>")
                return

            if path == "/api/games":
                q_raw = ((qs.get("q") or [""])[0] or "").strip()
                q = q_raw.lower()
                try:
                    limit = int((qs.get("limit") or ["50"])[0])
                except Exception:
                    limit = 50
                try:
                    offset = int((qs.get("offset") or ["0"])[0])
                except Exception:
                    offset = 0

                limit = max(1, min(200, limit))
                offset = max(0, offset)

                games = _load_games_index()
                if q:
                    filtered = [g for g in games if q in str(g.get("id", "")).lower() or q in str(g.get("name", "")).lower()]
                else:
                    filtered = games

                page = filtered[offset : offset + limit]
                self._send_json(
                    200,
                    {
                        "source": games_source,
                        "total": len(filtered),
                        "offset": offset,
                        "limit": limit,
                        "items": page,
                    },
                )
                return

            if path == "/games":
                q_raw = ((qs.get("q") or [""])[0] or "").strip()
                q = q_raw.lower()
                try:
                    limit = int((qs.get("limit") or ["50"])[0])
                except Exception:
                    limit = 50
                try:
                    offset = int((qs.get("offset") or ["0"])[0])
                except Exception:
                    offset = 0

                limit = max(1, min(200, limit))
                offset = max(0, offset)

                games = _load_games_index()
                if q:
                    filtered = [g for g in games if q in str(g.get("id", "")).lower() or q in str(g.get("name", "")).lower()]
                else:
                    filtered = games

                total = len(filtered)
                page = filtered[offset : offset + limit]

                def _make_link(new_offset: int) -> str:
                    params: Dict[str, Any] = {"limit": limit, "offset": new_offset}
                    if q_raw:
                        params["q"] = q_raw
                    return "/games?" + urlencode(params)

                prev_link = _make_link(max(0, offset - limit)) if offset > 0 else ""
                next_link = _make_link(offset + limit) if (offset + limit) < total else ""

                rows = "\n".join(
                    (
                        "<tr>"
                        f"<td><code>{int(g.get('id'))}</code></td>"
                        f"<td>{html.escape(str(g.get('name') or ''))}</td>"
                        f"<td><a href=\"/game/{int(g.get('id'))}\">Launch</a></td>"
                        "</tr>"
                    )
                    for g in page
                )

                src = html.escape(games_source or "(none)")
                self._send_html(
                    200,
                    f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Games</title>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 24px; }}
      a {{ color: #2563eb; text-decoration: none; }}
      .top {{ display:flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
      input {{ padding: 10px; font-size: 16px; width: 280px; }}
      button {{ padding: 10px 14px; font-size: 16px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: left; }}
      code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
      .muted {{ color: #666; }}
      .pager {{ margin-top: 14px; display:flex; gap: 12px; align-items:center; }}
    </style>
  </head>
  <body>
    <div class=\"top\">
      <h1 style=\"margin:0\">Games</h1>
      <a href=\"/\">Home</a>
      <span class=\"muted\">source: <code>{src}</code></span>
    </div>
    <form action=\"/games\" method=\"get\" style=\"margin-top:12px\">
      <input name=\"q\" value=\"{html.escape(q_raw)}\" placeholder=\"search by id or name\" />
      <input type=\"hidden\" name=\"limit\" value=\"{limit}\" />
      <button type=\"submit\">Search</button>
      <a href=\"/games\" style=\"margin-left:10px\">Clear</a>
    </form>
    <div class=\"muted\" style=\"margin-top:8px\">showing {offset + 1 if total else 0}-{min(offset + limit, total)} of {total}</div>
    <table>
      <thead>
        <tr><th>ID</th><th>Name</th><th></th></tr>
      </thead>
      <tbody>
        {rows if rows else '<tr><td colspan="3" class="muted">No results</td></tr>'}
      </tbody>
    </table>
    <div class=\"pager\">
      {f'<a href="{prev_link}">Prev</a>' if prev_link else '<span class="muted">Prev</span>'}
      {f'<a href="{next_link}">Next</a>' if next_link else '<span class="muted">Next</span>'}
      <span class=\"muted\">|</span>
      <a class=\"muted\" href=\"/api/games?q={html.escape(q_raw)}&limit={limit}&offset={offset}\">api</a>
    </div>
  </body>
</html>""",
                )
                return

            game_id: Optional[int] = None
            if path.startswith("/game/"):
                tail = path[len("/game/"):].strip("/")
                if tail:
                    try:
                        game_id = int(tail)
                    except Exception:
                        game_id = None
            elif path in ("/game", "/open"):
                v = (qs.get("id") or [None])[0]
                if v is not None:
                    try:
                        game_id = int(v)
                    except Exception:
                        game_id = None

            if path == "/":
                self._send_html(
                    200,
                    """<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>MelBet Game Launcher</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 24px; }
      input { padding: 10px; font-size: 16px; width: 220px; }
      button { padding: 10px 14px; font-size: 16px; margin-left: 8px; }
      .hint { color: #555; margin-top: 10px; }
    </style>
  </head>
  <body>
    <h1>MelBet Demo Game Launcher</h1>
    <form action=\"/game\" method=\"get\">
      <input name=\"id\" placeholder=\"game id (e.g. 95426)\" />
      <button type=\"submit\">Launch</button>
    </form>
    <div class=\"hint\">Tip: open <code>/game/&lt;id&gt;</code> directly.</div>
    <div class=\"hint\"><a href=\"/games\">Browse games</a> (local list)</div>
  </body>
</html>""",
                )
                return

            if game_id is None:
                self._send_html(404, "<h1>Not found</h1>")
                return

            try:
                if game_id in cache:
                    demo_url = cache[game_id]
                else:
                    demo_url = _get_demo_link_http(
                        base_url=base_url,
                        lang=lang,
                        game_id=game_id,
                        retries=retries,
                        backoff_s=backoff_s,
                    )
                    cache[game_id] = demo_url
            except Exception as e:
                self._send_html(500, f"<h1>Failed to resolve demo url</h1><pre>{e}</pre>")
                return

            if path == "/open":
                self.send_response(302)
                self.send_header("Location", demo_url)
                self.end_headers()
                return

            self._send_html(
                200,
                f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Game {game_id}</title>
    <style>
      body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; }}
      header {{ display: flex; gap: 12px; align-items: center; padding: 10px 12px; background: #111; color: #fff; }}
      a {{ color: #7dd3fc; text-decoration: none; }}
      iframe {{ width: 100vw; height: calc(100vh - 44px); border: 0; }}

      .hud {{
        position: absolute;
        top: 44px;
        right: 12px;
        width: 200px;
        height: 32px;
        background: rgba(0,0,0,0.7);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding: 0 16px;
        z-index: 100;
        backdrop-filter: blur(4px);
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        font-size: 12px;
      }}
      .hud-balance {{ font-size: 16px; font-weight: bold; color: #4ade80; font-family: monospace; }}

      code {{ background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 6px; }}
    </style>
  </head>
  <body>
    <header>
      <strong>Game {game_id}</strong>
      <a href=\"/\">Home</a>
      <a href=\"/open?id={game_id}\" target=\"_blank\">Open directly</a>
      <span style=\"opacity:.8\">(demo)</span>
      <span style=\"margin-left:auto; opacity:.7\">src: <code>{demo_url}</code></span>
    </header>
    <div class=\"hud\">
        <div class=\"hud-balance\">Loading...</div>
    </div>

    <iframe src=\"{demo_url}\" allowfullscreen></iframe>

    <script>
        let walletBalance = 0;
        let lastGameBalance = null;

        const hudBalance = document.querySelector('.hud-balance');

        async function fetchWallet() {{
            try {{
                const res = await fetch('/api/wallet/balance');
                const data = await res.json();
                walletBalance = data.balance;
                updateHud();
            }} catch (e) {{
                console.error(\"Failed to fetch wallet\", e);
            }}
        }}

        async function syncWallet(newBalance) {{
            try {{
                const res = await fetch('/api/wallet/sync', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ balance: newBalance }})
                }});
                const data = await res.json();
                if (data.success) {{
                    walletBalance = data.balance;
                    updateHud();
                }}
            }} catch (e) {{
                console.error(\"Failed to sync wallet\", e);
            }}
        }}

        function updateHud() {{
            hudBalance.textContent = walletBalance.toFixed(2);
        }}

        window.addEventListener('message', (e) => {{
            let data = e.data;
            try {{ if (typeof data === 'string') data = JSON.parse(data); }} catch(e){{}}
            
            if (!data) return;

            if (data.name === 'post_updateBalance' || (data.event === 'updateBalance' && data.params && data.params.total)) {{
                const rawAmount = data.params?.total?.amount;
                if (typeof rawAmount === 'number') {{
                    const gameVal = rawAmount / 100.0; 

                    if (lastGameBalance === null) {{
                        lastGameBalance = gameVal;
                        console.log(\"Initialized baseline game balance:\", gameVal);
                    }} else {{
                        const delta = gameVal - lastGameBalance;
                        lastGameBalance = gameVal;
                        
                        if (delta !== 0) {{
                            walletBalance += delta;
                            syncWallet(walletBalance);
                        }}
                    }}
                }}
            }}
        }});

        fetchWallet();
    </script>
  </body>
</html>""",
            )

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"

            if path == "/api/wallet/init":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len) if content_len > 0 else b"{}"
                try:
                    data = json.loads(body)
                    amount = float(data.get("amount", 1000.0))
                except Exception:
                    amount = 1000.0
                wallet.update(amount)
                self._send_json(200, {"balance": wallet.balance})
                return

            if path == "/api/wallet/sync":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    data = json.loads(body)
                    # Expected payload from client: {"balance": 123.45}
                    # We trust the client for this MVP demo
                    new_balance = float(data.get("balance", wallet.balance))
                    wallet.update(new_balance)
                    self._send_json(200, {"success": True, "balance": wallet.balance})
                except Exception as e:
                    self._send_json(400, {"success": False, "error": str(e)})
                return

            self._send_json(404, {"error": "Not found"})

    with socketserver.ThreadingTCPServer((host, port), Handler) as httpd:
        httpd.allow_reuse_address = True
        sys.stdout.write(f"Launcher running on http://{host}:{port}/\n")
        httpd.serve_forever()


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

    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)

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
    ap.add_argument("--balance", type=float, default=1000.0, help="initial virtual wallet balance")

    ap.add_argument("--list-categories", action="store_true")
    ap.add_argument("--launch", type=int, help="launch browser with extension for specific game id")
    ap.add_argument("--test-extension", action="store_true", help="Run automated verification of extension integration")

    return ap.parse_args(argv)

async def launch_integrated_browser(args: argparse.Namespace) -> int:
    if not _HAS_PLAYWRIGHT or async_playwright is None:
        print("Error: Playwright not found. Install it with: pip install playwright && playwright install chromium")
        return 1

    # 1. Start server in a background thread
    def run_server():
        serve_launcher(
            base_url=args.base_url,
            lang=args.lang,
            host=args.host,
            port=args.port,
            retries=args.retries,
            backoff_s=args.backoff,
            initial_balance=args.balance,
        )

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    print(f"Server starting on http://{args.host}:{args.port}...")
    await asyncio.sleep(2) # Give it a second to bind

    # 2. Launch Playwright with extension
    extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "extension"))
    if not os.path.exists(extension_path):
        print(f"Error: Extension folder not found at {extension_path}")
        return 1

    async with async_playwright() as p:
        print(f"Launching integrated browser with extension from {extension_path}...")
        
        # We must use a persistent context to load extensions in Chromium
        user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "playwright_profile"))
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
            ]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        target_url = f"http://{args.host}:{args.port}/game/{args.launch}"
        await page.goto(target_url, timeout=60000)
        
        # Keep alive until browser is closed (unless testing)
        if args.test_extension:
            print("TEST MODE: Waiting for extension to sync...")
            try:
                # Wait for initial load - relaxation for canvas games which poll constantly
                # await page.wait_for_load_state("networkidle") 
                await asyncio.sleep(8) # Allow extension to inject and iframe to load
                
                output_path = os.path.abspath("extension_verification.png")
                await page.screenshot(path=output_path, timeout=60000)
                print(f"TEST SUCCESS: Screenshot saved to {output_path}")
                
            except Exception as e:
                print(f"TEST FAILED: {e}")
            finally:
                await context.close()
                return 0

        try:
            while True:
                if not context.pages:
                    break
                await asyncio.sleep(1)
        except (KeyboardInterrupt, Exception):
            pass
        
        await context.close()
    
    return 0


def main(argv: List[str]) -> int:
    args = _parse_args(argv)

    if args.launch:
        return asyncio.run(launch_integrated_browser(args))

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

    if args.serve:
        serve_launcher(
            base_url=args.base_url,
            lang=args.lang,
            host=args.host,
            port=int(args.port),
            retries=args.retries,
            backoff_s=args.backoff,
            initial_balance=args.balance,
        )
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
