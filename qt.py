import os

default_variant = 'PySide'

env_api = os.environ.get('QT_API', 'pyside')
if env_api == 'pyside':
    variant = 'PySide'
elif env_api == 'pyqt':
    variant = 'PyQt4'
else:
    variant = default_variant

if variant == 'PySide':
    try:
        from PySide import QtGui, QtCore
    except ImportError:
        # Fallback to PyQt4
        variant = 'PyQt4'

if variant == 'PyQt4':
    import sip
    api2_classes = [
        'QData', 'QDateTime', 'QString', 'QTextStream',
        'QTime', 'QUrl', 'QVariant',
    ]

    for cl in api2_classes:
        sip.setapi(cl, 2)

    from PyQt4 import QtGui, QtCore
    
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.QString = str
elif variant != 'PySide':
    raise ImportError("Python Variant not specified (%s)" % variant)

__all__ = [QtGui, QtCore, variant]
