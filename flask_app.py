from flask import session
from flaskr import create_app
from flaskr.auth import get_user_roles

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)