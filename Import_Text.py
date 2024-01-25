import os
import os.path

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsField, QgsFeature, QgsPointXY, QgsGeometry

from .Import_Text_dialog import TextWingisDialog
from .resources import *


def message(title, text):
    proj_msg = QMessageBox()
    proj_msg.setWindowTitle(title)
    proj_msg.setText(text)
    proj_msg.exec_()


class TextWingis:

    def __init__(self, iface):

        self.iface = iface
        self.instance = QgsProject.instance()
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TextWingis_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&Text From Wingis 2003')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('TextWingis', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        icon_path = ':/plugins/Import_Text/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import Text from WinGis'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Text From Wingis 2003'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_file(self):
        filename = QFileDialog.getOpenFileNames(self.dlg, 'Open file', '', '"Файл "MIF" (*.MIF)')[0]
        [self.dlg.textEdit.append(singlefile) for singlefile in filename]

    def import_integers(self):
        filename = self.dlg.textEdit.toPlainText().split('\n')
        self.dlg.textEdit.clear()
        for mif in filename:
            labels = QgsVectorLayer("Point?crs=", f"{mif.split('/')[len(mif.split('/')) - 1][:-4]}", "memory")
            labels.dataProvider().addAttributes([QgsField(f"Text", QVariant.String)]), labels.updateFields()
            labels.setCrs(self.instance.crs())
            with open(mif, "r", encoding='cp1251') as file:
                text = file.readlines()
                for index in [i + 1 for i, ltr in enumerate(text) if ltr == "Text\n"]:
                    if text[index] not in ['    "/"\n', '    "\\"\n']:
                        value = text[index].replace('"', '').replace('    ', '').replace('n\\', ' ')[:-1]
                        coord = text[index + 1].replace('    ', '')[:-1].split(' ')
                        feat = QgsFeature()
                        feat.setAttributes([value])
                        x = (float(coord[0]) + float(coord[2])) / 2
                        y = (float(coord[1]) + float(coord[3])) / 2
                        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                        labels.dataProvider().addFeatures([feat])
                QgsProject.instance().addMapLayer(labels)
                labels.loadNamedStyle(os.path.join(os.path.dirname(__file__), "Style.qml"))

    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = TextWingisDialog()
            self.dlg.pushButton.clicked.connect(self.select_file)
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            self.import_integers()
        else:
            self.dlg.textEdit.clear()
