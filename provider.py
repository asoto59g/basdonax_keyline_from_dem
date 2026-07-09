from qgis.core import QgsProcessingProvider
from .algorithm_keyline_from_dem import KeylineFromDemAlgorithm


class BasdonaxKeylineProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(KeylineFromDemAlgorithm())

    def id(self):
        return "basdonax_keyline"

    def name(self):
        return "Basdonax Keyline"

    def longName(self):
        return self.name()