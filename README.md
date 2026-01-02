# MelBet Casino Game Scraper

A Python script to scrape casino game data from MelBet Tunisia (`melbet-tn.com`). It uses an API-first approach to reliably fetch game metadata, including names, providers, categories, and direct demo launch URLs.

## Features

- **API-First Scraping**: Discovers and uses the internal JSON APIs the site uses, making it more stable than HTML-based scraping.
- **Multiple Modes**: 
  - `http` (default): Runs with only the Python standard library. No external dependencies needed.
  - `playwright`: Uses a full browser session. Can be more resilient to API changes but requires installation.
- **Flexible Data Export**: 
  - Scrape all games, or filter by one or more categories.
  - Output formats: JSON (default) or CSV.
- **Game Launching**:
  - Resolve the direct URL for a game's demo mode.
  - Includes a simple local web server to launch and embed game demos by ID.
  - **In-App Game Browser**: The local launcher can list and search all scraped games, so you can find and launch games without leaving the app.
- **Virtual Wallet Integration**:
  - **Custom HUD**: Overlays a professional "VIRTUAL WALLET" HUD on game pages to track a virtual balance in real-time.
  - **Native Look & Feel**: Includes a browser extension that automatically synchronizes the virtual balance into the game's native UI elements, overriding the native balance displays.
  - **Zero Install**: Launch everything with a single command; the browser extension is "baked in" and loaded automatically via Playwright.

## Setup

The script is designed to run without external dependencies in `http` mode.

For `playwright` mode, you'll need to install the dependencies:

```bash
# Install pip if you don't have it
# sudo apt update && sudo apt install python3-pip

# Install dependencies
python3 -m pip install -r requirements.txt

# Install the Chromium browser for Playwright
python3 -m playwright install chromium
```

## Usage

The main script is `scrape_melbet_games.py`.

### 1. List Available Game Categories

To see all available game categories and their IDs:

```bash
python3 scrape_melbet_games.py --list-categories
```

### 2. Scrape Games

- **Scrape all games (no cap) into JSON**:
  ```bash
  python3 scrape_melbet_games.py --all-categories --max 0 --out all_games.json
  ```

- **Scrape a limited number of games from a specific category**:
  ```bash
  python3 scrape_melbet_games.py --category-id 696 --max 200 --out cosmic_new_win.json
  ```

- **Output as CSV**:
  ```bash
  python3 scrape_melbet_games.py --all-categories --max 500 --format csv --out games.csv
  ```

### 3. Launch a Game

- **Get the direct demo URL for a game**:
  ```bash
  python3 scrape_melbet_games.py --game-id 95426 --demo
  ```

- **Get the URL and open it in your browser**:
  ```bash
  python3 scrape_melbet_games.py --game-id 95426 --demo --open-game
  ```

### 4. Run the Local Game Launcher

This starts a local web server that lets you launch any game demo by its ID. It also includes an in-app browser to search your locally scraped games.

```bash
python3 scrape_melbet_games.py --serve
```

Then open your browser to `http://127.0.0.1:8000`.

The launcher includes:
- A home page to launch a game by ID.
- A **/games** page to browse and search the entire list of locally scraped games (from `all_games.json`, etc.).
- A **/api/games** JSON endpoint for programmatic access to the game list.
- A **Virtual Wallet** HUD at the top of the game page.

### 5. Launch with "Native Look" (Integrated Extension)

This is the recommended mode for a fully immersive experience. It starts the server and opens a browser instance with our integration extension already loaded.

```bash
python3 scrape_melbet_games.py --launch 95426
```

This will:
1. Start the local server in the background.
2. Launch a Chromium browser session.
3. Auto-load the `./extension` folder so the virtual balance replaces the game's native balance display.

## Files

- `scrape_melbet_games.py`: The main scraper script.
- `requirements.txt`: Python dependencies (only for Playwright mode).
- `.gitignore`: Prevents large scraped data files from being committed to Git.
- `all_games.json` / `*.json`: Scraped game data output.
