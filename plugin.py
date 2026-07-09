from qgis.core import QgsApplication
from .provider import BasdonaxKeylineProvider


class BasdonaxKeylinePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        self.provider = BasdonaxKeylineProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None