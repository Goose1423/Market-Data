# Market data

Daily closing prices for the Market data tab of Portfolio Builder, in euro. Market prices only: no client data.

- `market-data.json`: about three years of daily closes for 14 markets (shares, bonds, the US 10-year yield, global property, gold, Brent oil and the VIX). Prices are converted to euro at the same day's exchange rate; the yield and the VIX are kept as they are.
- `market_fetch.py`: downloads the closes from Yahoo Finance and builds the file.
- `.github/workflows/update.yml`: runs the script every weekday evening after the US close and saves the new file here. It can also be run by hand from the **Actions** tab (Update market data → Run workflow).

Portfolio Builder reads `market-data.json` from this repository by itself; nothing needs downloading or uploading.

Source: Yahoo Finance, for the adviser's own information. Past performance is not a reliable guide to future performance.
