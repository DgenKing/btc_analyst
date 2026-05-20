CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, venue TEXT NOT NULL, timeframe TEXT NOT NULL, open_time INTEGER NOT NULL, open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, volume REAL NOT NULL, turnover REAL, PRIMARY KEY (symbol, venue, timeframe, open_time));
CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol, venue, timeframe, open_time DESC);
CREATE TABLE IF NOT EXISTS funding (symbol TEXT NOT NULL, venue TEXT NOT NULL, funding_time INTEGER NOT NULL, funding_rate REAL NOT NULL, PRIMARY KEY (symbol, venue, funding_time));
CREATE TABLE IF NOT EXISTS open_interest (symbol TEXT NOT NULL, venue TEXT NOT NULL, ts INTEGER NOT NULL, oi REAL NOT NULL, PRIMARY KEY (symbol, venue, ts));
CREATE TABLE IF NOT EXISTS liquidations (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, venue TEXT NOT NULL, ts INTEGER NOT NULL, side TEXT NOT NULL, price REAL NOT NULL, qty REAL NOT NULL, notional REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_liq_ts ON liquidations(symbol, ts DESC);
