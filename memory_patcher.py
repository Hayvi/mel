#!/usr/bin/env python3
"""
Memory Patcher - Direct browser memory manipulation
Uses Chrome DevTools Protocol to directly modify game memory
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def patch_game_memory(page, target_balance=777.77):
    """Directly patch game memory using CDP"""
    
    # Enable runtime domain for memory access
    cdp = await page.context.new_cdp_session(page)
    await cdp.send('Runtime.enable')
    await cdp.send('Debugger.enable')
    
    print(f"[Memory Patcher] Patching game memory to {target_balance}")
    
    # Script to find and replace balance in memory
    memory_patch_script = f"""
    (function() {{
        console.log('[Memory Patcher] Starting memory scan...');
        
        // Find all numeric values in global scope
        function scanGlobalMemory() {{
            const found = [];
            
            function scanObject(obj, path = 'window') {{
                if (!obj || typeof obj !== 'object') return;
                
                try {{
                    Object.keys(obj).forEach(key => {{
                        const value = obj[key];
                        const fullPath = path + '.' + key;
                        
                        if (typeof value === 'number') {{
                            // Look for balance-like numbers
                            if (value >= 100000 && value <= 10000000) {{
                                found.push({{
                                    path: fullPath,
                                    oldValue: value,
                                    object: obj,
                                    key: key
                                }});
                                
                                // Try to replace it
                                try {{
                                    obj[key] = {target_balance};
                                    console.log(`[Memory Patcher] Replaced ${{fullPath}}: ${{value}} -> {target_balance}`);
                                }} catch (e) {{
                                    console.log(`[Memory Patcher] Failed to replace ${{fullPath}}:`, e);
                                }}
                            }}
                        }} else if (typeof value === 'object' && value !== null && path.split('.').length < 5) {{
                            scanObject(value, fullPath);
                        }}
                    }});
                }} catch (e) {{
                    // Ignore access errors
                }}
            }}
            
            scanObject(window);
            return found;
        }}
        
        // Scan WebGL contexts for uniform variables
        function scanWebGLUniforms() {{
            const canvases = document.querySelectorAll('canvas');
            canvases.forEach((canvas, i) => {{
                const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                if (gl) {{
                    console.log(`[Memory Patcher] Found WebGL context on canvas ${{i}}`);
                    
                    // Try to access shader programs (this is very limited)
                    const programs = gl.getParameter(gl.CURRENT_PROGRAM);
                    if (programs) {{
                        console.log('[Memory Patcher] Found active shader program');
                    }}
                }}
            }});
        }}
        
        // Scan for WASM memory
        function scanWASMMemory() {{
            if (window.WebAssembly) {{
                console.log('[Memory Patcher] WebAssembly detected');
                
                // Look for WASM instances
                Object.keys(window).forEach(key => {{
                    const obj = window[key];
                    if (obj && obj.constructor && obj.constructor.name === 'WebAssembly.Instance') {{
                        console.log(`[Memory Patcher] Found WASM instance: ${{key}}`);
                        
                        // Try to access exports
                        if (obj.exports) {{
                            console.log('[Memory Patcher] WASM exports:', Object.keys(obj.exports));
                        }}
                    }}
                }});
            }}
        }}
        
        // Execute all scans
        const results = scanGlobalMemory();
        scanWebGLUniforms();
        scanWASMMemory();
        
        console.log(`[Memory Patcher] Scan complete. Found ${{results.length}} potential balance variables.`);
        return results;
    }})();
    """
    
    # Execute the memory patch
    try:
        result = await page.evaluate(memory_patch_script)
        print(f"[Memory Patcher] Found {len(result)} potential balance variables")
        
        # Also try to force a re-render
        await page.evaluate("""
            // Force canvas redraw
            document.querySelectorAll('canvas').forEach(canvas => {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    // Trigger a repaint
                    canvas.style.display = 'none';
                    canvas.offsetHeight; // Force reflow
                    canvas.style.display = '';
                }
            });
            
            // Dispatch custom events that might trigger updates
            window.dispatchEvent(new Event('resize'));
            window.dispatchEvent(new CustomEvent('balanceUpdate', { detail: { balance: """ + str(target_balance) + """ } }));
        """)
        
        return result
        
    except Exception as e:
        print(f"[Memory Patcher] Error: {e}")
        return []

async def main():
    target_balance = 777.77
    
    async with async_playwright() as p:
        # Launch browser with debugging enabled
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--enable-unsafe-webgpu'
            ]
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the game
        print("[Memory Patcher] Loading game...")
        await page.goto("http://127.0.0.1:8001/game/95426", timeout=60000)
        
        # Wait for game to load
        await asyncio.sleep(5)
        
        # Patch memory every few seconds
        for i in range(10):
            print(f"[Memory Patcher] Patch attempt {i+1}/10")
            await patch_game_memory(page, target_balance)
            await asyncio.sleep(3)
        
        print("[Memory Patcher] Patching complete. Check the game!")
        
        # Keep browser open
        await asyncio.sleep(60)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())