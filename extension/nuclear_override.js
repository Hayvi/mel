// Nuclear Option: Direct Game Variable Manipulation
// This tries to find and override the actual game variables

(function() {
    'use strict';
    
    let melBetBalance = 777.77;
    
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 777.77;
            console.log('[Nuclear Override] Balance updated:', melBetBalance);
            performNuclearOverride();
        }
    });
    
    function performNuclearOverride() {
        // Try to find and override common game variable names
        const commonBalanceVars = [
            'balance', 'credit', 'credits', 'money', 'cash', 'wallet',
            'playerBalance', 'gameBalance', 'currentBalance', 'totalBalance',
            'userBalance', 'accountBalance', 'availableBalance'
        ];
        
        // Search in window object
        commonBalanceVars.forEach(varName => {
            if (window[varName] !== undefined) {
                try {
                    const oldValue = window[varName];
                    window[varName] = melBetBalance;
                    console.log(`[Nuclear Override] Overrode window.${varName}: ${oldValue} -> ${melBetBalance}`);
                } catch (e) {
                    console.log(`[Nuclear Override] Failed to override window.${varName}:`, e);
                }
            }
        });
        
        // Search in all global objects
        Object.keys(window).forEach(key => {
            const obj = window[key];
            if (obj && typeof obj === 'object') {
                commonBalanceVars.forEach(varName => {
                    if (obj[varName] !== undefined && typeof obj[varName] === 'number') {
                        try {
                            const oldValue = obj[varName];
                            obj[varName] = melBetBalance;
                            console.log(`[Nuclear Override] Overrode ${key}.${varName}: ${oldValue} -> ${melBetBalance}`);
                        } catch (e) {}
                    }
                });
            }
        });
        
        // Override Number constructor to return our balance for large numbers
        if (!window._melBetNumberOverridden) {
            const originalNumber = window.Number;
            window.Number = function(value) {
                const num = originalNumber(value);
                // If it's a balance-like number, replace it
                if (num >= 100000 && num <= 10000000) {
                    console.log(`[Nuclear Override] Number constructor override: ${num} -> ${melBetBalance}`);
                    return melBetBalance;
                }
                return num;
            };
            Object.setPrototypeOf(window.Number, originalNumber);
            window._melBetNumberOverridden = true;
        }
        
        // Override parseInt and parseFloat
        if (!window._melBetParseOverridden) {
            const originalParseInt = window.parseInt;
            const originalParseFloat = window.parseFloat;
            
            window.parseInt = function(string, radix) {
                const result = originalParseInt(string, radix);
                if (result >= 100000 && result <= 10000000) {
                    console.log(`[Nuclear Override] parseInt override: ${result} -> ${Math.floor(melBetBalance)}`);
                    return Math.floor(melBetBalance);
                }
                return result;
            };
            
            window.parseFloat = function(string) {
                const result = originalParseFloat(string);
                if (result >= 100000 && result <= 10000000) {
                    console.log(`[Nuclear Override] parseFloat override: ${result} -> ${melBetBalance}`);
                    return melBetBalance;
                }
                return result;
            };
            
            window._melBetParseOverridden = true;
        }
    }
    
    // Override JSON.parse to modify balance data
    if (!window._melBetJSONOverridden) {
        const originalJSONParse = JSON.parse;
        JSON.parse = function(text, reviver) {
            const result = originalJSONParse(text, reviver);
            
            if (result && typeof result === 'object') {
                // Recursively find and replace balance values
                function replaceBalances(obj) {
                    if (typeof obj === 'object' && obj !== null) {
                        Object.keys(obj).forEach(key => {
                            if (typeof obj[key] === 'number' && obj[key] >= 100000 && obj[key] <= 10000000) {
                                console.log(`[Nuclear Override] JSON balance override: ${key} ${obj[key]} -> ${melBetBalance}`);
                                obj[key] = melBetBalance;
                            } else if (typeof obj[key] === 'object') {
                                replaceBalances(obj[key]);
                            }
                        });
                    }
                }
                replaceBalances(result);
            }
            
            return result;
        };
        window._melBetJSONOverridden = true;
    }
    
    // Periodically scan for new variables and override them
    function scanAndOverride() {
        performNuclearOverride();
        
        // Also scan for canvas elements and try to redraw them
        const canvases = document.querySelectorAll('canvas');
        canvases.forEach(canvas => {
            if (canvas.getContext) {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    // Try to trigger a redraw by slightly modifying the canvas
                    const imageData = ctx.getImageData(0, 0, 1, 1);
                    ctx.putImageData(imageData, 0, 0);
                }
            }
        });
    }
    
    // Run periodically
    setInterval(scanAndOverride, 3000); // Reduced frequency
    
    // Run immediately
    setTimeout(performNuclearOverride, 100);
    setTimeout(performNuclearOverride, 1000);
    setTimeout(performNuclearOverride, 3000);
    
    console.log('[Nuclear Override] Nuclear option initialized');
})();