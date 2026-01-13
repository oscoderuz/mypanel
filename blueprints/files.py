"""
Files Blueprint
================
File Manager with upload, download, and code editing.
"""

import os
import stat
import shutil
import mimetypes
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

files_bp = Blueprint('files', __name__, template_folder='../templates')


def get_file_root():
    return current_app.config.get('FILE_MANAGER_ROOT', '/')


def safe_path(requested_path):
    root = get_file_root()
    if not requested_path or requested_path == '/':
        return root
    requested_path = requested_path.replace('\\', '/')
    if requested_path.startswith('/'):
        full_path = os.path.normpath(os.path.join(root, requested_path.lstrip('/')))
    else:
        full_path = os.path.normpath(os.path.join(root, requested_path))
    if not full_path.startswith(os.path.normpath(root)):
        return None
    return full_path


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def get_file_info(path):
    try:
        stat_info = os.stat(path)
        is_dir = os.path.isdir(path)
        return {
            'name': os.path.basename(path),
            'path': path,
            'is_dir': is_dir,
            'size': stat_info.st_size if not is_dir else 0,
            'size_human': format_size(stat_info.st_size) if not is_dir else '-',
            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            'permissions': stat.filemode(stat_info.st_mode),
            'mode': oct(stat_info.st_mode)[-3:]
        }
    except (OSError, PermissionError):
        return None


@files_bp.route('/')
@login_required
def manager():
    return render_template('files/manager.html')


@files_bp.route('/api/list')
@login_required
def api_list():
    requested_path = request.args.get('path', '/')
    full_path = safe_path(requested_path)
    if not full_path:
        return jsonify({'error': 'Недопустимый путь'}), 400
    if not os.path.exists(full_path):
        return jsonify({'error': 'Путь не найден'}), 404
    if not os.path.isdir(full_path):
        return jsonify({'error': 'Это не директория'}), 400
    try:
        items = []
        for name in os.listdir(full_path):
            item_path = os.path.join(full_path, name)
            info = get_file_info(item_path)
            if info:
                info['relative_path'] = item_path.replace(get_file_root(), '').replace('\\', '/')
                if not info['relative_path'].startswith('/'):
                    info['relative_path'] = '/' + info['relative_path']
                items.append(info)
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        parent = None
        if full_path != get_file_root():
            parent = os.path.dirname(full_path).replace(get_file_root(), '').replace('\\', '/') or '/'
        return jsonify({'path': requested_path, 'parent': parent, 'items': items})
    except PermissionError:
        return jsonify({'error': 'Нет доступа'}), 403


@files_bp.route('/api/read')
@login_required
def api_read():
    requested_path = request.args.get('path', '')
    full_path = safe_path(requested_path)
    if not full_path or not os.path.exists(full_path):
        return jsonify({'error': 'Файл не найден'}), 404
    if os.path.isdir(full_path):
        return jsonify({'error': 'Это директория'}), 400
    if os.path.getsize(full_path) > 10 * 1024 * 1024:
        return jsonify({'error': 'Файл слишком большой'}), 400
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        mime_type, _ = mimetypes.guess_type(full_path)
        return jsonify({'path': requested_path, 'content': content, 'mime_type': mime_type})
    except UnicodeDecodeError:
        with open(full_path, 'r', encoding='latin-1') as f:
            content = f.read()
        return jsonify({'path': requested_path, 'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/save', methods=['POST'])
@login_required
def api_save():
    data = request.get_json() or {}
    requested_path = data.get('path', '')
    content = data.get('content', '')
    full_path = safe_path(requested_path)
    if not full_path:
        return jsonify({'error': 'Недопустимый путь'}), 400
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'message': 'Файл сохранен'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json() or {}
    parent_path = data.get('path', '/')
    name = secure_filename(data.get('name', '').strip())
    item_type = data.get('type', 'file')
    if not name:
        return jsonify({'error': 'Недопустимое имя'}), 400
    parent_full = safe_path(parent_path)
    if not parent_full:
        return jsonify({'error': 'Недопустимый путь'}), 400
    full_path = os.path.join(parent_full, name)
    if os.path.exists(full_path):
        return jsonify({'error': 'Уже существует'}), 400
    try:
        if item_type == 'directory':
            os.makedirs(full_path)
        else:
            with open(full_path, 'w') as f:
                pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/rename', methods=['POST'])
@login_required
def api_rename():
    data = request.get_json() or {}
    requested_path = data.get('path', '')
    new_name = secure_filename(data.get('new_name', '').strip())
    if not new_name:
        return jsonify({'error': 'Недопустимое имя'}), 400
    full_path = safe_path(requested_path)
    if not full_path or not os.path.exists(full_path):
        return jsonify({'error': 'Файл не найден'}), 404
    new_path = os.path.join(os.path.dirname(full_path), new_name)
    try:
        os.rename(full_path, new_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/delete', methods=['POST'])
@login_required
def api_delete():
    data = request.get_json() or {}
    requested_path = data.get('path', '')
    full_path = safe_path(requested_path)
    if not full_path or not os.path.exists(full_path):
        return jsonify({'error': 'Файл не найден'}), 404
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/chmod', methods=['POST'])
@login_required
def api_chmod():
    data = request.get_json() or {}
    requested_path = data.get('path', '')
    mode_str = data.get('mode', '')
    full_path = safe_path(requested_path)
    if not full_path or not os.path.exists(full_path):
        return jsonify({'error': 'Файл не найден'}), 404
    try:
        os.chmod(full_path, int(mode_str, 8))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@files_bp.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    target_path = request.form.get('path', '/')
    full_path = safe_path(target_path)
    if not full_path or not os.path.isdir(full_path):
        return jsonify({'error': 'Недопустимый путь'}), 400
    files = request.files.getlist('files')
    uploaded = []
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            if filename:
                file.save(os.path.join(full_path, filename))
                uploaded.append(filename)
    return jsonify({'success': True, 'uploaded': uploaded})


@files_bp.route('/api/download')
@login_required
def api_download():
    requested_path = request.args.get('path', '')
    full_path = safe_path(requested_path)
    if not full_path or not os.path.exists(full_path) or os.path.isdir(full_path):
        return jsonify({'error': 'Файл не найден'}), 404
    return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))
