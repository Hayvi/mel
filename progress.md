# Project Progress: MelBet Game Integration

This document outlines the current state of the MelBet Virtual Wallet integration, specifically regarding the "Canvas Overlay" solution for real-money/demo balance masking.

## Project Status: COMPLETED (Phase 1)

The primary objective was to ensure the virtual wallet balance from the MelBet launcher correctly reflects inside the game UI, even when the game uses `<canvas>` rendering which prevents direct DOM text manipulation.

### Accomplishments
- **Dynamic Content Script**: Implemented a Manifest V3 extension (`extension/content.js`) that injects logic into every frame.
- **Canvas Overlay Solution**: Developed a deterministic UI overlay for Pragmatic Play games that mimics the native footer.
- **Multi-Frame Synchronization**: Used `window.postMessage` to sync balance data between the launcher (top frame) and the game (sub-frames/iframes) robustly.
- **Shadow DOM Support**: Recursively traverses Shadow DOM for direct text replacement in games that use it (e.g., NetEnt).
- **Automated Verification**: Integrated a Playwright-based testing flow into `scrape_melbet_games.py` to capture screenshots and verify injection across cross-origin frames.

## Technical Architecture

### 1. The Launcher (`scrape_melbet_games.py`)
- Acts as a local proxy/server for the MelBet game environment.
- Serves the "Virtual Wallet" HUD at the top of the page.
- Launches Chromium with the extension pre-loaded.

### 2. The Extension (`extension/content.js`)
- **Top Frame**: Watches the HUD for balance changes and broadcasts them to all child iframes.
- **Sub-Frames**: Listens for balance updates and applies both "Native Look" (DOM replacement) and "Canvas Overlay" (DOM injection) strategies.
- **Canvas Detection**: Specifically targets Pragmatic Play URL patterns and injects a `div` styled to match the game's footer.

## How to Test/Run

### Manual Testing
```bash
# Clean up any stuck ports first
pkill -f scrape_melbet_games.py; fuser -k 8000/tcp 2>/dev/null

# Launch a game with a specific balance
python3 scrape_melbet_games.py --launch 95426 --balance 5000.00
```

### Automated Verification
```bash
# Saves a screenshot to extension_verification.png
python3 scrape_melbet_games.py --launch 95426 --test-extension --balance 777.77
```

## Known Challenges & Solutions
- **CORS/CSP**: Solved by using `add_init_script` in the launcher for guaranteed injection in cross-origin frames where standard extension injection might be delayed or blocked.
- **Canvas Rendering**: Solved by using an overlay with `pointer-events: none`, allowing visual masking while maintaining click-through functionality for game buttons.
- **Timing**: Use `MutationObserver` combined with `setInterval` to handle dynamic balance updates and late-joining frames.

## Future Recommendations
- **Broaden Provider Support**: Add coord-based or visual-matching overlays for other canvas providers (e.g., Play'n GO).
- **Style Presets**: Create a dictionary of brand-specific styles for the overlay to exactly match different game providers' footers.
- **Enhanced Debugging**: Maintain the `--test-extension` flag as a regression test for any upstream changes to the game's URL structure.
