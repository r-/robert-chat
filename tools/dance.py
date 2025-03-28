#!/usr/bin/env python3

import sys

# Simple dance tool that echoes out "Tool_use: Dancing"
print("Tool_use: Dancing")

# If arguments are provided, print them too
if len(sys.argv) > 1:
    print(f"Arguments: {' '.join(sys.argv[1:])}")
