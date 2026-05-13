import duckdb

db_path = 'data/market_data.duckdb'
conn = duckdb.connect(db_path)

# Check date range in DB
result = conn.execute('SELECT MIN(datetime), MAX(datetime), COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv').fetchone()
print(f'DB range: {result[0]} to {result[1]}, Total rows: {result[2]}, Symbols: {result[3]}')

# Check a few symbols
for sym in ['CIPLA.NS', 'RELIANCE.NS', 'TCS.NS', 'ADANIENSOL.NS']:
    r = conn.execute(f"SELECT MIN(datetime), MAX(datetime), COUNT(*) FROM ohlcv WHERE symbol = '{sym}'").fetchone()
    print(f'{sym}: {r[0]} to {r[1]}, rows={r[2]}')

conn.close()
