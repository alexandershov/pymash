import sqlalchemy as sa
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


class _RepoDbModel(Base):
    __tablename__ = 'repos'
    repo_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    rating = sa.Column(sa.Float, nullable=False, index=True)


Repos = _RepoDbModel.__table__


class _FunctionDbModel(Base):
    __tablename__ = 'functions'
    function_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    repo_id = sa.Column(sa.ForeignKey(Repos.c.repo_id), nullable=False)
    text = sa.Column(sa.Text, nullable=False)
    random = sa.Column(sa.Float, server_default=sa.func.random(), index=True, nullable=False)


Functions = _FunctionDbModel.__table__

__all__ = ['Repos', 'Functions']
