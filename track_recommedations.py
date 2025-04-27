import sqlite3
from datetime import datetime

# Initialize DB
conn = sqlite3.connect('stocks.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS tracked_stocks (
    ticker TEXT PRIMARY KEY,
    status TEXT,           -- 'open' or 'closed'
    weinstein_stage INTEGER,
    date TEXT,             -- date when started tracking
    price REAL             -- price at that time
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    date TEXT,
    price REAL,
    weinstein_stage INTEGER
)
''')

conn.commit()


# Function to add a stock to track
def track_stock(ticker, stage, price):
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT OR REPLACE INTO tracked_stocks (ticker, status, weinstein_stage, date, price)
        VALUES (?, 'open', ?, ?, ?)
    ''', (ticker, stage, today, price))
    conn.commit()


# Function to record nightly snapshot
def nightly_update(ticker, price, stage):
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO stock_history (ticker, date, price, weinstein_stage)
        VALUES (?, ?, ?, ?)
    ''', (ticker, today, price, stage))

    if stage == 4:  # If we hit Stage 4, close it out
        cursor.execute('''
            UPDATE tracked_stocks
            SET status = 'closed'
            WHERE ticker = ?
        ''', (ticker,))

    conn.commit()