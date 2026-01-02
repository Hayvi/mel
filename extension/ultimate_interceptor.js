// Ultimate Interceptor - Catches EVERYTHING
// Uses MutationObserver to intercept any DOM changes and replace balance text

(function() {
    'use strict';
    
    let melBetBalance = 777.77;
    const BALANCE_PATTERNS = [
        /\$?100[,.]?000[,.]?00/g,
        /\$?\d{3}[,.]?\d{3}[,.]?\d{2}/g,
        /\b\d{6,}\b/g
    ];
    
    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            melBetBalance = parseFloat(e.data.balance) || 777.77;
            console.log('[Ultimate Interceptor] Balance updated:', melBetBalance);
        }
    });
    
    function replaceBalanceText(text) {
        if (typeof text !== 'string') return text;
        
        let modified = text;
        const replacement = melBetBalance.toLocaleString('en-US', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
        
        BALANCE_PATTERNS.forEach(pattern => {
            if (pattern.test(modified)) {
                const oldText = modified;
                modified = modified.replace(pattern, replacement);
                if (oldText !== modified) {
                    console.log('[Ultimate Interceptor] Text replaced:', oldText, '->', modified);
                }
            }
        });
        
        return modified;
    }
    
    // Ultimate DOM observer - catches ALL changes
    function setupUltimateDOMObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                // Handle added nodes
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.TEXT_NODE) {
                        const newValue = replaceBalanceText(node.nodeValue);
                        if (newValue !== node.nodeValue) {
                            node.nodeValue = newValue;
                        }
                    } else if (node.nodeType === Node.ELEMENT_NODE) {
                        scanAndReplaceInElement(node);
                    }
                });
                
                // Handle modified text nodes
                if (mutation.type === 'characterData') {
                    const newValue = replaceBalanceText(mutation.target.nodeValue);
                    if (newValue !== mutation.target.nodeValue) {
                        mutation.target.nodeValue = newValue;
                    }
                }
                
                // Handle attribute changes that might contain balance
                if (mutation.type === 'attributes') {
                    const element = mutation.target;
                    const attrValue = element.getAttribute(mutation.attributeName);
                    if (attrValue) {
                        const newValue = replaceBalanceText(attrValue);
                        if (newValue !== attrValue) {
                            element.setAttribute(mutation.attributeName, newValue);
                        }
                    }
                }
            });
        });
        
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeOldValue: true,
            characterDataOldValue: true
        });
        
        console.log('[Ultimate Interceptor] Ultimate DOM observer active');
        return observer;
    }
    
    function scanAndReplaceInElement(element) {
        // Scan all text nodes in the element
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let node;
        while (node = walker.nextNode()) {
            const newValue = replaceBalanceText(node.nodeValue);
            if (newValue !== node.nodeValue) {
                node.nodeValue = newValue;
            }
        }
        
        // Also check element attributes
        if (element.attributes) {
            Array.from(element.attributes).forEach(attr => {
                const newValue = replaceBalanceText(attr.value);
                if (newValue !== attr.value) {
                    element.setAttribute(attr.name, newValue);
                }
            });
        }
    }
    
    // Brute force scanner - runs periodically
    function bruteForceScanner() {
        // Scan entire document
        scanAndReplaceInElement(document.documentElement);
        
        // Also scan canvas elements for any text content
        document.querySelectorAll('canvas').forEach((canvas, i) => {
            // Try to access canvas context and redraw
            const ctx2d = canvas.getContext('2d');
            if (ctx2d) {
                // Force a redraw by slightly modifying the canvas
                const imageData = ctx2d.getImageData(0, 0, 1, 1);
                ctx2d.putImageData(imageData, 0, 0);
            }
            
            const webgl = canvas.getContext('webgl') || canvas.getContext('webgl2');
            if (webgl) {
                // Try to force a WebGL redraw
                webgl.viewport(0, 0, canvas.width, canvas.height);
            }
        });
        
        // Scan all global variables for balance-like numbers
        Object.keys(window).forEach(key => {
            try {
                const value = window[key];
                if (typeof value === 'number' && value >= 100000 && value <= 10000000) {
                    window[key] = melBetBalance;
                    console.log(`[Ultimate Interceptor] Replaced window.${key}: ${value} -> ${melBetBalance}`);
                }
            } catch (e) {
                // Ignore access errors
            }
        });
    }
    
    // Override ALL possible text-setting methods
    function overrideAllTextMethods() {
        // Override Node.prototype.textContent
        const originalTextContent = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
        if (originalTextContent && originalTextContent.set) {
            Object.defineProperty(Node.prototype, 'textContent', {
                ...originalTextContent,
                set: function(value) {
                    const newValue = replaceBalanceText(value);
                    return originalTextContent.set.call(this, newValue);
                }
            });
        }
        
        // Override Element.prototype.innerHTML
        const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
        if (originalInnerHTML && originalInnerHTML.set) {
            Object.defineProperty(Element.prototype, 'innerHTML', {
                ...originalInnerHTML,
                set: function(value) {
                    const newValue = replaceBalanceText(value);
                    return originalInnerHTML.set.call(this, newValue);
                }
            });
        }
        
        // Override HTMLElement.prototype.innerText
        const originalInnerText = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'innerText');
        if (originalInnerText && originalInnerText.set) {
            Object.defineProperty(HTMLElement.prototype, 'innerText', {
                ...originalInnerText,
                set: function(value) {
                    const newValue = replaceBalanceText(value);
                    return originalInnerText.set.call(this, newValue);
                }
            });
        }
        
        console.log('[Ultimate Interceptor] All text methods overridden');
    }
    
    // Initialize everything
    function initialize() {
        console.log('[Ultimate Interceptor] Initializing ultimate interception...');
        
        overrideAllTextMethods();
        setupUltimateDOMObserver();
        
        // Run brute force scanner immediately and then periodically
        bruteForceScanner();
        setInterval(bruteForceScanner, 2000); // Reduced frequency
        
        // Also run a more aggressive scan less frequently
        setInterval(() => {
            console.log('[Ultimate Interceptor] Running aggressive scan...');
            bruteForceScanner();
            
            // Try to trigger game events that might cause a redraw
            window.dispatchEvent(new Event('resize'));
            window.dispatchEvent(new CustomEvent('balanceUpdate', { 
                detail: { balance: melBetBalance } 
            }));
        }, 2000);
        
        console.log('[Ultimate Interceptor] Ultimate interception initialized');
    }
    
    // Initialize immediately and also after DOM is ready
    initialize();
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    }
    
    // Also initialize after a delay to catch late-loading content
    setTimeout(initialize, 1000);
    setTimeout(initialize, 3000);
    setTimeout(initialize, 5000);
    
})();