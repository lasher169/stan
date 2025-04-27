import csv
import logging
import time
import fetch_data as market_data
from trade_data import IBKR
import sys
import threading
import fetch_dividends as fd
import gemini

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


port = 4002

def combine_company_dividend_data(ticker, data, dividends_summary, dividends_count):
    if len(data) > 0:
        with open(f'data/{ticker}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Open Price", "Close Price", "Volume", "High Price", "Low Price", "Dividend", "Dividend Yield"])  # Header
            for row in data:
                if len(dividends_summary) > 0:
                    if dividends_summary.get(int(row[0][0:4])) != None:
                        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], dividends_summary.get(int(row[0][0:4])), dividends_summary.get(int(row[0][0:4]))/float(row[2])])
                    else:
                        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], "N/A", "N/A"])
                else:
                    writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], "N/A", "N/A"])

def get_ticker_data(ticker, currency, duration, bar_size):
    formatted_data = []
    total_data = app.get_historical_data(ticker, currency, duration, bar_size)
    print(f"Data for {ticker}:\n", total_data)
    time.sleep(3)  # space requests to avoid rate limits
    for data in total_data:
        formatted_data.append([data.date, data.open, data.close, data.volume, data.high, data.low])

    return formatted_data

def process_data(app, exchange, currency, duration, bar_size):
    # Initialize logging
    logger.info("Stock Analysis Application Started")

    try:
        method = getattr(market_data, exchange, None);
        tickers = method(logger)

        if tickers:
            for ticker in tickers:
                dividends_summary, dividends_count = fd.generate_dividend_for_ticker(ticker+".ax", app, currency)
                data = get_ticker_data(ticker, currency, duration, bar_size)
                combine_company_dividend_data(ticker, data, dividends_summary, dividends_count)

                insight = gemini.generate_insight(ticker)
                print(insight)
                #track_rec.track_stock()

        else:
            logger.warning("No stock data available")

    except Exception as e:
        logger.error(f"Main application error: {str(e)}")

if __name__ == "__main__":

    if len(sys.argv) == 0 or len(sys.argv) < 4:
        print("Please provide an exchange, currency, days of data in days (60 D), barsize (1 D) name as a command-line argument.")
        sys.exit(1)

    exchange = sys.argv[1]
    currency = sys.argv[2]
    duration = sys.argv[3]
    bar_size = sys.argv[4]

    app = IBKR()
    app.connect("127.0.0.1", port, clientId=0)
    threading.Thread(target=app.run, daemon=True).start()
    time.sleep(3)

    if not app.valid_id_received.wait(timeout=5):
        print("Failed to receive nextValidId")
        exit()

    process_data(app, exchange, currency, duration, bar_size)
    # for i in range(3):  # or any list of tickers
    #     ticker = "14D"
    #     data = app.get_historical_data(ticker)
    #     print(f"Data for {ticker}:\n", data)
    #     time.sleep(1)  # space requests to avoid rate limits