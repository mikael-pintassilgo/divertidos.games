--ALTER TABLE game_and_element
--ADD COLUMN parent_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE;

--ALTER TABLE game_and_element
--ADD COLUMN type_of_id TEXT NOT NULL DEFAULT 'element' CHECK (type_of_id IN ('element', 'game_element'));

--ALTER TABLE game_and_element
--ADD COLUMN game_element_id INTEGER REFERENCES game_and_element (id) ON DELETE CASCADE;

--ALTER TABLE game_and_element
--ADD COLUMN description TEXT;

ALTER TABLE game_and_element
ADD COLUMN previous_game_element_id INTEGER REFERENCES game_and_element (id) ON DELETE SET NULL;
