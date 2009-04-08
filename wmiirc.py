"""
wmiirc-python :: foolish attempt
"""

import subprocess
import time
import sys
import wmii
import logging
class Filter:
    def filter(self, rec): return False

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('py9').addFilter(Filter())
    print(logging.getLogger().filters)
    wmii.mainloop()

if __name__ == '__main__':
    main()
