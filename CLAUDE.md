# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TCC (undergraduate thesis) project: A website that finds the lowest flight prices from Brazilian airlines, comparing both cash (BRL) and loyalty points (miles) options.

## Architecture

### Azul Scraper (`azul_scraper/`)

Two scrapers for Azul airline with identical architecture but different payment methods:

- **azul_scraper_api_miles.py**: Searches flights payable with TudoAzul points (`cc=PTS`)
- **azul_scraper_api_money.py**: Searches flights payable with money (`cc=BRL`)

**How they work**:
1. Opens headless Chrome using `selenium-driverless` to visit Azul's booking page
2. Intercepts the API request via `NetworkInterceptor` to capture auth headers and request body template
3. Closes browser and makes direct API calls using `curl_cffi` with captured credentials
4. Supports date range searches (±2 days from base dates)
5. Saves responses to `debug/` folder

**Key classes**: `FlightSearchMiles`, `FlightSearchMoney`

### Smiles Scraper (`smiles_scraper/`)

- **smiles_scraper.py**: Direct API calls to Smiles (Gol loyalty program) with hardcoded cookies/headers
- Saves responses to `smiles_output/` folder
- Cookies expire and need manual updates from browser DevTools

### Legacy

- **azul_scraper_playwright.py**: Old Playwright-based implementation (deprecated)

## Date Formats

- User format: `MM/DD/YYYY` (e.g., "04/15/2026")
- API format: `YYYY-MM-DD` (e.g., "2026-04-15")
- Uses `arrow` library for conversion

## Running Scrapers

```bash
python azul_scraper/azul_scraper_api_miles.py
python azul_scraper/azul_scraper_api_money.py
python smiles_scraper/smiles_scraper.py
```

Each scraper has example usage in its `__main__` block with hardcoded parameters to modify.

## Key Dependencies

- `selenium-driverless`: Browser automation with request interception
- `curl_cffi`: HTTP requests with browser impersonation
- `arrow`: Date manipulation
- `rich`: Console output

## Important Functions

- `generate_date_range(base_date)`: Creates list of 5 dates (±2 days around base date)
- `extract_flight_info(response_data)`: Parses API response to extract prices and flight details
- `initialize_headers()`: Captures auth credentials from browser (Azul scrapers only)
- `search_date_range()`: Searches all date combinations in range
