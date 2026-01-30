from flask import Blueprint, jsonify, request, session
from app.blueprints.main import login_required
import app.services.db as db

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/search_users')
@login_required
def search_users_api():
    query = request.args.get('q', '')
    if len(query) < 2: return jsonify([])
    users = db.search_users(query)
    # Filter self
    users = [u for u in users if u['id'] != session['user_id']]
    return jsonify(users)

@bp.route('/contacts')
@login_required
def get_contacts_api():
    contacts = db.get_contacts(session['user_id'])
    return jsonify(contacts)

@bp.route('/add_contact', methods=['POST'])
@login_required
def add_contact_api():
    data = request.json
    target_id = data.get('user_id')
    if db.add_contact(session['user_id'], target_id):
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@bp.route('/block_user', methods=['POST'])
@login_required
def block_user_api():
    data = request.json
    target_id = data.get('user_id')
    if db.block_user(session['user_id'], target_id):
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@bp.route('/blocked_users')
@login_required
def get_blocked_users_api():
    blocked = db.get_blocked_users(session['user_id'])
    return jsonify(blocked)

@bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile_api():
    data = request.json
    email = data.get('email')
    bio = data.get('bio')
    avatar = data.get('avatar_url')

    db.update_user_profile(session['user_id'], email, bio, avatar)
    return jsonify({'status': 'ok'})
