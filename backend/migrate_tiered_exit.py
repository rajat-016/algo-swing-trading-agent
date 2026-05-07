"""
Database migration for tiered exit system.
Adds new columns to stocks table and creates exit_logs table.
Run: python migrate_tiered_exit.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "trading.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(stocks)")
    existing = [row[1] for row in cursor.fetchall()]

    new_columns = {
        "original_quantity": "INTEGER DEFAULT 0",
        "remaining_quantity": "INTEGER DEFAULT 0",
        "current_tier": "INTEGER DEFAULT 1",
        "trailing_sl": "FLOAT",
        "sl_breach_severity": "TEXT",
    }

    for col_name, col_type in new_columns.items():
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE stocks ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name}")
        else:
            print(f"  Column exists: {col_name}")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exit_logs'")
    if cursor.fetchone() is None:
        cursor.execute("""
            CREATE TABLE exit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                tier INTEGER NOT NULL,
                exit_price FLOAT NOT NULL,
                quantity INTEGER NOT NULL,
                exit_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                exit_reason TEXT NOT NULL,
                pnl FLOAT NOT NULL,
                pnl_percentage FLOAT NOT NULL,
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        """)
        print("  Created table: exit_logs")

        cursor.execute("CREATE INDEX idx_exit_logs_stock_id ON exit_logs(stock_id)")
        print("  Created index: idx_exit_logs_stock_id")
    else:
        print("  Table exists: exit_logs")

    cursor.execute("PRAGMA table_info(stocks)")
    final = [row[1] for row in cursor.fetchall()]
    print(f"\nFinal stocks columns ({len(final)}): {', '.join(final)}")

    conn.commit()
    conn.close()
    print("\nMigration complete.")

if __name__ == "__main__":
    migrate()
