// MelBet Game Integrator Content Script - Deep Control Mode

const SELECTORS = [
    '.credits-value',
    '.win-value',
    '.bet-value',
    '.balance-amount',
    '.user-balance',
    '.account-balance',
    '.footer-entry-value',
    '.label-value',
    '[class*="balance" i]',
    '[class*="credit" i]',
    '[class*="money" i]:not([class*="won"]):not([class*="win"])',
    '[id*="balance" i]',
    '[id*="credit" i]'
];

let currentBalance = "0.00";

const isTopFrame = window === window.top;

// Deep game control initialization
function initDeepGameControl() {
    // Override canvas rendering
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        const context = originalGetContext.call(this, contextType, ...args);
        
        if (context && contextType === '2d') {
            const originalFillText = context.fillText;
            context.fillText = function(text, x, y, maxWidth) {
                if (typeof text === 'string' && /\d{3}[,.]?\d{3}/.test(text)) {
                    const melBalance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    text = text.replace(/\d{3}[,.]?\d{3}[,.]?\d{2}/g, melBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                }
                return originalFillText.call(this, text, x, y, maxWidth);
            };
            
            const originalStrokeText = context.strokeText;
            context.strokeText = function(text, x, y, maxWidth) {
                if (typeof text === 'string' && /\d{3}[,.]?\d{3}/.test(text)) {
                    const melBalance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    text = text.replace(/\d{3}[,.]?\d{3}[,.]?\d{2}/g, melBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                }
                return originalStrokeText.call(this, text, x, y, maxWidth);
            };
        }
        
        return context;
    };
    
    // Override PIXI.js Text objects
    if (window.PIXI && window.PIXI.Text) {
        const originalPIXIText = window.PIXI.Text;
        window.PIXI.Text = function(text, style, canvas) {
            if (typeof text === 'string' && /\d{3}[,.]?\d{3}/.test(text)) {
                const melBalance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                text = text.replace(/\d{3}[,.]?\d{3}[,.]?\d{2}/g, melBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
            }
            return new originalPIXIText(text, style, canvas);
        };
        Object.setPrototypeOf(window.PIXI.Text, originalPIXIText);
        window.PIXI.Text.prototype = originalPIXIText.prototype;
    }
    
    // Override innerHTML and textContent globally
    const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
    if (originalInnerHTML) {
        Object.defineProperty(Element.prototype, 'innerHTML', {
            get: originalInnerHTML.get,
            set: function(value) {
                if (typeof value === 'string' && /\d{3}[,.]?\d{3}/.test(value)) {
                    const melBalance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    value = value.replace(/\b\d{3}[,.]?\d{3}[,.]?\d{2}\b/g, melBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                }
                return originalInnerHTML.set.call(this, value);
            }
        });
    }
    
    const originalTextContent = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
    if (originalTextContent) {
        Object.defineProperty(Node.prototype, 'textContent', {
            get: originalTextContent.get,
            set: function(value) {
                if (typeof value === 'string' && /\d{3}[,.]?\d{3}/.test(value)) {
                    const melBalance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    value = value.replace(/\b\d{3}[,.]?\d{3}[,.]?\d{2}\b/g, melBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                }
                return originalTextContent.set.call(this, value);
            }
        });
    }
    
    // Override fetch and XMLHttpRequest for API interception
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        return originalFetch(url, options).then(response => {
            if (typeof url === 'string' && (url.includes('balance') || url.includes('credit'))) {
                return response.clone().json().then(data => {
                    if (data.balance !== undefined) {
                        data.balance = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    }
                    if (data.credit !== undefined) {
                        data.credit = parseFloat(currentBalance.replace(/,/g, '')) || 0;
                    }
                    return new Response(JSON.stringify(data), {
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers
                    });
                }).catch(() => response);
            }
            return response;
        });
    };
    
    console.log("[MelBet Extension] Deep game control initialized");
}

const isTopFrame = window === window.top;

if (isTopFrame) {
    console.log("[MelBet Extension] Running in Top Frame (Launcher)");

    const broadcastBalance = (val) => {
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach(iframe => {
            try {
                iframe.contentWindow.postMessage({ type: 'MELBET_BALANCE_UPDATE', balance: val }, '*');
            } catch (e) { }
        });
    };

    setInterval(() => {
        const hudBalance = document.querySelector('.hud-balance');
        if (hudBalance) {
            const val = hudBalance.textContent.replace('FUN ', '').trim();
            if (val && val !== currentBalance) {
                currentBalance = val;
                if (typeof chrome !== 'undefined' && chrome.storage) {
                    chrome.storage.local.set({ melbet_balance: val });
                }
                broadcastBalance(val);
            }
        }
    }, 500);

    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_READY_FOR_BALANCE') {
            broadcastBalance(currentBalance);
        }
    });

} else {
    // Initialize deep game control for sub-frames
    initDeepGameControl();
    
    const updateUI = (balance) => {
        if (!balance) return;
        currentBalance = balance;
        injectNativeLook(balance, document);
        aggressiveGlobalReplace(balance);
    }

    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['melbet_balance'], (result) => {
            if (result && result.melbet_balance) updateUI(result.melbet_balance);
        });

        chrome.storage.onChanged.addListener((changes) => {
            if (changes.melbet_balance) updateUI(changes.melbet_balance.newValue);
        });
    }

    window.addEventListener('message', (e) => {
        if (e.data && e.data.type === 'MELBET_BALANCE_UPDATE') {
            updateUI(e.data.balance);
        }
    });

    try { window.parent.postMessage({ type: 'MELBET_READY_FOR_BALANCE' }, '*'); } catch (e) { }

    const observer = new MutationObserver(() => updateUI(currentBalance));

    const startObserver = () => {
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true, characterData: true });
        } else {
            setTimeout(startObserver, 100);
        }
    };
    startObserver();

    setInterval(() => updateUI(currentBalance), 2000); // Reduced frequency
}

function injectNativeLook(balanceStr, root) {
    if (!root) return;
    const numericBalance = parseFloat(balanceStr.replace(/,/g, '')) || 0;
    const formattedBalance = numericBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    SELECTORS.forEach(selector => {
        try {
            const elements = root.querySelectorAll(selector);
            elements.forEach(el => {
                if (el.getAttribute('data-mel-val') === formattedBalance) return;
                const isLikelyMoney = /[\d.,]+/.test(el.textContent);
                if (isLikelyMoney || el.classList.contains('credits-value') || el.classList.contains('win-value')) {
                    const prefix = el.textContent.includes('$') ? '$' : el.textContent.includes('€') ? '€' : '';
                    const newVal = prefix + formattedBalance;

                    if (el.textContent !== newVal && el.textContent.length < 50) {
                        if (el.children.length === 0) {
                            el.textContent = newVal;
                        } else {
                            el.childNodes.forEach(child => {
                                if (child.nodeType === Node.TEXT_NODE && /[\d,.]+/.test(child.nodeValue)) {
                                    child.nodeValue = child.nodeValue.replace(/[\d,.]+/, formattedBalance);
                                }
                            });
                        }
                        el.setAttribute('data-mel-val', formattedBalance);
                        applyStyle(el);
                    }
                }
            });
        } catch (e) { }
    });

    try {
        const all = root.querySelectorAll('*');
        all.forEach(el => {
            if (el.shadowRoot) injectNativeLook(balanceStr, el.shadowRoot);
        });
    } catch (e) { }
}

function aggressiveGlobalReplace(balanceStr) {
    if (!balanceStr) return;
    const numericBalance = parseFloat(balanceStr.replace(/,/g, '')) || 0;
    const formattedBalance = numericBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // More aggressive patterns for Pragmatic Play games
    const targets = [
        /100[,.]000([,.]00)?/g, 
        /100\s?000/g,
        /399[,.]997[,.]60/g,  // Specific to the current game balance
        /\b\d{3}[,.]?\d{3}[,.]?\d{2}\b/g  // Any 6+ digit balance pattern
    ];

    const isPragmatic = window.location.href.includes("Symbol=") ||
        window.location.href.includes("symbol=") ||
        window.location.href.includes("openGame.do");

    if (isPragmatic) {
        injectCanvasOverlay(balanceStr);
        
        // Hide native balance displays more aggressively
        const hideSelectors = [
            '[class*="credit" i]',
            '[class*="balance" i]',
            '.credit-display',
            '.balance-display',
            'div[style*="position: absolute"][style*="bottom"]', // Common for game UI overlays
        ];
        
        hideSelectors.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const text = el.textContent || '';
                    if (/\d{3}[,.]?\d{3}/.test(text)) { // If contains large numbers
                        el.style.visibility = 'hidden';
                        el.style.opacity = '0';
                    }
                });
            } catch (e) {}
        });
    }

    const walk = (node) => {
        if (!node) return;
        if (node.nodeType === Node.TEXT_NODE) {
            let val = node.nodeValue;
            let changed = false;
            targets.forEach(reg => {
                if (reg.test(val)) {
                    val = val.replace(reg, formattedBalance);
                    changed = true;
                }
            });
            if (changed) node.nodeValue = val;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.shadowRoot) walk(node.shadowRoot);
            node.childNodes.forEach(walk);
        }
    };

    if (document.body) walk(document.body);
}

function injectCanvasOverlay(balanceStr) {
    const ID = "melbet-canvas-overlay";
    let overlay = document.getElementById(ID);

    if (!overlay) {
        // Create a more native-looking overlay that matches Pragmatic Play's style
        overlay = document.createElement("div");
        overlay.id = ID;
        overlay.innerHTML = `
            <div class="mel-credit-section">
                <div class="mel-credit-bg">
                    <div class="mel-credit-label">CREDIT</div>
                    <div class="mel-credit-value" id="mel-credit">LOADING...</div>
                </div>
            </div>
        `;

        Object.assign(overlay.style, {
            position: "fixed",
            bottom: "8px",
            left: "8px",
            width: "auto",
            height: "auto",
            zIndex: "2147483647",
            pointerEvents: "none",
            fontFamily: "Arial, sans-serif"
        });

        // Style to match Pragmatic Play's native UI
        const css = `
            #${ID} .mel-credit-section {
                display: inline-block;
            }
            #${ID} .mel-credit-bg {
                background: linear-gradient(135deg, #2a1810 0%, #4a2820 50%, #2a1810 100%);
                border: 2px solid #8b6914;
                border-radius: 8px;
                padding: 4px 12px;
                box-shadow: 
                    inset 0 1px 0 rgba(255,255,255,0.2),
                    0 2px 4px rgba(0,0,0,0.8),
                    0 0 8px rgba(139,105,20,0.3);
                position: relative;
                min-width: 120px;
            }
            #${ID} .mel-credit-bg::before {
                content: '';
                position: absolute;
                top: 1px;
                left: 1px;
                right: 1px;
                height: 50%;
                background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, transparent 100%);
                border-radius: 6px 6px 0 0;
                pointer-events: none;
            }
            #${ID} .mel-credit-label {
                font-size: 9px;
                color: #d4af37;
                font-weight: bold;
                text-align: center;
                text-shadow: 0 1px 2px rgba(0,0,0,0.8);
                letter-spacing: 0.5px;
                margin-bottom: 1px;
            }
            #${ID} .mel-credit-value {
                font-size: 14px;
                color: #ffffff;
                font-weight: bold;
                text-align: center;
                text-shadow: 
                    0 1px 0 rgba(0,0,0,1),
                    0 2px 4px rgba(0,0,0,0.8);
                font-family: 'Arial Black', Arial, sans-serif;
            }
        `;
        const style = document.createElement("style");
        style.textContent = css;
        (document.head || document.documentElement).appendChild(style);
        (document.body || document.documentElement).appendChild(overlay);

        console.log("[MelBet] Injected Native-Style Canvas Overlay");
    }

    if (balanceStr) {
        const creditEl = document.getElementById("mel-credit");
        if (creditEl) {
            const numericBalance = parseFloat(balanceStr.replace(/,/g, '')) || 0;
            creditEl.textContent = numericBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    }
}

function applyStyle(el) {
    el.setAttribute('data-mel-integrated', 'true');
    el.style.color = '#FFC107';
    el.style.fontWeight = 'bold';
    el.style.textShadow = '0 0 5px rgba(0,0,0,0.8)';
}
