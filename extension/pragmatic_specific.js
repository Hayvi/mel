// Pragmatic Play Specific Interceptor - Canvas Direct Approach
// Directly intercepts canvas rendering calls - MUST RUN BEFORE GAME LOADS

(function() {
    'use strict';
    
    let melBetBalance = 500.00; // Default, will be updated from HUD/messages
    
    // Identify which frame we're in
    const frameInfo = window === window.top ? 'TOP FRAME' : 'IFRAME: ' + window.location.href.substring(0, 50);
    console.log('[Pragmatic Canvas] EARLY INIT in', frameInfo);
    
    // Try to get balance from HUD (top frame only)
    function updateBalanceFromHUD() {
        const hudBalance = document.querySelector('.hud-balance');
        if (hudBalance) {
            const text = hudBalance.textContent.replace('FUN ', '').trim();
            const parsed = parseFloat(text.replace(/,/g, ''));
            if (!isNaN(parsed) && parsed > 0) {
                melBetBalance = parsed;
                console.log('[Pragmatic Canvas] Got balance from HUD:', melBetBalance);
                // Broadcast to iframes
                document.querySelectorAll('iframe').forEach(iframe => {
                    try {
                        iframe.contentWindow.postMessage({ type: 'MELBET_BALANCE_UPDATE', balance: melBetBalance }, '*');
                    } catch(e) {}
                });
            }
        }
    }
    
    // Poll for HUD balance in top frame
    if (window === window.top) {
        setInterval(updateBalanceFromHUD, 500);
        setTimeout(updateBalanceFromHUD, 100);
    }
    
    // IMMEDIATELY intercept canvas - before any game code runs
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        const context = originalGetContext.call(this, contextType, ...args);
        
        // Intercept 2D context
        if (context && contextType === '2d' && !context._melBetIntercepted) {
            context._melBetIntercepted = true;
            console.log('[Pragmatic Canvas] Intercepting 2D context in', frameInfo);
            
            const originalFillText = context.fillText.bind(context);
            context.fillText = function(text, x, y, maxWidth) {
                let modifiedText = text;
                
                if (typeof text === 'string') {
                    const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
                    modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                        const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                        if (numValue > 5000) {
                            return dollar + melBetBalance.toFixed(2);
                        }
                        return match;
                    });
                }
                
                return originalFillText(modifiedText, x, y, maxWidth);
            };
            
            const originalStrokeText = context.strokeText.bind(context);
            context.strokeText = function(text, x, y, maxWidth) {
                let modifiedText = text;
                
                if (typeof text === 'string') {
                    const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
                    modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                        const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                        if (numValue > 5000) {
                            return dollar + melBetBalance.toFixed(2);
                        }
                        return match;
                    });
                }
                
                return originalStrokeText(modifiedText, x, y, maxWidth);
            };
        }
        
        return context;
    };
    
    // Also intercept prototype directly
    const proto = CanvasRenderingContext2D.prototype;
    const origFillText = proto.fillText;
    const origStrokeText = proto.strokeText;
    
    proto.fillText = function(text, x, y, maxWidth) {
        let modifiedText = text;
        if (typeof text === 'string') {
            const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
            modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                if (numValue > 5000) {
                    return dollar + melBetBalance.toFixed(2);
                }
                return match;
            });
        }
        return origFillText.call(this, modifiedText, x, y, maxWidth);
    };
    
    proto.strokeText = function(text, x, y, maxWidth) {
        let modifiedText = text;
        if (typeof text === 'string') {
            const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
            modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                if (numValue > 5000) {
                    return dollar + melBetBalance.toFixed(2);
                }
                return match;
            });
        }
        return origStrokeText.call(this, modifiedText, x, y, maxWidth);
    };
    
    // Listen for balance updates from parent frame
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 500;
            console.log('[Pragmatic Canvas] Balance updated via message:', melBetBalance);
        }
    });
    
    console.log('[Pragmatic Canvas] Canvas interception ready in', frameInfo);
    
})();