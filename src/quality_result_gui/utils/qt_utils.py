from qgis.PyQt.QtCore import QT_VERSION, QVariant

"""
Unfortunately https://github.com/qgis/QGIS/blob/master/scripts/pyqt5_to_pyqt6/pyqt5_to_pyqt6.py
tries to replace all QVariant() with NULL (QVariant(int)),
which breaks some functionality with models.

This workaround is here to provide working solution for now.
"""
# TODO: remove after QGIS>4 and just use None or `from qgis.core import NULL` instead
NULL = None if QT_VERSION >= 0x060000 else QVariant()  # noqa: PLR2004
