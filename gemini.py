from dotenv import load_dotenv
load_dotenv()
import os
import google.generativeai as genai
import itertools
import time
import pandas as pd
from io import StringIO


API_KEYS = [
    os.getenv("GOOGLE_API_KEY1"),
    os.getenv("GOOGLE_API_KEY2"),
    os.getenv("GOOGLE_API_KEY3"),
    os.getenv("GOOGLE_API_KEY4"),
    os.getenv("GOOGLE_API_KEY5"),
    os.getenv("GOOGLE_API_KEY6")
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
    #"""Configures the Gemini API with the next available API key."""
    next_key = get_next_api_key()
    genai.configure(api_key=next_key)
    return next_key

# Set initial API key
current_api_key = configure_gemini()
# Configure the API key
genai.configure(api_key=current_api_key)


def enforce_rate_limit():
    """Ensures requests do not exceed the allowed limit per API key per minute."""
    global current_api_key

    if api_usage[current_api_key] >= REQUEST_LIMIT:
        print(f"API key {current_api_key} reached limit. Switching keys...")
        # current_api_key = configure_gemini()
        # api_usage[current_api_key] = 0  # Reset usage for the new key
        print(f"Switched to API key: {current_api_key}")

    api_usage[current_api_key] += 1
    print(f"Using API key {current_api_key}, Request Count: {api_usage[current_api_key]}")

def generate_insight(logger, data):
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
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        content = []


        for row in data:
            content.append(f"{row.date},{row.open},{row.high},{row.low},{row.close},{row.volume}\n")

            # === Base rules for all stocks ===
            base_prompt = (
                "Act as a strict rules-based trading analyst. Using the provided OHLCV data, determine the stock's current stage based on the classic Stan Weinstein method.\n\n"
                "**Stage Rules:**\n"
                "1. **Stage 1 (Basing):** The 30-day SMA is flattening (trending sideways). Price oscillates above and below the 30-day SMA.\n"
                "2. **Stage 2 (Advancing):** Must meet ALL the following criteria, ALL on the SAME day:\n"
                "   a. **Breakout:** The CLOSE is decisively ABOVE the Stage 1 resistance level. Define resistance as the highest CLOSE during the entire basing period (or at least the prior 6–8 weeks).\n"
                "   b. **Crossover:** The 5-day SMA is ABOVE the 30-day SMA (bullish 5/30 crossover).\n"
                "   c. **Volume:** Volume is at least 2 TIMES the 30-day average volume on the breakout day.\n"
                "   - When ALL criteria occur on the SAME bar, Stage 2 is confirmed IMMEDIATELY on the breakout day. Do NOT wait for additional confirmation or for higher highs/lows.\n\n"
                "3. **Stage 3 (Topping):** After a Stage 2 advance, the 30-day SMA flattens. Price action becomes choppy and more frequently crosses below the 30-day SMA. A bearish 5/30 crossover may occur.\n"
                "4. **Stage 4 (Declining):** The price is consistently below a declining 30-day SMA, with the 5-day SMA also below. Price forms lower highs and lower lows.\n\n"
                "**Note on volume bar colors:** Infer bar color from price:\n"
                "- If today’s close is lower than the previous day’s close, the volume bar is red.\n"
                "- If today’s close is equal to or higher than the previous day’s close, the volume bar is green.\n"
                "- Red bars are NOT selling pressure, just a down close.\n\n"
                "**Evaluation method:**\n"
                "- Always check the most recent data first. For Stage 2, look for the FIRST bar that meets ALL the Stage 2 breakout conditions above, using the resistance definition as specified.\n"
                "- Return the earliest date where a valid Stage 2 breakout occurs (do not wait for later breakouts in the same run-up).\n"
                "- If the stock is no longer in Stage 2, do not report Stage 2 as current.\n\n"
                "Return only this format:\n"
                "STAGEX Crossover on YYYY-MM-DD at $CLOSE_PRICE\n"
            )
            # base_prompt = (
            #     "Act as a rules-based trading analyst. Using the provided OHLCV data, determine the stock's current stage based on a strict, classic Stan Weinstein method.\n\n"
            #     "**Stage Rules:**\n"
            #     "1. **Stage 1 (Basing):** The 30-day SMA is flattening (trending sideways). The price oscillates above and below the 30-day SMA.\n"
            #     "2. **Stage 2 (Advancing):** Must meet all three criteria, all on the same day:\n"
            #     "   a. **Breakout:** The price closes decisively above the Stage 1 resistance range, with a bullish 5/30 SMA crossover in place.\n"
            #     "   b. **Volume:** The breakout occurs on volume at least 2 times the 30-day average.\n"
            #     "   c. **Do NOT wait for a pattern of higher highs or higher lows. Stage 2 is confirmed immediately on the breakout day if the above conditions are met.**\n"
            #     "   - After entry, monitor for continuation, but entry is made on breakout day if above criteria are met.\n\n"
            #     "3. **Stage 3 (Topping):** After a Stage 2 advance, the 30-day SMA flattens. Price action becomes choppy and more frequently crosses below the 30-day SMA. A bearish 5/30 crossover may occur.\n"
            #     "4. **Stage 4 (Declining):** The price is consistently below a declining 30-day SMA, often with the 5-day SMA also below. Price forms lower highs and lower lows.\n\n"
            #     "**Note on volume bar colors:** You must infer volume bar color from price:\n"
            #     "- If today’s close is lower than the previous day’s close, the volume bar is red.\n"
            #     "- If today’s close is equal to or higher than the previous day’s close, the volume bar is green.\n"
            #     "- **Do not treat red bars as selling pressure.** Red simply reflects a down close, and may still occur during a strong Stage 2.\n\n"
            #     "Evaluate the most recent data first. Identify:\n"
            #     "- The current stage of the stock (STAGE1, STAGE2, STAGE3, or STAGE4) based on the latest data.\n"
            #     "- The most recent **confirmed 5/30 bullish crossover** date and closing price that initiated a valid Stage 2 breakout, if one ever occurred in the data.\n"
            #     "- **Always output the most recent valid 5/30 bullish crossover date and price, even if the current stage is not Stage 2. If no Stage 2 breakout occurred, return 'None' for the crossover date and price.**\n"
            #     "- Never report Stage 2 if the stock is now in Stage 3 or Stage 4.\n\n"
            #     "Return only the following format:\n"
            #     "STAGEX Crossover on YYYY-MM-DD at $CLOSE_PRICE\n"
            # )


        csv_header = "\n\nDate, Open, High, Low, Close, Volume\n"
        csv_data = ', '.join(map(str, content))
        prompt = f"{base_prompt}{csv_header}{csv_data}"

        logger.info(prompt)

        response = model.generate_content(prompt)

        # store this insight into a db table
        print(f"Gemini Response: {response.text}")
        return response.text

    except Exception as e:
        logger.error(f"Error: {e} (API Key: {key}). Not retrying.")
        return None  # Or handle it as needed

if __name__ == "__main__":
    ticker = "14D"
    generate_insight(ticker)