import sys


# ugly, hacky fix
def uhf(n):
    if n[:4] == 'lib.':
        globals()[n[4:]] = sys.modules[n]
