from flask import Blueprint, render_template, redirect, url_for, session
from app.blueprints.main import login_required
import app.services.db as db

bp = Blueprint('chat', __name__)

@bp.route('/chat/<sala_id>')
@login_required
def chat(sala_id):
    info_sala = db.get_room_by_id(sala_id)
    if not info_sala:
        return redirect(url_for('main.index'))

    user = db.get_user_by_id(session['user_id'])
    es_admin = session.get('es_admin', False)

    return render_template('chat.html',
                           sala_id=sala_id,
                           info_sala=info_sala,
                           user=user,
                           es_admin=es_admin)
