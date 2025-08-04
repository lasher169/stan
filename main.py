import logging
import re
import sys
import threading
import time
from importlib import import_module
from logging.handlers import TimedRotatingFileHandler

import fetch_data as market_data
import ibkr  # Import the function from ibkr.py
import track_recommedations as tr

# Create a handler that rotates the log file at midnight
rotating_handler = TimedRotatingFileHandler(
    'stock_analysis.log',
    when='midnight',       # Rotate at midnight
    interval=1,            # Every 1 day
    backupCount=7,         # Keep 7 days of logs
    encoding='utf-8'
)

# Optional: add a suffix to log file names for clarity
rotating_handler.suffix = "%Y-%m-%d"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        rotating_handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


port = 4002

def get_ticker_data(app, ticker, currency, duration, bar_size, dollar_size_limit):
    total_data = ibkr.getData(app, ticker, currency, duration, bar_size, dollar_size_limit)
    return total_data


def extract_stage_and_date(text):
    """
    Extracts the stage, crossover date, and crossover price from text like:
    "STAGE2 Crossover on 2025-05-21 at $4.71"
    or
    "STAGE3 on 2025-08-01 at $5.69"

    Returns:
        (stage, cross_date, cross_price)
    """
    # Regex matches "STAGEX [Crossover] on YYYY-MM-DD at $PRICE"
    pattern = r'\b(STAGE\d{1,2})\b(?:\s+Crossover)?\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+\$([0-9]*\.?[0-9]+)'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        stage = match.group(1).upper()
        cross_date = match.group(2)
        cross_price = float(match.group(3))
        return stage, cross_date, cross_price
    else:
        return None, None, None

def process_data(app, exchange, currency, duration, bar_size, import_module, model_name, dollar_size_limit, trade_amount):
    # Initialize logging
    logger.info("Stock Analysis Application Started")

    try:
        method = getattr(market_data, exchange, None);
        tickers = method(logger)

        if tickers:
            for ticker in tickers:
                data = get_ticker_data(app, ticker, currency, duration, bar_size, dollar_size_limit)

                if data:
                    # Generate insight
                    if len(model_name) > 0:
                        insight = import_module.generate_insight(ticker, model_name, logger, data)
                    else:
                        insight = import_module.generate_insight(ticker, logger, data, None, None)

                    if insight is not None:
                        stage, open_cross_date, open_cross_price = extract_stage_and_date(insight)
                        # Only track the stock if its stage is Stage 2
                        if stage != None and stage.lower() == 'stage2' :

                            # --- PLACE ORDER LOGIC HERE ---
                            # Example: Calculate volume, price, etc.
                            # buy_price = data[-1].close
                            # volume = int(float(trade_amount)/float(buy_price))
                            # action = "BUY"  # or "put" if you mean options; "BUY" for long stock
                            # # Place the order
                            # order_result = ibkr.place_order(app, ticker, buy_price, action, exchange, currency, volume)
                            # logger.info(f"Order placed for {ticker}: {order_result}")

                            tr.track_stock(ticker, stage=stage, price=data[-1].close, open_cross_date=open_cross_date, open_cross_price=open_cross_price)
                            logger.info(f"ticker == {ticker} stage == {stage} data== {data}")

                            # Optional: place stop-loss after order fill
                            # stop_loss_price = buy_price * (1 - stop_pct)
                            # place_stop_loss(app, ticker, stop_loss_price, volume, exchange, currency)

                    else:
                        logger.info(f"ticker == {ticker} has no insights as no data found")
        else:
            logger.warning(f"No stock data available from {exchange}")

    except Exception as e:
        logger.error(f"Main application error: {str(e)}")



def check_db_stocks_still_stage_2(app, currency, duration, bar_size, import_module, model_name, dollar_size_limit):
    open_positions = tr.get_open_positions()

    for rec in open_positions:
        ticker = rec["ticker"]
        buy_date = rec["open_date"]
        open_crossover_date = rec["open_crossover_date"]
        open_crossover_price = rec["open_crossover_price"]
        print(f"Checking {ticker} flagged on {buy_date}")

        try:
            # Fetch latest market data
            data = get_ticker_data(app, ticker, currency, duration, bar_size, dollar_size_limit)

            if data:
                # Generate insight using the same process_data logic
                if model_name:
                    insight = import_module.generate_insight(ticker, model_name, logger, data)
                else:
                    insight = import_module.generate_insight(ticker, logger, data, crossover_date=open_crossover_date, crossover_price=open_crossover_price)

                if insight:
                    stage, close_crossover_date, close_crossover_price = extract_stage_and_date(insight)

                    if stage != None and close_crossover_date != None and close_crossover_price != None and stage.upper() != "STAGE2":
                        close_date = data[-1].date
                        close_price = data[-1].close
                        print(f"Closing {ticker}: moved to {stage} on {close_crossover_date} at {close_crossover_price}")
                        tr.update_close_info(ticker, close_date=close_date, close_price=close_price, close_crossover_date=close_crossover_date, close_crossover_price=close_crossover_price)
                        logger.info(f"{ticker} is still in stage2")
                    else:
                        logger.info(f"{ticker} is no longer in stage2 but now in {stage}")
                else:
                    logger.info(f"No insight returned for {ticker}")
            else:
                logger.info(f"No data available for {ticker}")
        except Exception as e:
            logger.error(f"Error checking {ticker}: {e}")


if __name__ == "__main__":

    if len(sys.argv) == 0 or len(sys.argv) < 4:
        print("Please provide an exchange, currency, days of data in days (60 D), barsize (1 D) name as a command-line argument.")
        sys.exit(1)

    exchange = sys.argv[1]
    currency = sys.argv[2]
    duration = sys.argv[3]
    bar_size = sys.argv[4]
    dollar_size_limit = sys.argv[5]
    trade_amount = sys.argv[6]
    llm = sys.argv[7]

    if len(sys.argv) > 8:
        model_name = sys.argv[8]
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
    check_db_stocks_still_stage_2(app, currency, duration, bar_size, imported_module, model_name, dollar_size_limit)
    process_data(app, exchange, currency, duration, bar_size, imported_module, model_name, dollar_size_limit, trade_amount)
