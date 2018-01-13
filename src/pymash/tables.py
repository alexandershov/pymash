import sqlalchemy as sa
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


class _RepoDbModel(Base):
    __tablename__ = 'repos'
    repo_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    github_id = sa.Column(sa.BigInteger, unique=True, index=True, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False)
    rating = sa.Column(sa.Float, nullable=False, index=True)


Repos = _RepoDbModel.__table__


class _FunctionDbModel(Base):
    __tablename__ = 'functions'
    function_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    repo_id = sa.Column(sa.ForeignKey(Repos.c.repo_id), nullable=False)
    text = sa.Column(sa.Text, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False)
    random = sa.Column(sa.Float, server_default=sa.func.random(), nullable=False, index=True)


Functions = _FunctionDbModel.__table__

repo_id_md5_text_unique_idx = sa.Index(
    'functions_repo_id_md5_text_unique_idx',
    Functions.c.repo_id, sa.func.md5(Functions.c.text),
    unique=True)

sa.Index(
    'functions_is_active_random_partial_idx',
    Functions.c.is_active, Functions.c.random,
    postgresql_where=Functions.c.is_active.is_(True))


class _GameDbModel(Base):
    __tablename__ = 'games'
    game_id = sa.Column(sa.Text, primary_key=True, nullable=False)
    white_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    black_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    white_score = sa.Column(sa.Integer, nullable=False)
    black_score = sa.Column(sa.Integer, nullable=False)


Games = _GameDbModel.__table__

__all__ = ['Repos', 'Functions', 'Games']
