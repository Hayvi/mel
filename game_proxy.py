#!/usr/bin/env python3
"""
Advanced Game Proxy Server for Full UI Control
Intercepts and modifies all game assets, API calls, and resources
"""

import asyncio
import json
import re
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
import http.server
import socketserver
from typing import Dict, Any

class GameProxyHandler(http.server.BaseHTTPRequestHandler):
    """Proxy handler that intercepts and modifies all game traffic"""
    
    def __init__(self, *args, target_game_url: str = None, balance: float = 5000.0, **kwargs):
        self.target_game_url = target_game_url
        self.balance = balance
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self._proxy_request('GET')
    
    def do_POST(self):
        self._proxy_request('POST')
    
    def _proxy_request(self, method: str):
        """Proxy the request to the actual game server with modifications"""
        
        # Parse the request path
        path = self.path
        if path.startswith('/proxy/'):
            # Remove our proxy prefix
            path = path[7:]
        
        # Construct target URL
        if path.startswith('http'):
            target_url = path
        else:
            target_url = urljoin(self.target_game_url, path)
        
        try:
            # Create request
            req = Request(target_url, method=method)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            
            # Handle POST data
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length) if content_length > 0 else b''
                
                # Modify POST data if it's balance-related
                if b'balance' in post_data or b'credit' in post_data:
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        if 'balance' in data:
                            data['balance'] = self.balance
                        if 'credit' in data:
                            data['credit'] = self.balance
                        post_data = json.dumps(data).encode('utf-8')
                    except:
                        pass
                
                req.data = post_data
            
            # Make the request
            with urlopen(req, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                content = response.read()
            
            # Modify response based on content type
            if 'application/json' in content_type:
                content = self._modify_json_response(content)
            elif 'text/html' in content_type:
                content = self._modify_html_response(content)
            elif 'application/javascript' in content_type or 'text/javascript' in content_type:
                content = self._modify_js_response(content)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(500, f"Proxy error: {str(e)}")
    
    def _modify_json_response(self, content: bytes) -> bytes:
        """Modify JSON responses to inject our balance"""
        try:
            data = json.loads(content.decode('utf-8'))
            
            # Recursively find and replace balance/credit values
            def replace_balance(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key.lower() in ['balance', 'credit', 'money', 'amount']:
                            if isinstance(value, (int, float)):
                                obj[key] = self.balance
                        elif isinstance(value, (dict, list)):
                            replace_balance(value)
                elif isinstance(obj, list):
                    for item in obj:
                        replace_balance(item)
            
            replace_balance(data)
            return json.dumps(data).encode('utf-8')
        except:
            return content
    
    def _modify_html_response(self, content: bytes) -> bytes:
        """Modify HTML responses to inject our control scripts"""
        try:
            html = content.decode('utf-8')
            
            # Inject our advanced control script
            control_script = f"""
<script>
window.MELBET_BALANCE = {self.balance};
window.MELBET_PROXY_MODE = true;

// Override all number displays
const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
Object.defineProperty(Element.prototype, 'innerHTML', {{
    get: originalInnerHTML.get,
    set: function(value) {{
        if (typeof value === 'string') {{
            // Replace large numbers that look like balances
            value = value.replace(/\\b\\d{{3,}}[,.]?\\d{{3,}}[,.]?\\d{{2}}\\b/g, '{self.balance:,.2f}');
        }}
        return originalInnerHTML.set.call(this, value);
    }}
}});

// Override textContent
const originalTextContent = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
Object.defineProperty(Node.prototype, 'textContent', {{
    get: originalTextContent.get,
    set: function(value) {{
        if (typeof value === 'string') {{
            value = value.replace(/\\b\\d{{3,}}[,.]?\\d{{3,}}[,.]?\\d{{2}}\\b/g, '{self.balance:,.2f}');
        }}
        return originalTextContent.set.call(this, value);
    }}
}});

console.log('[MelBet Proxy] Full control mode activated');
</script>
"""
            
            if '</head>' in html:
                html = html.replace('</head>', control_script + '</head>')
            else:
                html = control_script + html
            
            return html.encode('utf-8')
        except:
            return content
    
    def _modify_js_response(self, content: bytes) -> bytes:
        """Modify JavaScript responses to inject balance overrides"""
        try:
            js = content.decode('utf-8')
            
            # Add balance override at the beginning
            balance_override = f"""
// MelBet Balance Override
window.MELBET_BALANCE = {self.balance};
(function() {{
    const originalNumber = window.Number;
    window.Number = function(value) {{
        const num = originalNumber(value);
        // If it's a large number that could be a balance, replace it
        if (num > 1000 && num < 1000000) {{
            return window.MELBET_BALANCE;
        }}
        return num;
    }};
    Object.setPrototypeOf(window.Number, originalNumber);
}})();

"""
            js = balance_override + js
            return js.encode('utf-8')
        except:
            return content


def create_game_proxy_server(target_game_url: str, balance: float = 5000.0, port: int = 8001):
    """Create a proxy server for full game control"""
    
    class ProxyServer(socketserver.ThreadingTCPServer):
        def __init__(self, server_address, RequestHandlerClass):
            super().__init__(server_address, RequestHandlerClass)
            self.allow_reuse_address = True
    
    def handler_factory(*args, **kwargs):
        return GameProxyHandler(*args, target_game_url=target_game_url, balance=balance, **kwargs)
    
    with ProxyServer(('127.0.0.1', port), handler_factory) as server:
        print(f"Game Proxy Server running on http://127.0.0.1:{port}/")
        print(f"Proxying: {target_game_url}")
        print(f"Balance override: {balance}")
        server.serve_forever()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 game_proxy.py <game_url> [balance] [port]")
        sys.exit(1)
    
    game_url = sys.argv[1]
    balance = float(sys.argv[2]) if len(sys.argv) > 2 else 5000.0
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8001
    
    create_game_proxy_server(game_url, balance, port)