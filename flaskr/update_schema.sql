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


CREATE TABLE IF NOT EXISTS game_element_variant (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  target_type TEXT NOT NULL CHECK(target_type IN ('game', 'game_and_element')),
  title TEXT NOT NULL,

  game_id INTEGER REFERENCES game (id) ON DELETE CASCADE,
  game_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id) ON DELETE SET NULL
);

ALTER TABLE element
ADD COLUMN status TEXT NOT NULL DEFAULT 'private' CHECK(status IN ('private', 'pending_review', 'public'));

ALTER TABLE game_element_variant
ADD COLUMN status TEXT NOT NULL DEFAULT 'private' CHECK(status IN ('private', 'pending_review', 'public'));

CREATE TABLE composition_of_element (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  element_id INTEGER REFERENCES element (id) ON DELETE CASCADE,
  subelement_id INTEGER REFERENCES element (id) ON DELETE RESTRICT,
  author_id INTEGER NOT NULL REFERENCES user (id)
);

DROP TABLE IF EXISTS element_tag;

CREATE TABLE element_tag (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  comment TEXT,
  
  element_id INTEGER NOT NULL REFERENCES element (id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tag (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id)
);

ALTER TABLE game_and_element
ADD COLUMN element_order INTEGER DEFAULT 0;

ALTER TABLE user
ADD COLUMN is_authenticated BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE user
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;

ALTER TABLE user
ADD COLUMN is_anonymous BOOLEAN NOT NULL DEFAULT 0;


-- ?????
DROP TABLE IF EXISTS element_value;

CREATE TABLE element_value (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  title TEXT NOT NULL,

  status TEXT NOT NULL DEFAULT 'private' CHECK(status IN ('private', 'pending_review', 'public')),

  element_id INTEGER NOT NULL REFERENCES element (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id) ON DELETE SET NULL
);
-- END ?????

-- Adding the column for admin feedback
-- We allow NULL because new records or public ones won't have feedback yet
ALTER TABLE game_element_variant 
ADD COLUMN admin_feedback TEXT;

CREATE TABLE IF NOT EXISTS variant_status (
    name TEXT PRIMARY KEY,
    description TEXT
);

INSERT OR IGNORE INTO variant_status(name, description) VALUES ('private', 'The variant is private');
INSERT OR IGNORE INTO variant_status(name, description) VALUES ('pending_review', 'The variant is pending review');
INSERT OR IGNORE INTO variant_status(name, description) VALUES ('public', 'The variant is public');
INSERT OR IGNORE INTO variant_status(name, description) VALUES ('needs_revision', 'The variant is needs revision');


*/

ALTER TABLE game_element_variant 
ADD COLUMN status_name TEXT REFERENCES variant_status(name);

UPDATE game_element_variant SET status_name = status;

