// Balance Hunter - Specifically targets balance rendering
// Focuses on the exact balance display area

(function() {
    'use strict';
    
    let melBetBalance = 777.77;
    
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 777.77;
            console.log('[Balance Hunter] Target balance:', melBetBalance);
            huntBalance();
        }
    });
    
    function huntBalance() {
        console.log('[Balance Hunter] Starting balance hunt...');
        
        // Target the specific balance area coordinates
        const canvases = document.querySelectorAll('canvas');
        canvases.forEach((canvas, i) => {
            console.log(`[Balance Hunter] Scanning canvas ${i}:`, canvas.width, 'x', canvas.height);
            
            const ctx = canvas.getContext('2d');
            if (ctx) {
                // Try to intercept the specific area where balance is drawn
                interceptBalanceArea(ctx, canvas);
            }
            
            const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
            if (gl) {
                interceptWebGLBalance(gl, canvas);
            }
        });
        
        // Also hunt in DOM for any balance-related elements
        huntDOMBalance();
        
        // Hunt in global variables more aggressively
        huntGlobalBalance();
    }
    
    function interceptBalanceArea(ctx, canvas) {
        // Override fillText with position-specific logic
        const originalFillText = ctx.fillText;
        ctx.fillText = function(text, x, y, maxWidth) {
            // Check if this text is in the balance area (bottom-left region)
            const isInBalanceArea = y > canvas.height * 0.8 && x < canvas.width * 0.3;
            
            if (isInBalanceArea && typeof text === 'string') {
                // Check if this looks like a balance
                if (/\$?\d{3}[,.]?\d{3}/.test(text)) {
                    const newText = `$${melBetBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                    console.log(`[Balance Hunter] Balance area text replaced: "${text}" -> "${newText}" at (${x}, ${y})`);
                    return originalFillText.call(this, newText, x, y, maxWidth);
                }
            }
            
            return originalFillText.call(this, text, x, y, maxWidth);
        };
        
        // Also override strokeText
        const originalStrokeText = ctx.strokeText;
        ctx.strokeText = function(text, x, y, maxWidth) {
            const isInBalanceArea = y > canvas.height * 0.8 && x < canvas.width * 0.3;
            
            if (isInBalanceArea && typeof text === 'string') {
                if (/\$?\d{3}[,.]?\d{3}/.test(text)) {
                    const newText = `$${melBetBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                    console.log(`[Balance Hunter] Balance area stroke replaced: "${text}" -> "${newText}" at (${x}, ${y})`);
                    return originalStrokeText.call(this, newText, x, y, maxWidth);
                }
            }
            
            return originalStrokeText.call(this, text, x, y, maxWidth);
        };
    }
    
    function interceptWebGLBalance(gl, canvas) {
        // More aggressive WebGL interception
        const originalDrawArrays = gl.drawArrays;
        gl.drawArrays = function(mode, first, count) {
            // Log draw calls to understand rendering patterns
            console.log(`[Balance Hunter] WebGL drawArrays: mode=${mode}, first=${first}, count=${count}`);
            return originalDrawArrays.call(this, mode, first, count);
        };
        
        const originalDrawElements = gl.drawElements;
        gl.drawElements = function(mode, count, type, offset) {
            console.log(`[Balance Hunter] WebGL drawElements: mode=${mode}, count=${count}, type=${type}, offset=${offset}`);
            return originalDrawElements.call(this, mode, count, type, offset);
        };
        
        // Try to intercept uniform variables (shader parameters)
        const originalUniform1f = gl.uniform1f;
        gl.uniform1f = function(location, value) {
            // Check if this could be a balance value
            if (value >= 100000 && value <= 10000000) {
                console.log(`[Balance Hunter] WebGL uniform1f balance candidate: ${value} -> ${melBetBalance}`);
                return originalUniform1f.call(this, location, melBetBalance);
            }
            return originalUniform1f.call(this, location, value);
        };
    }
    
    function huntDOMBalance() {
        // Look for any DOM elements that might contain balance
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            // Check text content
            if (el.textContent && /\$?\d{3}[,.]?\d{3}/.test(el.textContent)) {
                const oldText = el.textContent;
                const newText = oldText.replace(/\$?\d{3}[,.]?\d{3}[,.]?\d{2}/g, `$${melBetBalance.toFixed(2)}`);
                if (oldText !== newText) {
                    el.textContent = newText;
                    console.log(`[Balance Hunter] DOM balance replaced: "${oldText}" -> "${newText}"`);
                }
            }
            
            // Check attributes
            ['title', 'alt', 'data-value', 'value'].forEach(attr => {
                const value = el.getAttribute(attr);
                if (value && /\$?\d{3}[,.]?\d{3}/.test(value)) {
                    const newValue = value.replace(/\$?\d{3}[,.]?\d{3}[,.]?\d{2}/g, `$${melBetBalance.toFixed(2)}`);
                    if (value !== newValue) {
                        el.setAttribute(attr, newValue);
                        console.log(`[Balance Hunter] DOM attribute ${attr} replaced: "${value}" -> "${newValue}"`);
                    }
                }
            });
        });
    }
    
    function huntGlobalBalance() {
        // More targeted global variable hunting
        const balanceKeywords = [
            'balance', 'credit', 'credits', 'money', 'cash', 'wallet',
            'playerBalance', 'gameBalance', 'currentBalance', 'totalBalance',
            'userBalance', 'accountBalance', 'availableBalance', 'funds'
        ];
        
        // Search in window
        Object.keys(window).forEach(key => {
            const value = window[key];
            
            // Check if key name suggests it's balance-related
            const isBalanceKey = balanceKeywords.some(keyword => 
                key.toLowerCase().includes(keyword.toLowerCase())
            );
            
            if (isBalanceKey && typeof value === 'number') {
                try {
                    window[key] = melBetBalance;
                    console.log(`[Balance Hunter] Global balance variable replaced: window.${key} = ${melBetBalance}`);
                } catch (e) {
                    console.log(`[Balance Hunter] Failed to replace window.${key}:`, e);
                }
            }
            
            // Also check for large numbers that could be balances
            if (typeof value === 'number' && value >= 100000 && value <= 10000000) {
                try {
                    window[key] = melBetBalance;
                    console.log(`[Balance Hunter] Suspicious number replaced: window.${key} ${value} -> ${melBetBalance}`);
                } catch (e) {}
            }
        });
        
        // Search in common game object locations
        const commonGameObjects = ['game', 'Game', 'GAME', 'app', 'App', 'APP', 'player', 'Player'];
        commonGameObjects.forEach(objName => {
            if (window[objName] && typeof window[objName] === 'object') {
                huntInObject(window[objName], objName);
            }
        });
    }
    
    function huntInObject(obj, path) {
        if (!obj || typeof obj !== 'object' || path.split('.').length > 5) return;
        
        try {
            Object.keys(obj).forEach(key => {
                const value = obj[key];
                const fullPath = `${path}.${key}`;
                
                if (typeof value === 'number' && value >= 100000 && value <= 10000000) {
                    try {
                        obj[key] = melBetBalance;
                        console.log(`[Balance Hunter] Object balance replaced: ${fullPath} ${value} -> ${melBetBalance}`);
                    } catch (e) {}
                } else if (typeof value === 'object' && value !== null) {
                    huntInObject(value, fullPath);
                }
            });
        } catch (e) {
            // Ignore access errors
        }
    }
    
    // Force canvas redraw
    function forceRedraw() {
        document.querySelectorAll('canvas').forEach(canvas => {
            // Try to trigger a redraw
            const event = new Event('resize');
            window.dispatchEvent(event);
            
            // Also try to invalidate the canvas
            const ctx = canvas.getContext('2d');
            if (ctx) {
                // Save and restore context to potentially trigger redraw
                ctx.save();
                ctx.restore();
            }
        });
    }
    
    // Initialize and run periodically
    function initialize() {
        console.log('[Balance Hunter] Balance hunter initialized');
        huntBalance();
        
        // Run more frequently
        setInterval(huntBalance, 200);
        setInterval(forceRedraw, 1000);
    }
    
    // Start hunting immediately and after delays
    initialize();
    setTimeout(initialize, 500);
    setTimeout(initialize, 2000);
    
})();