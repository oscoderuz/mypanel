"""
Authentication Blueprint
=========================
Login, Logout, and First-run Admin Setup.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from database import db
from models import User

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Требуются права администратора.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler."""
    
    # Check if first run (no users exist)
    if User.query.count() == 0:
        return redirect(url_for('auth.setup'))
    
    # Already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'
        
        # Validate input
        if not username or not password:
            flash('Введите имя пользователя и пароль.', 'danger')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Аккаунт деактивирован.', 'danger')
                return render_template('auth/login.html')
            
            # Login successful
            login_user(user, remember=remember)
            user.update_last_login()
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """First-run admin account creation."""
    
    # Redirect if users already exist
    if User.query.count() > 0:
        flash('Панель уже настроена.', 'info')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно быть не менее 3 символов.')
        
        if not email or '@' not in email:
            errors.append('Введите корректный email.')
        
        if not password or len(password) < 6:
            errors.append('Пароль должен быть не менее 6 символов.')
        
        if password != password_confirm:
            errors.append('Пароли не совпадают.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/login.html', is_setup=True)
        
        try:
            # Create admin user
            admin = User(
                username=username,
                email=email,
                password=password,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            
            flash('Администратор создан! Теперь войдите в систему.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка создания пользователя: {str(e)}', 'danger')
    
    return render_template('auth/login.html', is_setup=True)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            email = request.form.get('email', '').strip()
            if email:
                current_user.email = email
                db.session.commit()
                flash('Профиль обновлен.', 'success')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not current_user.check_password(current_password):
                flash('Неверный текущий пароль.', 'danger')
            elif len(new_password) < 6:
                flash('Новый пароль должен быть не менее 6 символов.', 'danger')
            elif new_password != confirm_password:
                flash('Пароли не совпадают.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Пароль изменен.', 'success')
    
    return render_template('auth/profile.html')


# API endpoints for user management (admin only)
@auth_bp.route('/api/users', methods=['GET'])
@admin_required
def api_list_users():
    """List all users (admin only)."""
    users = User.query.all()
    return {'users': [u.to_dict() for u in users]}


@auth_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    """Delete a user (admin only)."""
    if user_id == current_user.id:
        return {'error': 'Нельзя удалить себя'}, 400
    
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Пользователь не найден'}, 404
    
    db.session.delete(user)
    db.session.commit()
    
    return {'success': True, 'message': 'Пользователь удален'}
