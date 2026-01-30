from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import app.services.db as db
import os

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['avatar_url'] = user['avatar_url']
            session['es_admin'] = False
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html', mode='login')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if db.create_user(username, password, email):
            flash('Cuenta creada con éxito. Por favor inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('El nombre de usuario ya existe.', 'error')

    return render_template('login.html', mode='register')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route('/admin')
def admin_page():
    if session.get('es_admin'):
        return redirect(url_for('main.index'))
    return render_template('login.html', mode='admin')

@bp.route('/login_admin', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    admin_secret = os.environ.get('ADMIN_PASSWORD', 'admin123')

    if password and password == admin_secret:
        session['es_admin'] = True
        session['nick'] = 'Administrador'
        flash('¡Bienvenido, Jefe!', 'success')
        return redirect(url_for('main.index'))
    else:
        flash('Credenciales inválidas', 'error')
        return redirect(url_for('auth.admin_page'))
