#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""EkahauBOM - Bill of Materials generator for Ekahau AI projects.

This is the main entry point for the command-line interface.
"""

import sys
from ekahau_bom.cli import main

if __name__ == '__main__':
    sys.exit(main())