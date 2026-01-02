// MelBet Game Integrator Content Script

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

    setInterval(() => updateUI(currentBalance), 1000);
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

    const targets = [/100[,.]000([,.]00)?/g, /100\s?000/g];

    const isPragmatic = window.location.href.includes("Symbol=") ||
        window.location.href.includes("symbol=") ||
        window.location.href.includes("openGame.do");

    if (isPragmatic) {
        injectCanvasOverlay(balanceStr);
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
        overlay = document.createElement("div");
        overlay.id = ID;
        overlay.innerHTML = `
            <div class="mel-item">
                <div class="mel-label">CREDIT</div>
                <div class="mel-value" id="mel-credit">LOADING...</div>
            </div>
            <div class="mel-item">
                <div class="mel-label">BET</div>
                <div class="mel-value" id="mel-bet">2.00</div>
            </div>
            <div class="mel-item">
                <div class="mel-label">WIN</div>
                <div class="mel-value" id="mel-win">0.00</div>
            </div>
        `;

        Object.assign(overlay.style, {
            position: "fixed",
            bottom: "0",
            left: "0",
            width: "100%",
            height: "35px",
            background: "rgba(0, 0, 0, 0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 10vw",
            fontFamily: "sans-serif",
            color: "#fff",
            zIndex: "2147483647",
            pointerEvents: "none",
            boxSizing: "border-box",
            backdropFilter: "blur(4px)"
        });

        const css = `
            #${ID} .mel-item { text-align: center; min-width: 100px; }
            #${ID} .mel-label { font-size: 10px; color: #888; font-weight: bold; letter-spacing: 1px; font-family: sans-serif !important; }
            #${ID} .mel-value { font-size: 15px; font-weight: bold; color: #fff; text-shadow: 0 1px 2px #000; font-family: sans-serif !important; }
        `;
        const style = document.createElement("style");
        style.textContent = css;
        (document.head || document.documentElement).appendChild(style);
        (document.body || document.documentElement).appendChild(overlay);

        console.log("[MelBet] Injected Canvas Overlay");
    }

    if (balanceStr) {
        const creditEl = document.getElementById("mel-credit");
        if (creditEl) {
            const numericBalance = parseFloat(balanceStr.replace(/,/g, '')) || 0;
            creditEl.textContent = "FUN " + numericBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    }
}

function applyStyle(el) {
    el.setAttribute('data-mel-integrated', 'true');
    el.style.color = '#FFC107';
    el.style.fontWeight = 'bold';
    el.style.textShadow = '0 0 5px rgba(0,0,0,0.8)';
}
