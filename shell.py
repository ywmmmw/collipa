# coding: utf-8

import sys
import importlib

from pony import orm
from IPython import embed
from collipa.models import db


@orm.db_session
def runshell():
    embed()

if __name__ == '__main__':
    db.generate_mapping()
    runshell()
