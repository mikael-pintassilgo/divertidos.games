ALTER TABLE game_and_element
ADD COLUMN parent_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE;

ALTER TABLE game_and_element
ADD COLUMN type_of_id TEXT NOT NULL DEFAULT 'element' CHECK (type_of_id IN ('element', 'game_element'));
