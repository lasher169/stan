import numpy as np
import faiss
import time
import schedule
import logging
from datetime import datetime
import yfinance as yf
from dotenv import load_dotenv
import fetch_data as market_data
import sys
import csv
import local_models

load_dotenv()

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

# FAISS index initialization (or load from file if exists)
try:
    index = faiss.read_index('faiss_index_file.index')  # Load the index from file
    logger.info("Loaded existing FAISS index.")
except Exception as e:
    index = faiss.IndexFlatL2(2)  # Create a new index if loading fails
    logger.info("Created new FAISS index.")


# Rate-limiting: Automatically reset API usage every minute


def store_in_faiss(features, ticker):
    # Assuming you have a FAISS index created globally
    try:
        # Add the feature vector to FAISS
        index.add(np.array([features[:2]]).astype('float32'))  # Add the first 2 features (SMA-5 and SMA-30)

        # Store ticker with its RAG status (optional: store in a dictionary or separate list)
        logger.info(f"Stored {ticker} with RAG status: {features[2]}")

        # Save index to file after each addition
        faiss.write_index(index, 'faiss_index_file.index')
        logger.info(f"FAISS index saved to 'faiss_index_file.index'.")
    except Exception as e:
        logger.error(f"Failed to store data in FAISS for {ticker}: {str(e)}")



def generate_data_for_ticker(ticker):
    try:
        logger.info(f"Processing ticker: {ticker}")
        time.sleep(1)
        stock_data = yf.download(ticker, period="60d", progress=False)
        info = yf.Ticker(ticker).info
        data = []
        data.append(["Symbol", "Sector", "Date", "Close Price", "Volume"])
        df = stock_data.reset_index()[['Date', 'Close', 'Volume']]
        for index, row in df.iterrows():
            print("date-->", row['Date'][0])
            date = row['Date'][0].strftime('%Y-%m-%d')
            close = row['Close']
            volume = row['Volume']
            data.append([ticker, date, close[0], volume[0]])
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
        return None

def main(exchange):
    # Initialize logging
    logger.info("Stock Analysis Application Started")

    try:
        # Run initial job
        logger.info("Running initial stock analysis job...")

        method = getattr(market_data, exchange, None);
        tickers = method(logger)
        if tickers:
            for ticker in tickers:
                data = generate_data_for_ticker(ticker)
                with open(f'data/{ticker.replace(".ax", "")}.csv', 'w') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)

                local_models.generate_insight(data)
        else:
            logger.warning("No stock data available")

        # Schedule daily job
        now = datetime.now()

        if now.hour >= 19:
            next_run = now + (24 - now.hour) * 3600
        else:
            next_run = now.replace(hour=19, minute=0, second=0)

        logger.info(f"Scheduling daily job at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        def job():
            try:
                logger.info("Starting daily stock analysis job...")
                tickers = getattr(market_data, exchange)

                if tickers:
                    for ticker in tickers:
                        data = generate_data_for_ticker(ticker)

                else:
                    logger.warning("No stock data available")
            except Exception as e:
                logger.error(f"Failed to run daily job: {str(e)}")

        schedule.every().day.at(next_run.strftime("%H:%M")).do(job)

        # Run scheduler
        while True:
            try:
                schedule.run_pending()
                time.sleep(10)
            except KeyboardInterrupt:
                logger.info("Application shutdown requested")
                break

    except Exception as e:
        logger.error(f"Main application error: {str(e)}")


if __name__ == "__main__":
    exchange = sys.argv[1]
    if len(exchange) == 0:
        print("Please provide an exchange name as a command-line argument.")
        sys.exit(1)

    main(exchange)