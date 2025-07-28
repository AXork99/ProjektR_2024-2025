#!/usr/bin/env python3 

from src import *
import sys

metis = graphs.MetisFormat()

path = "data/parsed/zupanija_"

G = metis.read(path + sys.argv[1]).embed().flush()
metis.write(G)