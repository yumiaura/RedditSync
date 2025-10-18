-- subscriptions: list of threads to monitor
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL UNIQUE,
    title TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- news: posts and comments
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,  -- Reddit ID (e.g., t1_... for comments or t3_... for posts)
    thread_id TEXT,  -- foreign key to subscriptions.thread_id
    author TEXT,
    created_utc INTEGER,
    title TEXT,
    body TEXT,
    media_url TEXT,  -- original URL
    media_uid TEXT,  -- filename in media/ directory if downloaded
    raw_json TEXT,   -- optional: full record in JSON
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES subscriptions(thread_id)
);

-- media: downloaded files information
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid_filename TEXT NOT NULL UNIQUE,
    original_url TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Add r/unixporn as default subscription
INSERT OR IGNORE INTO subscriptions (thread_id, title) VALUES ('unixporn', 'r/unixporn - Unix Customization');