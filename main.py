import requests
import numpy as np
import faiss
import time
import schedule
import logging
from datetime import datetime
import yfinance as yf
import os
import google.generativeai as genai
from dotenv import load_dotenv
import itertools
import fetch_data as market_data
import sys

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

# this uses my ollama version but is very slow and the GPU goes nutso
# def generate_insight(rag_status, ticker, sma_5, sma_30):
#     try:
#         # Prompt for the LLM to generate an analysis based on the stock's RAG status
#         prompt = f"you are Stan Weinstein how would you Analyze the stock with ticker {ticker}. The RAG status is {rag_status}. The 5-day SMA is {sma_5}, and the 30-day SMA is {sma_30}. I want to know the stage only."
#
#         print(prompt)
#
#         response = ollama.chat(
#             model="deepseek-r1:14b",
#             messages=[
#                 {"role": "user", "content": prompt}
#             ]
#         )
#
#         insight = response['text'].strip()
#         return insight
#
#     except Exception as e:
#         logger.error(f"Error generating insight for {ticker}: {str(e)}")
#         return "Insight generation failed"

# Load API keys from environment variables
# Load API keys from environment variables
API_KEYS = [
    os.getenv("GOOGLE_API_KEY1"),
    os.getenv("GOOGLE_API_KEY2"),
    os.getenv("GOOGLE_API_KEY3"),
    os.getenv("GOOGLE_API_KEY4"),
]

# Remove None values in case some keys are missing
API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise ValueError("No valid API keys found. Please check your environment variables.")

# Create a cycle iterator for API keys
api_key_cycle = itertools.cycle(API_KEYS)

# Track the number of requests per API key
api_usage = {key: 0 for key in API_KEYS}
REQUEST_LIMIT = 15  # Max requests per API key per minute
TIME_WINDOW = 60  # Time window in seconds (1 minute)

def get_next_api_key():
    """Returns the next API key in the cycle."""
    return next(api_key_cycle)

def configure_gemini():
    """Configures the Gemini API with the next available API key."""
    next_key = get_next_api_key()
    genai.configure(api_key=next_key)
    return next_key

# Set initial API key
current_api_key = configure_gemini()
model = genai.GenerativeModel('gemini-2.0-flash')

def enforce_rate_limit():
    """Ensures requests do not exceed the allowed limit per API key per minute."""
    global current_api_key

    if api_usage[current_api_key] >= REQUEST_LIMIT:
        print(f"API key {current_api_key} reached limit. Switching keys...")
        current_api_key = configure_gemini()
        api_usage[current_api_key] = 0  # Reset usage for the new key
        print(f"Switched to API key: {current_api_key}")

    api_usage[current_api_key] += 1
    print(f"Using API key {current_api_key}, Request Count: {api_usage[current_api_key]}")

def generate_insight(rag_status, ticker, sma_5, sma_30):
    """
    Generates an investment insight based on a given RAG status, ticker symbol,
    5-day SMA, and 30-day SMA using the Gemini Pro model.

    Args:
        rag_status (str): The RAG (Red, Amber, Green) status of the stock.
        ticker (str): The ticker symbol of the stock.
        sma_5 (float): The 5-day Simple Moving Average.
        sma_30 (float): The 30-day Simple Moving Average.

    Returns:
        str: The generated investment insight, or "Insight generation failed"
             if an error occurs.
    """
    try:
        # Introduce a 10-second delay before switching to the next API key
        time.sleep(10)

        # Switch to the next API key
        key = configure_gemini()

        prompt = f"As a technical analyst. I want to apply Stan Weinstein's staging theroy to analyze the stock with ticker {ticker}. The RAG status is {rag_status}. The 5-day SMA is {sma_5}, and the 30-day SMA is {sma_30}. Provide a *single* stage only (Stage 1, Stage 2, Stage 3, or Stage 4)."

        print(f"Sending prompt to Gemini: {prompt}")

        response = model.generate_content(prompt)
        insight = response.text.strip()

        print(f"Gemini Response: {insight}")

        # Validate stage output
        if not any(stage in insight for stage in ["Stage 1", "Stage 2", "Stage 3", "Stage 4"]):
            print(f"Invalid response: {insight}. Trying with next API key...")
            return generate_insight(rag_status, ticker, sma_5, sma_30)  # Retry with new key

        return insight

    except Exception as e:
        print(f"Error: {e} (API Key: {key}). Not retrying.")
        return None  # Or handle it as needed

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


def calculate_stock_features_with_insight(ticker):
    try:
        logger.info(f"Processing ticker: {ticker}")
        time.sleep(1)
        stock_data = yf.download(ticker, period="60d", progress=False)

        if len(stock_data) < 60:
            logger.warning(f"Not enough data for {ticker}, returning neutral features")
            return np.array([0, 0, 'Amber'])  # Default to 'Amber' if not enough data

        stock_data['5_day_SMA'] = stock_data['Close'].rolling(window=5).mean()
        stock_data['30_day_SMA'] = stock_data['Close'].rolling(window=30).mean()

        sma_5 = stock_data['5_day_SMA'].iloc[-1] if not np.isnan(stock_data['5_day_SMA'].iloc[-1]) else 0
        sma_30 = stock_data['30_day_SMA'].iloc[-1] if not np.isnan(stock_data['30_day_SMA'].iloc[-1]) else 0

        logger.info(f"Calculated features for {ticker}: SMA-5={sma_5}, SMA-30={sma_30}")

        # Determine RAG status based on SMAs
        if sma_5 > sma_30:
            rag_status = 'Green'  # Trending up
        elif sma_5 < sma_30:
            rag_status = 'Red'  # Trending down
        else:
            rag_status = 'Amber'  # Neutral or no clear trend

        # Generate insights using LLM based on RAG status
        insight = generate_insight(rag_status, ticker, sma_5, sma_30)

        # Return features with RAG status
        return np.array([sma_5, sma_30, rag_status, insight])

    except Exception as e:
        logger.error(f"Failed to calculate features for {ticker}: {str(e)}")
        return np.array([0, 0, 'Amber'])  # Default to 'Amber' in case of error


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
                features = calculate_stock_features_with_insight(ticker)

                if features is not None:
                    store_in_faiss(features, ticker)  # Store features in FAISS index
                try:
                    logger.info(f"Successfully processed {ticker}")
                except Exception as e:
                    logger.error(f"Failed to process {ticker}: {str(e)}")
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
                data = getattr(market_data, exchange)
                if data:
                    tickers = process_tickers(data)
                    if tickers:
                        for ticker in tickers:
                            features = calculate_stock_features_with_insight(ticker)
                            store_in_faiss(features, ticker)  # Store features in FAISS index
                            try:
                                logger.info(f"Successfully processed {ticker}")
                            except Exception as e:
                                logger.error(f"Failed to process {ticker}: {str(e)}")
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