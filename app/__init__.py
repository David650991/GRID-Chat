import os
from flask import Flask, make_response, send_from_directory
from flask_socketio import SocketIO
from datetime import datetime

socketio = SocketIO()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Config
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_atomica_v2')
    # app.config['SESSION_COOKIE_HTTPONLY'] = True # Uncomment in prod
    # app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Init DB
    from app.services.db import init_db
    init_db()

    # Blueprints
    from app.blueprints import auth, main, chat, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(api.bp)

    # SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    from app.events import register_events
    register_events(socketio)

    # Global/Static Routes
    @app.route('/sw.js')
    def service_worker():
        response = make_response(send_from_directory('../static', 'sw.js'))
        response.headers['Content-Type'] = 'application/javascript'
        return response

    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('../static', 'manifest.json')

    @app.errorhandler(404)
    def page_not_found(e):
        return "404 Not Found", 404 # Simple text for now, should be template

    return app
