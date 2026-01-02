// Ultra-Aggressive WebGL and Rendering Interception
// This intercepts at the lowest possible level

(function() {
    'use strict';
    
    let melBetBalance = 777.77;
    
    // Listen for balance updates
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 777.77;
            console.log('[WebGL Interceptor] Balance updated:', melBetBalance);
        }
    });
    
    // Intercept WebGL at the lowest level
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        const context = originalGetContext.call(this, contextType, ...args);
        
        if (context && (contextType === 'webgl' || contextType === 'webgl2')) {
            interceptWebGLDeep(context, this);
        }
        
        return context;
    };
    
    function interceptWebGLDeep(gl, canvas) {
        console.log('[WebGL Interceptor] Intercepting WebGL context');
        
        // Intercept texture uploads (where text might be stored)
        const originalTexImage2D = gl.texImage2D;
        gl.texImage2D = function(target, level, internalformat, width, height, border, format, type, pixels) {
            // If pixels is an ImageData, Canvas, or similar, we can modify it
            if (pixels && (pixels instanceof ImageData || pixels instanceof HTMLCanvasElement)) {
                pixels = modifyTextureData(pixels);
            }
            return originalTexImage2D.call(this, target, level, internalformat, width, height, border, format, type, pixels);
        };
        
        // Intercept buffer data (for vertex/text data)
        const originalBufferData = gl.bufferData;
        gl.bufferData = function(target, data, usage) {
            if (data instanceof ArrayBuffer || data instanceof Float32Array) {
                // This is where text vertex data might be - harder to modify
                console.log('[WebGL Interceptor] Buffer data intercepted, size:', data.byteLength);
            }
            return originalBufferData.call(this, target, data, usage);
        };
        
        // Intercept draw calls
        const originalDrawArrays = gl.drawArrays;
        gl.drawArrays = function(mode, first, count) {
            // Before drawing, check if we can modify anything
            return originalDrawArrays.call(this, mode, first, count);
        };
        
        const originalDrawElements = gl.drawElements;
        gl.drawElements = function(mode, count, type, offset) {
            return originalDrawElements.call(this, mode, count, type, offset);
        };
    }
    
    function modifyTextureData(imageData) {
        // This is very complex - we'd need to analyze the image data
        // and find text patterns to replace
        console.log('[WebGL Interceptor] Texture data modification attempted');
        return imageData;
    }
    
    // More aggressive DOM interception
    function interceptAllTextMethods() {
        // Override ALL possible text-setting methods
        const textProperties = ['textContent', 'innerText', 'innerHTML', 'value'];
        
        textProperties.forEach(prop => {
            const descriptor = Object.getOwnPropertyDescriptor(Element.prototype, prop) ||
                             Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop) ||
                             Object.getOwnPropertyDescriptor(Node.prototype, prop);
            
            if (descriptor && descriptor.set) {
                const originalSetter = descriptor.set;
                Object.defineProperty(Element.prototype, prop, {
                    ...descriptor,
                    set: function(value) {
                        if (typeof value === 'string') {
                            value = replaceBalanceInText(value);
                        }
                        return originalSetter.call(this, value);
                    }
                });
            }
        });
    }
    
    function replaceBalanceInText(text) {
        if (typeof text !== 'string') return text;
        
        const patterns = [
            /\$?100[,.]?000[,.]?00/g,
            /\$?\d{3}[,.]?\d{3}[,.]?\d{2}/g,
            /\b\d{6,}\b/g
        ];
        
        let modified = text;
        const replacement = melBetBalance.toLocaleString('en-US', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
        
        patterns.forEach(pattern => {
            if (pattern.test(modified)) {
                modified = modified.replace(pattern, replacement);
                console.log('[WebGL Interceptor] Text replaced:', text, '->', modified);
            }
        });
        
        return modified;
    }
    
    // Intercept any possible game framework
    function interceptGameFrameworks() {
        // Check for common game engines
        const checkFrameworks = () => {
            // PIXI.js
            if (window.PIXI) {
                interceptPIXI();
            }
            
            // Three.js
            if (window.THREE) {
                interceptThreeJS();
            }
            
            // Phaser
            if (window.Phaser) {
                interceptPhaser();
            }
            
            // CreateJS
            if (window.createjs) {
                interceptCreateJS();
            }
        };
        
        checkFrameworks();
        setTimeout(checkFrameworks, 1000);
        setTimeout(checkFrameworks, 3000);
        setTimeout(checkFrameworks, 5000);
    }
    
    function interceptPIXI() {
        if (window.PIXI && window.PIXI.Text) {
            const originalText = window.PIXI.Text;
            window.PIXI.Text = function(text, style, canvas) {
                text = replaceBalanceInText(text);
                return new originalText(text, style, canvas);
            };
            Object.setPrototypeOf(window.PIXI.Text, originalText);
            window.PIXI.Text.prototype = originalText.prototype;
            console.log('[WebGL Interceptor] PIXI.js intercepted');
        }
    }
    
    function interceptThreeJS() {
        // Three.js text interception would go here
        console.log('[WebGL Interceptor] Three.js check');
    }
    
    function interceptPhaser() {
        // Phaser text interception would go here
        console.log('[WebGL Interceptor] Phaser check');
    }
    
    function interceptCreateJS() {
        // CreateJS text interception would go here
        console.log('[WebGL Interceptor] CreateJS check');
    }
    
    // Initialize everything
    interceptAllTextMethods();
    interceptGameFrameworks();
    
    // Brute force: periodically scan and replace all text in the DOM
    function bruteForceTextReplacement() {
        const walker = document.createTreeWalker(
            document.body || document.documentElement,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let node;
        while (node = walker.nextNode()) {
            if (node.nodeValue && /\$?\d{3}[,.]?\d{3}/.test(node.nodeValue)) {
                const newValue = replaceBalanceInText(node.nodeValue);
                if (newValue !== node.nodeValue) {
                    node.nodeValue = newValue;
                    console.log('[WebGL Interceptor] Brute force replacement');
                }
            }
        }
    }
    
    // Run brute force replacement periodically
    setInterval(bruteForceTextReplacement, 500);
    
    console.log('[WebGL Interceptor] Ultra-aggressive interception initialized');
})();