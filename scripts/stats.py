#!/usr/bin/env python3

# Copyright 2017-2019, The Johns Hopkins University Applied Physics Laboratory LLC
# All rights reserved.
# Distributed under the terms of the Apache 2.0 License.

#
# Usage: python3 scripts/stats.py [annotations directory]
#
# Use -v to get a count over mentions
#

import argparse
import os
import sys

# don't assume the user has install dragonfly
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import dragonfly.stats

MIN_PYTHON = (3, 0)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python {}.{} or later is required.\n".format(*MIN_PYTHON))

parser = argparse.ArgumentParser()
parser.add_argument("input", help="directory with .anno files")
parser.add_argument("-v", "--verbose", help="verbose output", action='store_true', default=False)
args = parser.parse_args()

if not os.path.exists(args.input):
    sys.exit(f"Error: {args.input} does not exist")

stats = dragonfly.stats.Stats()
stats.collect(args.input)

print(f"{stats.num_files} Documents")
print(f"{stats.num_tokens} Tokens")
print(f"{stats.num_tagged_tokens} Tagged Tokens")
print(f"{stats.num_entities} Entity Tags")
print(f"{stats.num_unique_entities} Unique Entity Tags")
for s in stats.entities.values():
    print(f"{s.type}: {s.num_entities} Entities")
    print(f"{s.type}: {len(s.entities)} Unique Entities")
if args.verbose:
    print("---------------------------------")
    for s in stats.entities.values():
        print()
        print(s.type)
        print("-------------------")
        for name, count in s.entities.most_common(len(s.entities)):
            print(f"{name}\t{count}")
