import aiopg.sa
import sqlalchemy

import typing as tp
from pymash import models
from pymash import parser

AsyncEngine = aiopg.sa.Engine
Engine = sqlalchemy.engine.base.Engine

Integers = tp.List[int]

Repos = tp.List[models.Repo]
Functions = tp.List[models.Function]

ParserFunctions = tp.List[parser.Function]
