import os
import sys
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import click
from flask import request
from flask import flash
from flask import redirect, url_for
from sqlalchemy import exc

app = Flask(__name__)

# 配置数据库连接信息
HOSTNAME = '127.0.0.1'
DATABASE = 'moviedb1'
PORT = 3306
USERNAME = 'root'
PASSWORD = '14285700'
DB_URL = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(USERNAME, PASSWORD, HOSTNAME, PORT, DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'  # 设置上传文件夹
app.config['ALLOWED_EXTENSIONS'] = {'html'}  # 允许上传的文件扩展名

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 创建数据库引擎
db = SQLAlchemy(app)

# 初始化数据库迁移
migrate = Migrate(app, db)

class Movie(db.Model):
    __tablename__ = 'movie_info'
    movie_id = db.Column(db.Integer, primary_key=True)
    movie_name = db.Column(db.String(20), nullable=False)
    release_date = db.Column(db.DateTime)
    country = db.Column(db.String(20))
    type = db.Column(db.String(10))
    year = db.Column(db.Integer)


class MoveBox(db.Model):
    __tablename__ = 'move_box'
    #id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(10), nullable=False, primary_key=True)
    box = db.Column(db.Float)

class ActorInfo(db.Model):
    __tablename__ = 'actor_info'
    actor_id = db.Column(db.Integer, primary_key=True)
    actor_name = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(2), nullable=False)
    country = db.Column(db.String(20))

class MovieActorRelation(db.Model):
    __tablename__ = 'movie_actor_relation'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie_info.movie_id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('actor_info.actor_id'), nullable=False)
    relation_type = db.Column(db.String(20))
    movie = db.relationship('Movie', backref='movie_relations')
    actor = db.relationship('ActorInfo', backref='actor_relations')

# 使用application context创建表
with app.app_context():
    # 初始化数据库
    db.create_all()


@app.cli.command()
@click.option('--drop', is_flag=True, help='Create after drop.')
def initdb(drop):
    """Initialize the database."""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/')
def index():
    return render_template('index.html')
    
from sqlalchemy.exc import IntegrityError

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        try:
            #movie_id = 1001+Movie.query.count()
            max_movie_id = db.session.query(func.max(Movie.movie_id)).scalar()
            movie_id = int(max_movie_id) + 1 if max_movie_id else 1
            movie_name = request.form.get('movie_name')
            year = request.form.get('year')
            release_date = request.form.get('release_date')
            country = request.form.get('country')
            type = request.form.get('type')
            box_office = request.form.get('box')

            # 验证输入
            if not movie_name or not year or len(year) != 4 or len(movie_name) > 60:
                flash('Invalid Input.')
            else:
                # 尝试将电影添加到数据库
                movie = Movie(movie_id=movie_id, movie_name=movie_name, year=year,
                            release_date=release_date, country=country, type=type)
                box = MoveBox(movie_id=movie_id, box=float(box_office))
                db.session.add(movie)
                db.session.add(box)
                db.session.commit()
                flash('Movie added successfully.')
        except IntegrityError as e:
            # 如果有完整性错误（例如，重复的ID），回滚并显示错误消息
            db.session.rollback()
            flash('Error when adding movie.')

    return render_template('add.html')


@app.route('/add_actor', methods=['GET', 'POST'])
def add_actor():
    if request.method == 'POST':
        try:
            #actor_id = 2001+ActorInfo.query.count()
            max_actor_id = db.session.query(func.max(ActorInfo.actor_id)).scalar()
            actor_id = int(max_actor_id) + 1 if max_actor_id else 1
            actor_name = request.form.get('actor_name')
            gender = request.form.get('gender')
            country = request.form.get('country')

            # 验证输入
            if not actor_name or  len(actor_name) > 60:
                flash('Invalid input.')
            else:
                # 尝试将演员添加到数据库
                actor = ActorInfo(actor_id=actor_id,actor_name=actor_name, gender=gender, country=country)
                db.session.add(actor)
                db.session.commit()
                flash('Actor added successfully.')
        except IntegrityError as e:
            # 如果有完整性错误，回滚并显示错误消息
            db.session.rollback()
            flash('Error when adding actor.')

    return render_template('add_actor.html')





from sqlalchemy import func
from sqlalchemy import case

@app.route('/list')
def list():
    movies = (
        db.session.query(
            Movie,
            func.coalesce(ActorInfo.actor_id, 0).label('actor_id'),
            func.coalesce(ActorInfo.actor_name, 'N/A').label('actor_name'),
            MovieActorRelation.relation_type,
            func.coalesce(MoveBox.box).label('box')
        )
        .outerjoin(MovieActorRelation, Movie.movie_id == MovieActorRelation.movie_id)
        .outerjoin(ActorInfo, ActorInfo.actor_id == MovieActorRelation.actor_id)
        .outerjoin(MoveBox, Movie.movie_id == MoveBox.movie_id)  # Join Movie with MoveBox
        .order_by(Movie.movie_id)
        .all()
    )
    return render_template('list.html', movies=movies, count=Movie.query.count())


@app.route('/actor_list')
def actor_list():
    actors = (
        db.session.query(
            ActorInfo,
            func.coalesce(Movie.movie_name, 'N/A').label('movie_name'),
            MovieActorRelation.relation_type
        )
        .outerjoin(MovieActorRelation, ActorInfo.actor_id == MovieActorRelation.actor_id)
        .outerjoin(Movie, Movie.movie_id == MovieActorRelation.movie_id)
        .order_by(ActorInfo.actor_id)
        .all()
        )
    return render_template('actor_list.html', actors=actors,count=ActorInfo.query.count())


@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    move_box = MoveBox.query.get(movie_id)

    if request.method == 'POST':
        movie.movie_name = request.form['movie_name']
        movie.year = request.form['year']
        movie.release_date = request.form['release_date']
        movie.country = request.form['country']
        movie.type = request.form['type']

        if not movie.movie_name or not movie.year or len(movie.year) != 4 or len(movie.movie_name) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))

        # Update the corresponding entry in move_box
        try:
            db.session.commit()

            # Update the corresponding entry in move_box
            move_box = MoveBox.query.get(movie_id)
            if move_box:
                move_box.box = float(request.form['box'])
                db.session.commit()

            flash('Movie and associated box office record updated successfully.')
        except IntegrityError:
            # Handle potential integrity error (rollback)
            db.session.rollback()
            flash('Error updating movie. Please try again.')

        return redirect(url_for('list'))

    return render_template('edit.html', movie=movie)

@app.route('/movie/add_actor_relation/<int:movie_id>', methods=['GET', 'POST'])
def add_actor_relation(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        # Get form data
        actor_name = request.form.get('actor_name')
        relation_type = request.form.get('relation_type')

        # Query ActorInfo to find actor_id
        actor_info = ActorInfo.query.filter_by(actor_name=actor_name).first()

        if not actor_info:
            flash('Actor invalid')
            return redirect(url_for('add_actor_relation', movie_id=movie_id))

        new_relation_id = 1 + MovieActorRelation.query.count()
        #max_relation_id = db.session.query(func.max(MovieActorRelation.id)).scalar()
        #new_relation_id = int(max_relation_id) + 1 if max_relation_id else 1
        # Create new movie_actor_relation entry
        new_relation = MovieActorRelation(
            id=new_relation_id,
            movie_id=movie_id,
            actor_id=actor_info.actor_id,
            relation_type=relation_type
        )

        # Try to insert the new relation into the database
        try:
            db.session.add(new_relation)
            db.session.commit()
            flash('Movie-Actor relation added successfully.')
        except IntegrityError as e:
            # Handle potential integrity error (rollback)
            db.session.rollback()
            flash('Error adding Movie-Actor relation. Please try again.')

        return redirect(url_for('list'))

    return render_template('add_actor_relation.html', movie=movie)


from flask import render_template, flash, redirect, url_for

@app.route('/actor/edit/<string:actor_id>', methods=['GET', 'POST'])
def edit_actor(actor_id):
    actor = ActorInfo.query.get_or_404(actor_id)

    if request.method == 'POST':
        actor.actor_name = request.form['actor_name']
        actor.gender = request.form['gender']
        actor.country = request.form['country']

        if not actor.actor_name or len(actor.actor_name) > 20:
            flash('Invalid input.')
            return redirect(url_for('edit_actor', actor_id=actor_id))

        db.session.commit()
        flash('Actor updated successfully.')
        return redirect(url_for('actor_list'))

    return render_template('edit_actor.html', actor=actor)



@app.route('/movie/delete/<int:movie_id>', methods=['POST'])
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    relations = MovieActorRelation.query.filter_by(movie_id=movie_id).all()
    box = MoveBox.query.filter_by(movie_id=movie_id).first()
    for relation in relations:
        db.session.delete(relation)
    if box:
        db.session.delete(box)
    db.session.delete(movie)
    db.session.commit()
    flash('Movie deleted successfully.')
    return redirect(url_for('list'))

@app.route('/actor/delete/<string:actor_id>', methods=['POST'])
def delete_actor(actor_id):
    actor = ActorInfo.query.get_or_404(actor_id)
    relations = MovieActorRelation.query.filter_by(actor_id=actor_id).all()
    for relation in relations:
        db.session.delete(relation)
    db.session.delete(actor)
    db.session.commit()
    flash('Actor deleted successfully.')
    return redirect(url_for('actor_list'))


from urllib.parse import unquote

@app.route('/movie/delete_actor_relation/<int:movie_id>/<int:actor_id>/<string:relation_type>', methods=['POST'])
def delete_actor_relation(movie_id, actor_id, relation_type):
    # Convert movie_id and actor_id to integers
    movie_id = int(movie_id)
    actor_id = int(actor_id)
    relation_type = unquote(relation_type)

    # Query and delete the corresponding entry in movie_actor_relation
    relation = MovieActorRelation.query.filter_by(movie_id=movie_id, actor_id=actor_id, relation_type=relation_type).first()

    if relation:
        db.session.delete(relation)
        db.session.commit()
        flash('Actor relation deleted successfully.')
    else:
        flash('Actor relation not found.')

    return redirect(url_for('list'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # 获取用户输入的电影名称
        search_input = request.form.get('movie_name')

        # 查询数据库，获取匹配的电影信息
        movies = (
        db.session.query(
            Movie,
            func.coalesce(ActorInfo.actor_id, 0).label('actor_id'),
            func.coalesce(ActorInfo.actor_name, 'N/A').label('actor_name'),
            MovieActorRelation.relation_type,
            func.coalesce(MoveBox.box).label('box')
        )
        .outerjoin(MovieActorRelation, Movie.movie_id == MovieActorRelation.movie_id)
        .outerjoin(ActorInfo, ActorInfo.actor_id == MovieActorRelation.actor_id)
        .outerjoin(MoveBox, Movie.movie_id == MoveBox.movie_id)  # Join Movie with MoveBox
        .filter(Movie.movie_name.ilike(f'%{search_input}%'))  # 过滤电影名称
        .order_by(Movie.movie_id)
        .all()
    )
        
        return render_template('search_results.html', movies=movies, search_input=search_input)

    return render_template('search.html')




@app.route('/search_actor', methods=['GET', 'POST'])
def search_actor():
    if request.method == 'POST':
        # 获取用户输入的电影名称
        search_input = request.form.get('actor_name')

        # 查询数据库，获取匹配的电影信息
        
        actors = (
        db.session.query(
            ActorInfo,
            func.coalesce(Movie.movie_name, 'N/A').label('movie_name'),
            MovieActorRelation.relation_type
        )
        .outerjoin(MovieActorRelation, ActorInfo.actor_id == MovieActorRelation.actor_id)
        .outerjoin(Movie, Movie.movie_id == MovieActorRelation.movie_id)
        .filter(ActorInfo.actor_name.ilike(f'%{search_input}%'))
        .order_by(ActorInfo.actor_id)
        .all()
        )
        
        
        return render_template('search_actor_results.html', actors=actors, search_input=search_input)

    return render_template('search_actor.html')


@app.route('/upload')
def upload_file():
    file_content = None

    # Try to read the content of the first HTML file in the 'uploads' folder
    file_list = os.listdir(app.config['UPLOAD_FOLDER'])
    if file_list:
        first_html_file = next((file for file in file_list if file.endswith('.html')), None)
        if first_html_file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], first_html_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

    return render_template('upload.html', file_content=file_content)


if __name__ == '__main__':
    app.run(debug=True)
