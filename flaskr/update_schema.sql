-- ALTER TABLE element ADD tags TEXT;

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