PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    order_id TEXT NOT NULL,
    items TEXT NOT NULL DEFAULT '[]',
    amount REAL NOT NULL DEFAULT 0,
    expected_income REAL NOT NULL DEFAULT 0,
    raw_payload TEXT NOT NULL,
    pushed_to_erp INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, order_id)
);

CREATE TABLE IF NOT EXISTS status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    order_id TEXT NOT NULL,
    status TEXT NOT NULL,
    rider_status_text TEXT NOT NULL DEFAULT '',
    event_time TEXT NOT NULL,
    raw_payload TEXT NOT NULL DEFAULT '{}',
    pushed_to_erp INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, order_id, status, event_time)
);

CREATE TABLE IF NOT EXISTS push_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    order_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    request_payload TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    success INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_pushed_to_erp
    ON orders (pushed_to_erp);

CREATE INDEX IF NOT EXISTS idx_status_pushed_to_erp
    ON status (pushed_to_erp);

CREATE INDEX IF NOT EXISTS idx_push_logs_order_id
    ON push_logs (platform, order_id, data_type);
