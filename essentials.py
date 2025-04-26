from ibapi.client import *
from ibapi.wrapper import *
from ibapi.contract import Contract
import time
import threading
import datetime as dt

port = 4002

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.valid_id_received = threading.Event()
        self.data = []
        self.dividends = []
        self.orderId = None
        self.lock = threading.Lock()

    def nextValidId(self, orderId):
        self.orderId = orderId
        self.valid_id_received.set()

    def nextId(self):
        with self.lock:
            self.orderId += 1
            return self.orderId

    def historicalData(self, reqId, bar):
        self.data.append(bar)

    def historicalDataEnd(self, reqId, start, end):
        self.done.set()

    def get_historical_data(self, symbol, duration="60 D", bar_size="1 day"):
        self.data = []  # Clear previous data
        self.done = threading.Event()

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "AUD"

        now = dt.datetime.now().strftime('%Y%m%d %H:%M:%S Australia/Sydney')
        self.reqHistoricalData(self.nextId(), contract, now, duration, bar_size, "TRADES", 1, 1, False, [])

        # Wait until data is received or timeout
        self.done.wait(timeout=10)
        return self.data

    def get_dividend_data(self, symbol, duration="10 Y", bar_size="1 year", currency="AUD"):          # Clear previous data
        self.done = threading.Event()

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = currency

        self.reqHistoricalData(
            self.nextId(),
            contract,
            '',
            duration,
            bar_size,
            "DIVIDENDS",
            1,
            1,
            False, []
        )

        # Wait until data is received or timeout
        self.done.wait(timeout=10)
        return self.data