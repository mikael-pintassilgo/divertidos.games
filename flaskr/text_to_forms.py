from flask import Blueprint, jsonify
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from transformers import pipeline

from .auth import login_required
from .db import get_db

bp = Blueprint("parse", __name__, url_prefix="/parse")

"""
def _get_parse_result(nl_input=None):
    import spacy


    if nl_input is None:
        return jsonify({"error": "No input provided"}), 400
    
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(nl_input)

    parsed_data = {
          'company_name': '',
          'industry': '',
          'location': '',
          'employee_count': '',
          'launch_date': ''
    }

    print(f"User input: {nl_input}")
    
    for ent in doc.ents:
       print(f"label : {ent.label_}")
       print(f"text : {ent.text}")

    
    
    for ent in doc.ents:
          if ent.label_ == 'ORG':
                parsed_data['company_name'] = ent.text
          elif ent.label_ == 'GPE':
                parsed_data['location'] = ent.text
          elif ent.label_ == 'DATE':
                parsed_data['launch_date'] = ent.text
          elif ent.label_ == 'CARDINAL' and 'employee' in nl_input.lower():
                parsed_data['employee_count'] = ent.text

    if 'software' in nl_input.lower():
          parsed_data['industry'] = 'Software Development'
    elif 'marketing' in nl_input.lower():
          parsed_data['industry'] = 'Marketing'
    elif 'finance' in nl_input.lower():
          parsed_data['industry'] = 'Finance'


    summarizer = pipeline("summarization")
    summary = summarizer(nl_input, max_length=50, min_length=25, do_sample=False)
    print("Summary:")
    print(summary[0]['summary_text'])

    # 2. Named Entity Recognition (NER)
    ner = pipeline("ner", grouped_entities=True)
    key_elements = ner(nl_input)
    print("\nKey Elements:")
    for element in key_elements:
        print(f"{element['word']} ({element['entity_group']})")


    # 3. Classification
    classifier = pipeline("zero-shot-classification")
    categories = ["narrative", "gameplay", "UI"]
    classification = classifier(nl_input, candidate_labels=categories)
    print("\nClassification:")
    print(classification)
    for i, label in enumerate(classification['labels']):
        print(f"{i+1}. {label} ({classification['scores'][i]:.2f})")
        print(f"Value: {label}")
        print(f"Text: {classification['sequence']}")
        if label == 'UI':
            print(f"Text associated with 'UI': {classification['sequence']}")


    return jsonify(classification)

@bp.route('/feedback', methods=['POST'])
def _feedback():
    data = request.json
    feedback_text = data.get('feedback', '')
    rating = data.get('rating', '')
    email = data.get('email', '')

    db = get_db()
    db.execute('INSERT INTO feedback (feedback, rating, email) VALUES (?, ?, ?)',
                (feedback_text, rating, email))
    db.commit()
    return jsonify({'status': 'success'})

@bp.route('/view-feedback')
def _view_feedback():
    db = get_db()
    entries = db.execute('SELECT feedback, rating, email, timestamp FROM feedback ORDER BY timestamp DESC').fetchall()

    html = "<h2>User Feedback</h2><table border='1' cellpadding='5'><tr><th>Feedback</th><th>Rating</th><th>Email</th><th>Timestamp</th></tr>"
    for feedback, rating, email, timestamp in entries:
          html += f"<tr><td>{feedback}</td><td>{rating}</td><td>{email}</td><td>{timestamp}</td></tr>"
    html += "</table>"

    return html


def _extract_game_doc_info(nl_input):
    import spacy
    
    doc_text = nl_input
    if not doc_text:
        return jsonify({'error': 'No input text provided'}), 400

    # Load spaCy model
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(doc_text)

    # Zero-shot classification for labels
    classifier = pipeline("zero-shot-classification")
    labels = [
        "title", "genre", "platform", "engine", "high concept",
        "core gameplay", "primary loop", "key mechanics"
    ]
    extracted = {}

    # Try to extract title (assume first ORG or first line)
    title = ""
    for ent in doc.ents:
        if ent.label_ == "ORG":
            title = ent.text
            break
    if not title:
        title = doc_text.split('\n')[0].strip()
    extracted['title'] = title

    # Use zero-shot classification to find relevant text for each label
    for label in labels[1:]:
        #result = classifier(doc_text, candidate_labels=[label], multi_label=True)
        # Find the sentence most relevant to the label using zero-shot classification
        best_score = 0
        best_text = ""
        for sent in doc.sents:
            sent_result = classifier(sent.text, candidate_labels=[label], multi_label=True)
            score = float(sent_result['scores'][0])
            if score > best_score:
                best_score = score
                best_text = sent.text
        
        extracted[label] = {
            "score": best_score,
            "text": best_text if best_score > 0.3 else ""
        }

    # Try to extract genre/platform/engine with pattern matching
    genres = ["action", "adventure", "rpg", "strategy", "simulation", "puzzle", "shooter", "platformer", "sports"]
    platforms = ["PC", "PlayStation", "Xbox", "Switch", "Mobile", "iOS", "Android"]
    engines = ["Unity", "Unreal", "Godot", "GameMaker", "CryEngine"]

    for genre in genres:
        if genre.lower() in doc_text.lower():
            extracted['genre'] = genre
            break

    for platform in platforms:
        if platform.lower() in doc_text.lower():
            extracted['platform'] = platform
            break

    for engine in engines:
        if engine.lower() in doc_text.lower():
            extracted['engine'] = engine
            break

    return jsonify(extracted)

def __extract_game_doc_info(nl_input):
    # Example code to extract product attributes using GPT-2
    from transformers import GPT2Tokenizer, GPT2LMHeadModel
    import torch

    # Load GPT-2 model and tokenizer
    model_name = "gpt2"  # You can also try "gpt2-medium" or "gpt2-large"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)
    model.eval()

    # Define the product attributes to extract
    attributes = ["Name", "Description", "Price", "Size", "Color", "Material", "Brand"]

    # User input text
    user_text = 
    # Create a prompt for GPT-2
    prompt = f"Extract the following product attributes: {', '.join(attributes)}.\n\nText:\n{user_text}\n\nAttributes:\n"

    # Tokenize and generate
    inputs = tokenizer.encode(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(inputs, max_length=300, num_return_sequences=1, temperature=0.2)

    # Decode and print result
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(generated_text)
"""

def extract_game_doc_info(nl_input):
    from openai import OpenAI
    import os

    # Set your OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY", "sk-proj-your_api_key_here")
    print(f"api_key: {api_key}")
    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input="Write a one-sentence bedtime story about a unicorn."
    )

    print(response.output_text)


