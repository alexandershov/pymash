import sqlalchemy as sa
from sqlalchemy.ext import declarative

Base = declarative.declarative_base()


# TODO(aershov182): maybe use strings instead of integers for primary keys?
class _RepoAlchemyModel(Base):
    __tablename__ = 'repos'
    id = sa.Column(sa.Integer, sa.Sequence('repos_id_seq'), primary_key=True, nullable=False)
    url = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    rating = sa.Column(sa.Float, nullable=False)


Repos = _RepoAlchemyModel.__table__
