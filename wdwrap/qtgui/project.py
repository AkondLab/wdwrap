#  Copyright (c) 2020. Mikolaj Kaluszynski et. al. CAMK, AkondLab
import typing

import PySide2
from PySide2.QtCore import QObject
from wdwrap.bundle import Bundle
from wdwrap.qtgui.bundle_model import BundleModel


class Project(QObject):

    def __init__(self, parent: typing.Optional[PySide2.QtCore.QObject] = None):
        super().__init__(parent)

        self.bundle = Bundle.default_binary()
        self.parameters_model = BundleModel(self.bundle)
        # self.curves_model = CurvesModel(self.bundle)

