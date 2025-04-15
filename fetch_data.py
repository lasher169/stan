import requests
import pandas as pd
def process_tickers(logger, data):
    try:
        tickers = []
        rows = data.get('data').get('table').get('rows', [])
        for row in rows:
            ticker = row.get('symbol')
            if ticker:
                tickers.append(ticker)
        logger.info(f"Successfully processed {len(tickers)} stock symbols")
        return sorted(tickers)
    except Exception as e:
        logger.error(f"Failed to process tickers: {str(e)}")
        return []

def fetch_nasdaq_stocks(logger):
    url = "https://api.nasdaq.com/api/screener/stocks"
    params = {
        "limit": 4050,
        "exchange": "nasdaq"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    try:
        logger.info("Fetching NASDAQ stocks data...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        nasdaq_data = response.json()
        logger.info(f"Successfully fetched {len(nasdaq_data.get('data').get('table').get('rows', []))} stocks")
        data = process_tickers(nasdaq_data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ stocks: {str(e)}")
        return None

def fetch_asx_stocks(logger):
    url = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    try:
        logger.info("Fetching ASX stocks data...")
        df = pd.read_csv(url, skiprows=1)
        logger.info(f"Successfully fetched {df.shape} stocks")
        data = []
        for index, row in df.iterrows():
            data.append(row['ASX code'])
        return data
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ stocks: {str(e)}")
        return None