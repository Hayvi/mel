// Advanced Canvas Interception for Full Game Control
// This script intercepts WebGL and Canvas2D rendering to modify balance displays

(function() {
    'use strict';
    
    let melBetBalance = 5000.00;
    
    // Listen for balance updates
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 5000.00;
            console.log('[Canvas Interceptor] Balance updated:', melBetBalance);
        }
    });
    
    // Intercept Canvas 2D Context
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        const context = originalGetContext.call(this, contextType, ...args);
        
        if (context && contextType === '2d') {
            interceptCanvas2D(context);
        } else if (context && (contextType === 'webgl' || contextType === 'webgl2')) {
            interceptWebGL(context);
        }
        
        return context;
    };
    
    function interceptCanvas2D(ctx) {
        // Intercept fillText
        const originalFillText = ctx.fillText;
        ctx.fillText = function(text, x, y, maxWidth) {
            const modifiedText = replaceBalanceInText(text);
            return originalFillText.call(this, modifiedText, x, y, maxWidth);
        };
        
        // Intercept strokeText
        const originalStrokeText = ctx.strokeText;
        ctx.strokeText = function(text, x, y, maxWidth) {
            const modifiedText = replaceBalanceInText(text);
            return originalStrokeText.call(this, modifiedText, x, y, maxWidth);
        };
        
        console.log('[Canvas Interceptor] Canvas 2D context intercepted');
    }
    
    function interceptWebGL(gl) {
        // For WebGL, we need to intercept texture uploads that might contain text
        const originalTexImage2D = gl.texImage2D;
        gl.texImage2D = function(...args) {
            // This is more complex - WebGL games often use texture atlases for text
            // We'd need to analyze the texture data and modify it
            return originalTexImage2D.apply(this, args);
        };
        
        console.log('[Canvas Interceptor] WebGL context intercepted');
    }
    
    function replaceBalanceInText(text) {
        if (typeof text !== 'string') return text;
        
        // Replace various balance patterns
        const patterns = [
            /\b\d{3}[,.]?\d{3}[,.]?\d{2}\b/g,  // 399,998.50 or 399998.50
            /\b\d{6,}\b/g,                      // Any 6+ digit number
            /\$\d{1,3}[,.]?\d{3}[,.]?\d{2}/g,  // $399,998.50
        ];
        
        let modifiedText = text;
        const formattedBalance = melBetBalance.toLocaleString('en-US', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
        
        patterns.forEach(pattern => {
            if (pattern.test(modifiedText)) {
                modifiedText = modifiedText.replace(pattern, formattedBalance);
                console.log('[Canvas Interceptor] Replaced text:', text, '->', modifiedText);
            }
        });
        
        return modifiedText;
    }
    
    // Intercept PIXI.js if present (common game engine)
    function interceptPIXI() {
        if (window.PIXI && window.PIXI.Text) {
            const originalPIXIText = window.PIXI.Text;
            window.PIXI.Text = function(text, style, canvas) {
                const modifiedText = replaceBalanceInText(text);
                return new originalPIXIText(modifiedText, style, canvas);
            };
            
            // Copy prototype and static properties
            Object.setPrototypeOf(window.PIXI.Text, originalPIXIText);
            window.PIXI.Text.prototype = originalPIXIText.prototype;
            
            console.log('[Canvas Interceptor] PIXI.js Text intercepted');
        }
    }
    
    // Try to intercept PIXI immediately and also after a delay
    interceptPIXI();
    setTimeout(interceptPIXI, 1000);
    setTimeout(interceptPIXI, 3000);
    
    // Intercept any dynamic script loading that might load PIXI
    const originalAppendChild = Node.prototype.appendChild;
    Node.prototype.appendChild = function(child) {
        const result = originalAppendChild.call(this, child);
        if (child.tagName === 'SCRIPT') {
            child.addEventListener('load', () => {
                setTimeout(interceptPIXI, 100);
            });
        }
        return result;
    };
    
    console.log('[Canvas Interceptor] Advanced canvas interception initialized');
})();