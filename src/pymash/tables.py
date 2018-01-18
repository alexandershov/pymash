import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import event

__all__ = ['Repos', 'Functions', 'Games']

# noinspection SqlNoDataSourceInspection
_TRIGGER_TEMPLATE = (
    '''CREATE FUNCTION set_updated_{table_name}()                                                                          
       RETURNS TRIGGER AS $$
       BEGIN
         NEW.updated = current_timestamp;
         return NEW;
       END $$ LANGUAGE 'plpgsql';
    '''
    'CREATE TRIGGER set_updated BEFORE INSERT OR UPDATE ON {table_name} '
    'FOR EACH ROW EXECUTE PROCEDURE set_updated_{table_name}()')


def get_index_by_name(table, name):
    for index in table.indexes:
        if index.name == name:
            return index
    raise ValueError(f'unknown index {name}')


def _get_table_with_trigger(model):
    table = model.__table__
    trigger = sa.DDL(_TRIGGER_TEMPLATE.format(table_name=model.__tablename__))
    event.listen(table, 'after_create', trigger)
    return table


Base = declarative.declarative_base()


class _CreatedUpdatedMixin:
    created = sa.Column(
        sa.DateTime(timezone=True),
        server_default=sa.func.current_timestamp(),
        nullable=False)
    updated = sa.Column(sa.DateTime(timezone=True), nullable=False)


class _RepoDbModel(_CreatedUpdatedMixin, Base):
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


# noinspection PyTypeChecker
Repos = _get_table_with_trigger(_RepoDbModel)


class _FunctionDbModel(_CreatedUpdatedMixin, Base):
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
        sa.Index(
            'functions_repo_id_md5_text_unique_idx',
            repo_id, sa.func.md5(text),
            unique=True)
    )


# noinspection PyTypeChecker
Functions = _get_table_with_trigger(_FunctionDbModel)


class _GameDbModel(_CreatedUpdatedMixin, Base):
    __tablename__ = 'games'
    game_id = sa.Column(sa.Text, primary_key=True, nullable=False)
    white_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    black_id = sa.Column(sa.ForeignKey(Functions.c.function_id), nullable=False)
    white_score = sa.Column(sa.Integer, nullable=False)
    black_score = sa.Column(sa.Integer, nullable=False)


# noinspection PyTypeChecker
Games = _get_table_with_trigger(_GameDbModel)
