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
DATABASE = 'moviedb'
PORT = 3306
USERNAME = 'root'
PASSWORD = '14285700'
DB_URL = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(USERNAME, PASSWORD, HOSTNAME, PORT, DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'

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
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(10), nullable=False, unique=True)
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
    actor_id = db.Column(db.String(10), db.ForeignKey('actor_info.actor_id'), nullable=False)
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
            movie_id = 1001+Movie.query.count()
            movie_name = request.form.get('movie_name')
            year = request.form.get('year')
            release_date = request.form.get('release_date')
            country = request.form.get('country')
            type = request.form.get('type')

            # 验证输入
            if not movie_name or not year or len(year) != 4 or len(movie_name) > 60:
                flash('无效输入.')
            else:
                # 尝试将电影添加到数据库
                movie = Movie(movie_id=movie_id, movie_name=movie_name, year=year,
                            release_date=release_date, country=country, type=type)
                db.session.add(movie)
                db.session.commit()
                flash('电影添加成功.')
        except IntegrityError as e:
            # 如果有完整性错误（例如，重复的ID），回滚并显示错误消息
            db.session.rollback()
            flash('添加电影时出错。请确保ID是唯一的.')

    return render_template('add.html')






from sqlalchemy import func
from sqlalchemy import case

@app.route('/list')
def list():
    movies = (
        db.session.query(
            Movie,
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

    if request.method == 'POST':
        movie.movie_name = request.form['movie_name']
        movie.year = request.form['year']
        movie.release_date = request.form['release_date']
        movie.country = request.form['country']
        movie.type = request.form['type']

        if not movie.movie_name or not movie.year or len(movie.year) != 4 or len(movie.movie_name) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))

        db.session.commit()
        flash('Movie updated successfully.')
        return redirect(url_for('list'))

    return render_template('edit.html', movie=movie)

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
    db.session.delete(movie)
    db.session.commit()
    flash('Movie deleted successfully.')
    return redirect(url_for('list'))

@app.route('/actor/delete/<string:actor_id>', methods=['POST'])
def delete_actor(actor_id):
    actor = ActorInfo.query.get_or_404(actor_id)
    db.session.delete(actor)
    db.session.commit()
    flash('Actor deleted successfully.')
    return redirect(url_for('actor_list'))




@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # 获取用户输入的电影名称
        search_input = request.form.get('movie_name')

        # 查询数据库，获取匹配的电影信息
        movies = (
        db.session.query(
            Movie,
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




if __name__ == '__main__':
    app.run(debug=True)
