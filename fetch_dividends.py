import logging
import time
import yfinance as yf
import pandas as pd
logger = logging.getLogger('main')  # This should match the logger name from main.py

def generate_dividend_for_ticker(ticker, app, currency):
    try:
        logger.info(f"Processing ticker: {ticker}")
        time.sleep(1)

        dividends = yf.Ticker(ticker).dividends
        time.sleep(1)
        # Ensure the index is a datetime object
        dividends = dividends.to_frame()
        dividends.index = pd.to_datetime(dividends.index)

        # Add a column for the year
        dividends['Year'] = dividends.index.year

        # Group by the year and sum the dividends for each year
        dividends_summary = dividends.groupby('Year')['Dividends'].sum()

        # Optionally, you can also count the number of dividends per year
        dividends_count = dividends.groupby('Year')['Dividends'].count()
        return dividends_summary, dividends_count

    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
        return None, None