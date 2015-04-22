try:
    # Set PySide compatible APIs
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit

    from PyQt4.QtCore import pyqtProperty
    from PyQt4.QtCore import pyqtSignal
    from PyQt4.QtCore import pyqtSlot

    QtCore.Property = pyqtProperty
    QtCore.Signal = pyqtSignal
    QtCore.Slot = pyqtSlot

except ImportError:
    from PySide import QtCore, QtGui, QtNetwork, QtWebKit
