import logging
import re
import sys
import threading
import time
from importlib import import_module

import fetch_data as market_data
import ibkr  # Import the function from ibkr.py
import track_recommedations as tr

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

def get_ticker_data(ticker, currency, duration, bar_size, dollar_size_limit):
    total_data = ibkr.getData(app, ticker, currency, duration, bar_size, dollar_size_limit)
    return total_data


def extract_stage_and_date(text):
    # Match formats like: "STAGE3 on 2025-05-22"
    match = re.search(r'\b(STAGE\d)\b\s+on\s+(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)

    if match:
        stage = match.group(1).upper()
        date = match.group(2)
        return stage, date

    # Fallback: if only stage present
    stage_match = re.search(r'\b(STAGE\d)\b', text, re.IGNORECASE)
    stage = stage_match.group(1).upper() if stage_match else None

    return stage, None

def process_data(app, exchange, currency, duration, bar_size, import_module, model_name, dollar_size_limit):
    # Initialize logging
    logger.info("Stock Analysis Application Started")

    try:
        method = getattr(market_data, exchange, None);
        tickers = method(logger)

        if tickers:
            for ticker in tickers:
                # dividends_summary, dividends_count = fd.generate_dividend_for_ticker(ticker+".ax", app, currency)
                data = get_ticker_data(ticker, currency, duration, bar_size, dollar_size_limit)

                if data:
                    # Generate insight
                    if len(model_name) > 0:
                        insight = import_module.generate_insight(ticker, model_name, logger, data)
                    else:
                        insight = import_module.generate_insight(ticker, logger, data)

                    if insight != None:
                        stage, date = extract_stage_and_date(insight)
                        # Only track the stock if its stage is Stage 2
                        if stage.lower() == 'stage2' :
                            tr.track_stock(ticker, stage=stage, price=data[-1].close, cross_date=date)

                        print("ticker == ",ticker, "stage == ",stage, "data==", data)
                    else:
                        print("ticker == ",ticker, 'has no insights as no data found')
        else:
            logger.warning(f"No stock data available from {exchange}")

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
    dollar_size_limit = sys.argv[5]
    llm = sys.argv[6]

    if len(sys.argv) > 7:
        model_name = sys.argv[7]
    else:
        model_name = ""


    # Initialize IBKR connection using the setup function
    app = ibkr.setup_ibkr()  # Call the imported function
    threading.Thread(target=app.run, daemon=True).start()
    time.sleep(3)

    if not app.valid_id_received.wait(timeout=5):
        print("Failed to receive nextValidId")
        exit()

    imported_module = import_module(llm)

    # Ensure the database is initialized before processing data
    tr.initialize_db()
    process_data(app, exchange, currency, duration, bar_size, imported_module, model_name, dollar_size_limit)
