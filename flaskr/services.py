import json
import os
from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db
from .blog import get_element_by_title, clean_key

bp = Blueprint("services", __name__, url_prefix="/services")


@bp.route("/", methods=("GET",))
@login_required
def index():
    return render_template("services/services.html", messages=[])

@bp.route("/get-prompt-to-compare-games", methods=("GET",))
def get_prompt_to_compare_games():
    return render_template("services/get-prompt-to-compare-games.html")

@bp.route("/get-prompt-to-load-elements", methods=("GET",))
def get_prompt_to_load_elements():
    game_title = request.args.get('game_title', 'INPUT_HERE_THE_TITLE_OF_THE_GAME_YOU_ARE_INTERESTED_IN')
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../flaskr/static/dictionary/dictionary.json'))
    with open(data_path, 'r') as f:
        game_data_json = json.load(f)
        
        prompt = """Generate a JSON dictionary structure for the """ + game_title + """ game. 
        Use the example structure below as a guide: \n""" + json.dumps(game_data_json, indent=2) + """
        \nAdd new elements that are relevant to the game but not present in the example structure.
        \nDelete irrelevant elements that do not pertain to the game.
        \nThe JSON structure should be nested appropriately to reflect relationships between elements (e.g., characters within locations, items associated with quests).
        \nEnsure that each element type has a title and a description that provides sufficient detail about its role in the game.
        \nThe final output should be a valid JSON dictionary that can be easily parsed and used for further processing.
        \nAdd a description to each new type of element you add.
        \nDo not include any explanations or additional text outside of the JSON structure.
        \nJSON should contain only the descriptions of the types of elements of the game, not the actual elements.
        \nIt means that I want to get the structure of the types of elements that the game contains, not the actual elements.
        \nI will use this structure to prepare the actual elements data for the game later.
        \nThen generate another the JSON data that following the structure that you generated and contains the actual elements.
        \nThen generate the text with tab delimiter that contains the titles of the type of element and the value of element.
        \nOne tab-delimited line per element type and value. Use the character unocode U+0009 as a delimiter.
        \n"""
        return prompt
    
    return "Error generating prompt."

def add_element_from_dict(just_check_flag, db, title, body, parent_id=None):
    if body.strip() == '' or title.strip() == '':
        return
                
    # Check if element already exists
    existing_element = get_element_by_title(db, title)

    if not existing_element:
        print('Added element: ', title, '. body: ', body, '. parent_id: ', parent_id)
        if just_check_flag:
            return None
        else:
            cursor = db.execute(
                "INSERT INTO element (title, body, parent_id, author_id) VALUES (?, ?, ?, ?)",
                (clean_key(title), body, parent_id, g.user["id"])
            )
            db.commit()
            return cursor.lastrowid
    
    return existing_element['id']

def load_elements_recursive(just_check_flag, ids, db, dict_data, parent_id=None):
    for key, value in dict_data.items():
            #body = item.get('description', item.get('body', ''))
            if key.strip().lower() == 'description':
                continue
            
            if isinstance(value, str): # or isinstance(value, int) or isinstance(value, float):
                id = add_element_from_dict(just_check_flag, db, clean_key(key), value, parent_id)
                ids.append({ 'id': id, 'title': clean_key(key), 'body': value })
                #messages.append({'key': clean_key(key), 'value': value, 'id': id})
                
            elif isinstance(value, dict):
                print('debug', 'dict found for key: ' + str(clean_key(key)))
                description = value.get('description', '')
                new_parent_id = add_element_from_dict(just_check_flag, db, clean_key(key), description, parent_id)
                ids.append({ 'id': new_parent_id, 'title': clean_key(key), 'body': description })
                #messages.append({'key': clean_key(key), 'value': description, 'id': parent_id})
                
                for sub_key, sub_value in value.items():
                    if sub_key.strip().lower() == 'description':
                        continue
                    
                    if isinstance(sub_value, str):
                        id = add_element_from_dict(just_check_flag, db, clean_key(sub_key), sub_value, new_parent_id)
                        ids.append({ 'id': id, 'title': clean_key(sub_key), 'body': sub_value })
                    elif isinstance(sub_value, dict):
                        print('debug', 'SUB dict found for key: ' + str(clean_key(sub_key)))
                        
                        description = sub_value.get('description', '')
                        new_sub_parent_id = add_element_from_dict(just_check_flag, db, clean_key(sub_key), description, new_parent_id)
                        ids.append({ 'id': new_sub_parent_id, 'title': clean_key(sub_key), 'body': description })
                        
                        load_elements_recursive(just_check_flag, ids, db, sub_value, parent_id=new_sub_parent_id)
                    #messages.append({'sub_key': clean_key(sub_key), 'sub_value': sub_value, 'id': id})
                        
            else:
                pass
                #messages.append({'key': clean_key(key), 'value': 'Unsupported data type'})

@bp.route("/load-elements", methods=("GET", "POST"))
@login_required
def load_elements():
    messages = []
    ids = []
    
    if request.method == "POST":
        db = get_db()
        json_input = request.form.get('json_input')
        
        just_check_flag = True if request.form.get('just_check_flag') else False
        print('just_check_flag = ' + str(just_check_flag))
        
        if not json_input:
            # Load dictionary logic here
            data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../flaskr/static/dictionary/dictionary.json'))
            with open(data_path, 'r') as f:
                game_data_json = json.load(f)
        else:
            try:
                game_data_json = json.loads(json_input)
            except Exception as e:
                messages.append('Error loading elements: ' + str(e))
        
        elements_data = game_data_json.get("game", {})
        try:
            load_elements_recursive(just_check_flag, ids, db, elements_data)
            messages.append('Elements loaded successfully.')
        except Exception as e:
            messages.append('Error loading elements: ' + str(e))
        
    return render_template("services/load-elements.html", messages=messages, ids=ids)

@bp.route("/delete-elements", methods=("GET", "POST"))
@login_required
def delete_elements():
    messages = []
    ids = []
        
    if request.method == "POST":
        db = get_db()
        just_check_flag = True if request.form.get('just_check_flag') else False
        print('just_check_flag = ' + str(just_check_flag))
        
        try:
            all_elements = db.execute(
                "SELECT id, title FROM element WHERE id NOT IN (SELECT DISTINCT element_id FROM game_and_element)"
            ).fetchall()

            for element in all_elements:
                if not just_check_flag:
                    db.execute("DELETE FROM element WHERE id = ?", (element['id'],))
                ids.append({'id': element['id'], 'title': element['title']})

            if not just_check_flag:
                db.commit()
            #messages.append('Elements deleted successfully.')
        except Exception as e:
            messages.append('Error deleting elements: ' + str(e))
            
    return render_template("services/delete-elements.html", messages=messages, ids=ids)

@bp.route("/delete-game-elements", methods=("GET", "POST"))
@login_required
def delete_game_elements():
    messages = []
    ids = []
        
    if request.method == "POST":
        db = get_db()
        just_check_flag = True if request.form.get('just_check_flag') else False
        print('just_check_flag = ' + str(just_check_flag))
        
        try:
            all_game_elements = db.execute(
                "SELECT id, description, game_id FROM game_and_element WHERE game_id NOT IN (SELECT DISTINCT id FROM game)"
            ).fetchall()

            for game_element in all_game_elements:
                if not just_check_flag:
                    db.execute("DELETE FROM game_and_element WHERE id = ?", (game_element['id'],))
                ids.append({'game_id': game_element['game_id'], 'id': game_element['id'], 'title': game_element['description']})

            if not just_check_flag:
                db.commit()
            #messages.append('Elements deleted successfully.')
        except Exception as e:
            messages.append('Error deleting game elements: ' + str(e))
            
    return render_template("services/delete-game-elements.html", messages=messages, ids=ids)
