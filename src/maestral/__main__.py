# -*- coding: utf-8 -*-

import sys

from .cli import main

if __name__ == "__main__":
    sys.argv[0] = "maestral"
    main()
