CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback TEXT,
                rating INTEGER,
                email TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP