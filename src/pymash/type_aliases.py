import aiopg.sa
import sqlalchemy

import typing as tp
from pymash import models

AsyncEngine = aiopg.sa.Engine
Engine = sqlalchemy.engine.base.Engine

Integers = tp.List[int]

Repos = tp.List[models.Repo]
Functions = tp.List[models.Function]
