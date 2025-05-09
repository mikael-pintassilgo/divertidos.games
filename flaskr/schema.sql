-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS element;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE element (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  comment TEXT,
  tags TEXT,
  FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE element_link (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  comment TEXT,
  element_id INTEGER NOT NULL REFERENCES element (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id)
);

CREATE TABLE element_tag (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  comment TEXT,
  element_id INTEGER NOT NULL REFERENCES element (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id)
);

CREATE TABLE game (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  comment TEXT,
  
  FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE game_link (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  comment TEXT,
  game_id INTEGER NOT NULL REFERENCES game (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id) ON DELETE SET NULL
);

CREATE TABLE game_tag (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  comment TEXT,
  game_id INTEGER NOT NULL REFERENCES game (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id) ON DELETE SET NULL
);

CREATE TABLE game_and_element (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  description TEXT,
  game_id INTEGER REFERENCES game (id) ON DELETE CASCADE,
  type_of_id TEXT NOT NULL DEFAULT 'element' CHECK (type_of_id IN ('element', 'game_element')),
  element_id INTEGER REFERENCES element (id) ON DELETE RESTRICT,
  game_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES user (id),
  parent_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE,
  previous_game_element_id INTEGER REFERENCES game_and_element (id) ON DELETE SET NULL
);

DROP TABLE IF EXISTS quest;
DROP TABLE IF EXISTS quest_task;

CREATE TABLE quest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  --
  city TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  static_link TEXT,
  image_static_link TEXT,
  price real DEFAULT 0.0,
  start_point TEXT NOT NULL,
  --
  first_task_id INTEGER REFERENCES quest_task (id) ON DELETE SET NULL,
  FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE quest_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  --
  description TEXT NOT NULL,
  image_static_link TEXT,
  first_clue TEXT,
  second_clue TEXT,
  third_clue TEXT,
  answer TEXT,
  --
  next_task_id INTEGER REFERENCES quest_task (id) ON DELETE SET NULL,
  quest_id INTEGER NOT NULL REFERENCES quest (id) ON DELETE CASCADE
);