# coding: utf-8

import re
import sys
import getopt
from pony.orm import db_session
from collipa import config


@db_session
def init_node():
    from collipa.models import Node
    if not Node.get(id=1):
        Node(name='根节点', urlname='root',
             description='一切的根源').save()

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "", ["install", "init"])
    except getopt.GetoptError:
        print("参数错误")
        sys.exit(2)

    for opt, val in opts:
        if opt == "--init":
            # create tables
            from collipa.models import db
            db.generate_mapping(create_tables=True)
            init_node()
            print("数据库表初始化成功")


if __name__ == "__main__":
    main(sys.argv[1:])
