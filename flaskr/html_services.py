import bleach

ALLOWED_TAGS = [
    'br', 'b', 'i', 'strong', 'em', 'u',
    'a', 'p', 'ul', 'ol', 'li'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target']
}

def sanitize_html(raw_html):
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=['http', 'https', 'mailto'],
        strip=True
    )

    cleaned = bleach.linkify(
        cleaned,
        callbacks=bleach.linkifier.DEFAULT_CALLBACKS,
        skip_tags=['pre', 'code']
    )
    
    return cleaned

