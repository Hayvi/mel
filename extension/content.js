// MelBet Game Integrator Content Script

const SELECTORS = [
    // Pragmatic Play
    '.balance-value',
    '.credits-value',
    '.bet-value',
    // Generic patterns
    '[class*="balance" i]',
    '[class*="credit" i]',
    '[class*="money" i]:not([class*="won"]):not([class*="win"])'
];

let currentBalance = "0.00";

// 1. Detect Frame Type
const isTopFrame = window === window.top;

if (isTopFrame) {
    console.log("[MelBet Extension] Running in Top Frame (Launcher)");
    // Listen for balance updates from the launcher's window.postMessage
    // This is the channel the existing Python-served JS uses
    window.addEventListener('message', (event) => {
        // We look for updates that indicate a balance change
        // In the existing code, we have 'walletBalance' updated
        // We can also just poll the DOM helper if we added one, 
        // but let's try to catch the sync events.

        // Better: The launcher script can explicitly ping the extension
        // For now, let's look for the HUD element we created
        const hudBalance = document.querySelector('.hud-balance');
        if (hudBalance) {
            const val = hudBalance.textContent.replace('FUN ', '').trim();
            if (val && val !== currentBalance) {
                currentBalance = val;
                chrome.storage.local.set({ melbet_balance: val });
            }
        }
    });

    // Also poll occasionally to ensure sync
    setInterval(() => {
        const hudBalance = document.querySelector('.hud-balance');
        if (hudBalance) {
            const val = hudBalance.textContent.replace('FUN ', '').trim();
            if (val && val !== currentBalance) {
                currentBalance = val;
                chrome.storage.local.set({ melbet_balance: val });
            }
        }
    }, 1000);

} else {
    console.log("[MelBet Extension] Running in Sub-Frame (Game)");

    // Listen for storage changes to update UI immediately
    chrome.storage.onChanged.addListener((changes) => {
        if (changes.melbet_balance) {
            injectNativeLook(changes.melbet_balance.newValue);
        }
    });

    // Initial load
    chrome.storage.local.get(['melbet_balance'], (result) => {
        if (result.melbet_balance) {
            injectNativeLook(result.melbet_balance);
        }
    });

    // Periodically search for balance elements (they might be dynamic)
    setInterval(() => {
        chrome.storage.local.get(['melbet_balance'], (result) => {
            if (result.melbet_balance) {
                injectNativeLook(result.melbet_balance);
            }
        });
    }, 2000);
}

function injectNativeLook(balance) {
    SELECTORS.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            // If it's a balance element, we want to replace its content
            // We tag it so we don't end up in an infinite loop or mess other things up
            if (el.getAttribute('data-mel-integrated')) {
                if (el.textContent !== balance) el.textContent = balance;
                return;
            }

            // Simple replacement for text elements
            if (el.children.length === 0) {
                el.setAttribute('data-mel-integrated', 'true');
                el.textContent = balance;
                el.style.color = '#FFC107'; // Match Gold
                el.style.fontWeight = 'bold';
            }
        });
    });
}
