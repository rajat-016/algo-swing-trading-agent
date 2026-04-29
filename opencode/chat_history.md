# Chat History

## 2026-04-24

### Session 1: Order Exit Bug Fixes, Frontend Theme Toggle, ML Enhancements

**Issues Fixed:**

1. **Order Status Bug** - Exit order marked as "EXITED" even when Zerodha API failed (IP restriction)
   - Root cause: Code marked stock as EXITED without verifying order success
   - Fix: Added order verification BEFORE DB update in `loop.py:_place_exit()`
   - Changed exit order type from SL to LIMIT ( Zerodha error fix)

2. **Light Theme Toggle** - CSS targeting wrong element
   - Fix: Changed from `.app.theme-light` to `body.theme-light`
   - Added proper light theme CSS variables

3. **Auto-Refresh Countdown** - No auto-refresh
   - Added 60-second countdown timer in header
   - Auto-refresh data on countdown completion
   - Added visual countdown display

4. **Tech=0 Fix** - Technical score always showed 0
   - Added better error handling in `_calculate_technical_score()`
   - Added warning logs when score components are zero
   - Fixed `calculate_strategy_scores()` to return default score

5. **XGBoost Added** - Added to ML ensemble
   - Added XGBoost import with fallback
   - Updated `adaptive_model.py` to use XGBoost + sklearn ensemble
   - Added xgboost to requirements.txt

6. **LSTM Model** - Created new LSTM predictor
   - Created `services/ai/lstm_predictor.py`
   - 60-sequence price prediction model
   - Added tensorflow to requirements.txt

7. **ChartInk Scraping** - Only 1 stock returned
   - Enhanced selectors list
   - Added fallback regex extraction
   - Increased wait time and viewport

8. **max_positions Removed** - Holdings count blocked new entries
   - Removed max_positions check from RiskManager
   - Removed from loop.py - now only fund-based limitation

### Session 2: Order Existence Check + ChartInk Symbol Fix + Frontend Updates

**Issues Fixed:**

9. **Order Existence Check** - Before placing BUY/SELL, code now checks broker for existing orders
   - Added `_check_broker_order(symbol)` method in loop.py
   - Added `_sync_existing_order()` method in loop.py
   - Modified `_place_entry()` to check broker before placing BUY
   - Modified `_place_exit()` to check broker before placing SELL
   - Added `ORDER_FILLED` to ExitReason enum
   - Prevents duplicate orders when order already filled/pending

10. **ChartInk Symbol Extraction Fix** - Got wrong data like '1,047.05', '0.55%'
    - Changed to ONLY check first column (column 0 = Symbol)
    - Added strict validation: `text.isupper() and text.isalpha()`
    - Added BLOCKLIST for header words
    - Also handles symbols in links (`a[href*='/charts/']`)
    - Added regex fallback with stricter pattern

11. **Countdown Timer Dynamic** - Now matches trading cycle from backend
    - Added `cycle_interval_seconds` to TradingStatus in trading.py
    - Added `cycle_interval_seconds` to get_status() in loop.py
    - Frontend fetches from API and uses for countdown

12. **Table Fonts Fixed** - Mismatched fonts in table
    - Table headers: `var(--font-display)` - Outfit
    - Table cells: `var(--font-display)` - Outfit (matching)
    - Symbol column: `var(--font-mono)` - JetBrains Mono
    - Price/Target/SL cells: `var(--font-mono)` - JetBrains Mono

**Files Modified:**
- `frontend/src/App.js` - Theme toggle + countdown + dynamic interval
- `frontend/src/index.css` - Body-based theme classes + table fonts
- `backend/services/trading/loop.py` - Order checks + sync methods + status
- `backend/models/stock.py` - Added ORDER_FILLED
- `backend/services/ai/analyzer.py` - Better error handling
- `backend/services/ai/adaptive_model.py` - XGBoost addition
- `backend/services/ai/lstm_predictor.py` - New file (LSTM)
- `backend/services/broker/chartink.py` - Enhanced scraping
- `backend/requirements.txt` - xgboost, tensorflow
- `backend/api/routes/trading.py` - cycle_interval_seconds
- `backend/core/config.py` - cycle_interval_seconds

---

## 2026-04-24 (Continued)

### Session 3: DB Sync Logic Fixes, ChartInk Fix, Frontend UI Fixes

**Issues Fixed:**

1. **Holdings Sync Logic** - Wrong status for stocks
   - Changed: check `qty + t1_qty + t2_qty >= 1` for ENTERED
   - If all 0: mark as NOT_HOLDING/EXITED
   - Fixed: SILVERCASE (qty=0,t1=0) → EXITED, AXISBANK (t1=4) → ENTERED
   - File: `backend/services/broker/kite.py:sync_holdings_to_db()`

2. **ChartInk Symbol Extraction** - Got DOCTYPE, NREUM, LICENSE
   - Expanded BLOCKLIST with HTML tags
   - Changed selectors to target stock links (`a[href*='/stocks/']`)
   - Added regex patterns for data-symbol extraction
   - File: `backend/services/broker/chartink.py:fetch_stocks()`

3. **P&L% Calculation** - Wrong weighted average
   - Changed: `total_pnl / total_invested * 100` instead of avg of percentages
   - File: `backend/api/routes/stocks.py:get_portfolio_summary()`

4. **Font Consistency** - Ensure monospace for numbers
   - Added `font-family: var(--font-mono)` to `.pnlCell`
   - File: `frontend/src/index.css`

5. **Light Theme Grid** - Grid overlay hidden in light theme
   - Changed: Show grid-overlay in light theme with subtle borders
   - File: `frontend/src/index.css`

6. **Position Sync** - Handle negative qty
   - qty < 0 = EXITED, qty > 0 = ENTERED
   - File: `backend/services/broker/kite.py:sync_positions_to_db()`

7. **Order Sync Overwriting Status** - Orders sync was overwriting holdings/positions
   - Fixed: Order sync only updates broker_status, not stock.status
   - Added: When COMPLETE, check holdings (qty+t1+t2 >= 1) → ENTERED
   - Added: Check positions (qty < 0 = EXITED, qty > 0 = ENTERED)
   - File: `backend/services/broker/kite.py:sync_order_status_to_db()`

8. **Delete Rejected Stocks** - Never bought stocks cluttered DB
   - Deleted stocks with broker_status = REJECTED
   - Removed: NESTLEIND, TATACONSUM

**Final DB State:**
- AXISBANK: ENTERED (holdings t1=4)
- LIQUIDCASE: ENTERED (holdings qty=1)
- TATASTEEL: ENTERED (holdings qty=14)
- SILVERCASE: EXITED (position qty=-5, sold)

---

*End of chat history*