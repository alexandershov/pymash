import sqlalchemy as sa
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


class Repo(Base):
    __tablename__ = 'repos'
    id = sa.Column(sa.Integer, sa.Sequence('repos_id_seq'), primary_key=True, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    rating = sa.Column(sa.Float, nullable=False)


# TODO(aershov182): get rid of sa_ prefix?
sa_repos = Repo.__table__
