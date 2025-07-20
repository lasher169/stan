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
            close_price REAL,         -- Price at close
            open_crossover_date DATETIME,  -- Date when crossover occurred
            close_crossover_date DATETIME -- Date when crossover occurred
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

def track_stock(ticker, stage, price, cross_date):
    initialize_db()
    conn = sqlite3.connect('stocks1.db')
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    stage = stage.lower()

    try:
        cursor.execute('''
            SELECT rowid, open_date, close_date, close_price 
            FROM tracked_stocks
            WHERE ticker = ?
            ORDER BY open_date DESC
            LIMIT 1
        ''', (ticker,))
        last_entry = cursor.fetchone()

        if last_entry is None:
            if stage == 'stage2':
                cursor.execute('''
                    INSERT INTO tracked_stocks (ticker, open_date, open_price, open_cross_date)
                    VALUES (?, ?, ?, ?)
                ''', (ticker, today, price, cross_date))
            else:
                print(f"{ticker}: Stage {stage[-1]} but no existing position — skipping.")

        else:
            rowid, _, close_date, close_price = last_entry

            if stage == 'stage2':
                if close_date is not None and close_price is not None:
                    cursor.execute('''
                        INSERT INTO tracked_stocks (ticker, open_date, open_price, open_cross_date)
                        VALUES (?, ?, ?, ?)
                    ''', (ticker, today, price, cross_date))
                else:
                    print(f"{ticker}: Already has open position — skipping Stage 2 insert.")

            elif stage == 'stage3':
                if close_date is None and close_price is None:
                    cursor.execute('''
                        UPDATE tracked_stocks
                        SET close_date = ?, close_price = ?, close_cross_date = ?
                        WHERE rowid = ?
                    ''', (today, price, cross_date, rowid))
                    print(f"{ticker}: Closed open position at Stage 3.")
                else:
                    print(f"{ticker}: Already closed — skipping Stage 3.")

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()