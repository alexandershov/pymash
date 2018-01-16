import sqlalchemy as sa
from sqlalchemy.ext import declarative

__all__ = ['Repos', 'Functions', 'Games']

Base = declarative.declarative_base()


# TODO: add created/updated attributes to all tables
class _RepoDbModel(Base):
    __tablename__ = 'repos'
    repo_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    github_id = sa.Column(sa.BigInteger, unique=True, index=True, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False)
    rating = sa.Column(sa.Float, nullable=False)

    __table_args__ = (
        sa.Index(
            'repos_is_active_rating_partial_idx',
            rating,
            postgresql_where=is_active.is_(True)),
    )


Repos = _RepoDbModel.__table__


class _FunctionDbModel(Base):
    __tablename__ = 'functions'
    function_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    repo_id = sa.Column(sa.ForeignKey(Repos.c.repo_id), nullable=False, index=True)
    text = sa.Column(sa.Text, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False)
    random = sa.Column(sa.Float, server_default=sa.func.random(), nullable=False, index=True)

    __table_args__ = (
        sa.Index(
            'functions_is_active_random_partial_idx',
            random,
            postgresql_where=is_active.is_(True)),
    )


Functions = _FunctionDbModel.__table__

repo_id_md5_text_unique_idx = sa.Index(
    'functions_repo_id_md5_text_unique_idx',
    Functions.c.repo_id, sa.func.md5(Functions.c.text),
    unique=True)


class _GameDbModel(Base):
    __tablename__ = 'games'
    game_id = sa.Column(sa.Text, primary_key=True, nullable=False)
    white_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    black_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    white_score = sa.Column(sa.Integer, nullable=False)
    black_score = sa.Column(sa.Integer, nullable=False)


Games = _GameDbModel.__table__
