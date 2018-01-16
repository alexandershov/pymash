import typing as tp

import aiopg.sa
import github.Repository
import sqlalchemy
from aiohttp import web

from pymash import models
from pymash import parser

AsyncEngine = aiopg.sa.Engine
Engine = sqlalchemy.engine.base.Engine

Integers = tp.List[int]
SetOfStrings = tp.Set[str]

Repos = tp.List[models.Repo]
Functions = tp.List[models.Function]

Repository = github.Repository.Repository

GithubRepos = tp.List[models.GithubRepo]
ParserFunctions = tp.List[parser.Function]

DictOrResponse = tp.Union[dict, web.Response]
