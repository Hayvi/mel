// Pragmatic Play Specific Interceptor - Canvas Direct Approach
// Directly intercepts canvas rendering calls - MUST RUN BEFORE GAME LOADS

(function() {
    'use strict';
    
    let melBetBalance = 777.77;
    
    // Identify which frame we're in
    const frameInfo = window === window.top ? 'TOP FRAME' : 'IFRAME: ' + window.location.href.substring(0, 50);
    console.log('[Pragmatic Canvas] EARLY INIT in', frameInfo);
    
    // IMMEDIATELY intercept canvas - before any game code runs
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        console.log('[Pragmatic Canvas] getContext called:', contextType, 'in', frameInfo);
        const context = originalGetContext.call(this, contextType, ...args);
        
        // Intercept 2D context
        if (context && contextType === '2d' && !context._melBetIntercepted) {
            context._melBetIntercepted = true;
            console.log('[Pragmatic Canvas] Intercepting 2D context in', frameInfo);
            
            const originalFillText = context.fillText.bind(context);
            context.fillText = function(text, x, y, maxWidth) {
                let modifiedText = text;
                
                if (typeof text === 'string') {
                    // Replace ANY large balance-like number
                    const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
                    modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                        const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                        // Only replace credit/balance values (typically > 500), not bet amounts or buy prices
                        if (numValue > 500) {
                            console.log('[Pragmatic Canvas] REPLACING fillText:', match, '->', dollar + melBetBalance.toFixed(2));
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
                        if (numValue > 500) {
                            console.log('[Pragmatic Canvas] REPLACING strokeText:', match, '->', dollar + melBetBalance.toFixed(2));
                            return dollar + melBetBalance.toFixed(2);
                        }
                        return match;
                    });
                }
                
                return originalStrokeText(modifiedText, x, y, maxWidth);
            };
        }
        
        // Also intercept WebGL context
        if (context && (contextType === 'webgl' || contextType === 'webgl2') && !context._melBetIntercepted) {
            context._melBetIntercepted = true;
            console.log('[Pragmatic Canvas] WebGL context detected in', frameInfo, '- Game likely uses WebGL for rendering');
        }
        
        return context;
    };
    
    // Also intercept CanvasRenderingContext2D prototype directly for existing contexts
    const proto = CanvasRenderingContext2D.prototype;
    const origFillText = proto.fillText;
    const origStrokeText = proto.strokeText;
    
    proto.fillText = function(text, x, y, maxWidth) {
        let modifiedText = text;
        if (typeof text === 'string') {
            const balanceRegex = /(\$?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})/g;
            modifiedText = text.replace(balanceRegex, (match, dollar, whole, decimal) => {
                const numValue = parseFloat(whole.replace(/,/g, '') + '.' + decimal);
                // Only replace credit/balance values (typically > 500), not bet amounts or buy prices
                if (numValue > 500) {
                    console.log('[Pragmatic Canvas] PROTO fillText:', match, '->', dollar + melBetBalance.toFixed(2));
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
                if (numValue > 500) {
                    return dollar + melBetBalance.toFixed(2);
                }
                return match;
            });
        }
        return origStrokeText.call(this, modifiedText, x, y, maxWidth);
    };
    
    // Listen for balance updates
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 777.77;
            console.log('[Pragmatic Canvas] Balance updated in', frameInfo, ':', melBetBalance);
        }
    });
    
    console.log('[Pragmatic Canvas] Canvas interception ready in', frameInfo);
    
})();