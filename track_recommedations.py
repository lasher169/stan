import sqlite3
from datetime import datetime

def initialize_db():
    conn = sqlite3.connect('stocks.db')
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_stocks (
            ticker TEXT PRIMARY KEY,
            open_date DATETIME,          -- Date when stock was first tracked
            close_date DATETIME,         -- Date when stock was closed
            open_price REAL,         -- Price at open
            close_price REAL         -- Price at close
        )
    ''')

    conn.commit()
    conn.close()

# Function to get the latest price of a stock (placeholder)
def get_latest_price(ticker):
    # Replace this with your actual price fetching logic (e.g., API, CSV, etc.)
    # For example: return 160.0 for AAPL
    return 160.0

# Function to check for price or volume rise in open stocks
def check_price_rise(ticker, open_price):
    latest_price = get_latest_price(ticker)
    if latest_price > open_price:
        print(f"[Rise] {ticker} has risen from {open_price} to {latest_price}")
    elif latest_price < open_price:
        print(f"[Drop] {ticker} has dropped from {open_price} to {latest_price}")
    else:
        print(f"[No Change] {ticker} price remains at {open_price}")

# Function to add a stock to track (open or close)
import sqlite3
from datetime import datetime

def track_stock(ticker, stage, price):
    initialize_db()
    conn = sqlite3.connect('stocks.db')
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        # Get the most recent row for this stock
        cursor.execute('''
            SELECT rowid, open_date, close_date, close_price 
            FROM tracked_stocks
            WHERE ticker = ?
            ORDER BY open_date DESC
            LIMIT 1
        ''', (ticker,))
        last_entry = cursor.fetchone()

        if last_entry is None:
            # No entry exists → insert new open
            cursor.execute('''
                INSERT INTO tracked_stocks (ticker, open_date, open_price)
                VALUES (?, ?, ?)
            ''', (ticker, today, price))
            check_price_rise(ticker, price)

        else:
            rowid, _, close_date, close_price = last_entry

            if stage == 2:
                if close_date is not None and close_price is not None:
                    # Previous entry is closed → insert new open
                    cursor.execute('''
                        INSERT INTO tracked_stocks (ticker, open_date, open_price)
                        VALUES (?, ?, ?)
                    ''', (ticker, today, price))
                    check_price_rise(ticker, price)
                # Else: existing is already open → do nothing

            elif stage == 3:
                if close_date is None and close_price is None:
                    # Close the open trade
                    cursor.execute('''
                        UPDATE tracked_stocks
                        SET close_date = ?, close_price = ?
                        WHERE rowid = ?
                    ''', (today, price, rowid))
                # Else: already closed → do nothing

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()