import sqlalchemy as sa
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


# TODO(aershov182): maybe use strings instead of integers for primary keys?
class _RepoDbModel(Base):
    __tablename__ = 'repos'
    id = sa.Column(sa.Integer, sa.Sequence('repos_id_seq'), primary_key=True, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    rating = sa.Column(sa.Float, nullable=False)


Repos = _RepoDbModel.__table__


class _FunctionDbModel(Base):
    __tablename__ = 'functions'
    id = sa.Column(sa.Integer, sa.Sequence('functions_id_seq'), primary_key=True, nullable=False)
    repo_id = sa.Column(sa.ForeignKey(Repos.c.id), nullable=False)
    text = sa.Column(sa.Text, nullable=False)
    rnd = sa.Column(sa.Float, default=sa.func.random(), nullable=False)


Functions = _FunctionDbModel.__table__
