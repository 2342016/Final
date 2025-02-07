import uuid
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, redirect, url_for, session
import jwt
import datetime
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from app.models import User, db,  Memo


# データベースインスタンスの作成


SECRET_KEY = "your_secret_key"  # 本番環境では環境変数を使用

# Flaskアプリの設定
app = Flask(__name__)
POSTGRES_USER = os.getenv("POSTGRES_USER", "default_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "default_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "default_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db.init_app(app)  # ← ここを追加

with app.app_context():
    db.create_all()  # ← ここでテーブルを作成



# セッションを利用するための設定
@app.before_request
def require_login():
    allowed_routes = ['login_page', 'register_page', 'new_page', 'login', 'register', 'static']
    if request.endpoint is None:
        return  # `None` の場合は処理しない
    if 'user' not in session and request.endpoint not in allowed_routes:
        if request.endpoint != 'new_page':
            return redirect(url_for('new_page'))


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(email=data['sub']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    memos = Memo.query.order_by(Memo.created_at.desc()).all()
    return render_template('index.html', memos=memos)


# メモの詳細を表示
@app.route('/view/<uuid:memo_id>')
def view_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    return render_template('view_memo.html', memo=memo)

# 新しいメモの作成フォームを表示
@app.route('/create', methods=['GET'])
def show_create_memo():
    return render_template('create_memo.html')

@app.route('/create', methods=['POST'])
def create_memo():
    if 'user' not in session:
        return redirect(url_for('login_page'))  

    user = User.query.filter_by(email=session['user']).first()

    if user is None:
        return redirect(url_for('login_page')) 

    title = request.form['title']
    content = request.form['content']
    genre = request.form['genre']

    new_memo = Memo(title=title, content=content, genre=genre, user_id=user.id)  
    db.session.add(new_memo)
    db.session.commit()

    return redirect(url_for('index'))


# メモを削除
# ===============================
# エンドポイント /post/(メモのID)/delete
# メソッド　　POST
# 返すもの　index.html (リダイレクト)
# ===============================
@app.route('/memo/<uuid:memo_id>/delete', methods=['POST'])
def delete_memo(memo_id):
    memo = Memo.query.get_or_404(str(memo_id))
    db.session.delete(memo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/setting', methods=['GET', 'POST'])
def setting():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    user = User.query.filter_by(email=session['user']).first()
    return render_template('setting.html', user=user)

@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.filter_by(email=session['user']).first()

    if request.method == 'POST':
        new_username = request.form['username']

        # ユーザー名の重複チェック
        if User.query.filter_by(username=new_username).first() and new_username != user.username:
            return render_template('edit_user.html', user=user, error="このユーザー名は既に使われています。")

        
        user.username = new_username
        db.session.commit()

        return redirect(url_for('setting'))

    return render_template('edit_user.html', user=user)

@app.route('/delete_user', methods=['POST'])
def delete_user():
        if 'user' not in session:
            return redirect(url_for('login_page'))
    
        user = User.query.filter_by(email=session['user']).first()
    
        if user:
            db.session.delete(user)
            db.session.commit()
            session.pop('user', None)  # セッションからユーザーを削除

        return redirect(url_for('new_page'))  # `/new` にリダイレクト




@app.route('/new')
def new_page():
    return render_template('new.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(email=data['email']).first():
            return render_template('register.html', error_email="このメールアドレスは既に登録されています。")
        
        new_user = User(email=data['email'])
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login_page'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(email=data['email']).first()
        if not user:
            return render_template('login.html', error_login="このメールアドレスは登録されていません。")
        if not user.check_password(data['password']):
            return render_template('login.html', error_login="パスワードが間違っています。")

        session['user'] = user.email
        return redirect('/')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('new_page'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)