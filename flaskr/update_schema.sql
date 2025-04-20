ALTER TABLE game_and_element
ADD COLUMN parent_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE;
