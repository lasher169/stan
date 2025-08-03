import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


USER = "postgres.fxvqlreibfzfzvwkvbll"
PASSWORD = "E@M0nSkyl@r!8"
HOST = "aws-0-ap-southeast-2.pooler.supabase.com"
PORT = 6543
DBNAME = "postgres"

def initialize_db():
    # Connect to the database
    try:
        conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful!")

        # Create a cursor to execute SQL queries
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracked_stocks (
                    ticker TEXT PRIMARY KEY,
                    open_date TIMESTAMP,
                    close_date TIMESTAMP,
                    open_price DOUBLE PRECISION,
                    close_price DOUBLE PRECISION,
                    open_crossover_date TIMESTAMP,
                    close_crossover_date TIMESTAMP,
                    open_crossover_price DOUBLE PRECISION,
                    close_crossover_price DOUBLE PRECISION
                )
            ''')

        conn.commit()
        conn.close()

        # Close the cursor and connection
        cursor.close()
        print("Connection closed.")

    except Exception as e:
        print(f"Failed to connect: {e}")




# Function to get the latest price of a stock (placeholder)
def get_latest_price(ticker):
    # Replace this with your actual price fetching logic (e.g., API, CSV, etc.)
    # For example: return 160.0 for AAPL
    return 160.0


# Function to add a stock to track (open or close)

def track_stock(ticker, stage, price, open_cross_date, open_cross_price):
    initialize_db()
    conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
    print("Connection successful!")
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    stage = stage.lower()

    try:
        cursor.execute('''
            SELECT open_date, close_date, close_price 
            FROM tracked_stocks
            WHERE ticker = %s
            ORDER BY open_date DESC
            LIMIT 1
        ''', (ticker,))
        last_entry = cursor.fetchone()

        # If there is no entry inside the table and stock is stage2 just insert
        if last_entry is None:
            if stage == 'stage2':
                cursor.execute('''
                    INSERT INTO tracked_stocks (ticker, open_date, open_price, open_crossover_date, open_crossover_price)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (ticker, today, price, open_cross_date, open_cross_price))
            else:
                print(f"{ticker}: Stage {stage[-1]} but no existing position — skipping.")

        else:
            # We have found an existing entry.
            # This entry had been in stage2 and left stage2 so we closed it off previously. We can add another entry in.
            id, _, close_date, close_price = last_entry
            if stage == 'stage2':
                if close_date is not None and close_price is not None:
                    cursor.execute('''
                        INSERT INTO tracked_stocks (ticker, open_date, open_price, open_crossover_date, open_crossover_price)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (ticker, today, price, open_cross_date, open_cross_price))
                else:
                    print(f"{ticker}: Already has open position — skipping Stage 2 insert.")
        conn.commit()
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    """
    Retrieve all currently open stock positions from the 'tracked_stocks' PostgreSQL table.

    An open position is defined as a row where:
    - 'close_date' is NULL
    - 'close_price' is NULL

    Returns:
        List[Dict]: A list of dictionaries, each containing the following keys:
            - 'ticker': The stock symbol
            - 'open_date': The date the position was opened
            - 'open_crossover_date': The date a bullish 5/30 crossover occurred
            - 'open_crossover_price': The close price on the crossover date
    """
def get_open_positions():
    conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
    print("Connection successful!")
    c = conn.cursor()
    c.execute("SELECT ticker, open_date, open_crossover_date, open_crossover_price FROM tracked_stocks WHERE close_date IS NULL AND close_price IS NULL")
    rows = c.fetchall()
    conn.close()
    return [{"ticker": row[0], "open_date": row[1], "open_crossover_date": row[2], "open_crossover_price": row[3]} for row in rows]

def update_close_info(ticker, close_date, close_price, close_crossover_date, close_crossover_price):
    """
    Update the close information for an open position in the 'tracked_stocks' table.

    Args:
        ticker (str): Stock symbol to update.
        close_date (str): Date the position is being closed (YYYY-MM-DD).
        close_price (float): Price at which the position is closed.
        close_crossover_date (str): Date of the bearish 5/30 crossover (if applicable). This comes from LLM
        close_crossover_price (float): Price at the close crossover date. This comes from LLM

    Notes:
        Only updates rows where 'close_date' is currently NULL (i.e., still open).
    """
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")

    # Create a cursor object
    c = conn.cursor()

    # Execute the update query using %s placeholders (correct for psycopg2)
    c.execute("""
        UPDATE tracked_stocks
        SET close_date = %s,
            close_price = %s,
            close_crossover_date = %s,
            close_crossover_price = %s
        WHERE ticker = %s AND close_date IS NULL
    """, (close_date, close_price, close_crossover_date, close_crossover_price, ticker))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()