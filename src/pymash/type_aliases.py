import aiopg.sa
import sqlalchemy

import typing as tp
from pymash import models
from pymash import parser

AsyncEngine = aiopg.sa.Engine
Engine = sqlalchemy.engine.base.Engine

Integers = tp.List[int]
SetOfStrings = tp.Set[str]

Repos = tp.List[models.Repo]
Functions = tp.List[models.Function]

GithubRepos = tp.List[models.GithubRepo]
ParserFunctions = tp.List[parser.Function]
