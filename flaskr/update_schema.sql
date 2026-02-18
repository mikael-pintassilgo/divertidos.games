/*ALTER TABLE element
ADD COLUMN parent_id INTEGER REFERENCES element (id) ON DELETE SET NULL;


CREATE TABLE role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER REFERENCES user (id) ON DELETE SET NULL,
  service_name TEXT NOT NULL,
  feedback_text TEXT,
  is_positive BOOLEAN,
  is_negative BOOLEAN,
  version TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- vote table (works for both game and game_and_element)
CREATE TABLE IF NOT EXISTS vote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES user (id) ON DELETE SET NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('game', 'game_and_element')),
    target_id INTEGER NOT NULL,
    vote_value INTEGER NOT NULL CHECK(vote_value IN (1, -1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, target_type, target_id)
);

-- indexes for speed
CREATE INDEX IF NOT EXISTS idx_vote_target
ON vote(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_vote_user
ON vote(user_id);

CREATE TABLE IF NOT EXISTS user_role (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO role(name) VALUES ('admin');
INSERT OR IGNORE INTO role(name) VALUES ('user');
INSERT OR IGNORE INTO role(name) VALUES ('auditor');

ALTER TABLE game
ADD COLUMN status TEXT NOT NULL DEFAULT 'private' CHECK(status IN ('private', 'pending_review', 'public'));

*/