import os
import os.path

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .resources import *
from .Import_Text_dialog import TextWingisDialog


class TextWingis:

    def __init__(self, iface):

        self.iface = iface
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
            # Adds plugin icon to Plugins toolbar
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

        # will be set False in run()
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Text From Wingis 2003'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_file(self):
        filename = QFileDialog.getOpenFileNames(self.dlg, 'Open file', '', '"Файл "MIF" (*.MIF *.MID)')[0]
        for singlefile in filename:
            self.dlg.textEdit.append(singlefile)

    def run(self):

        if self.first_start == True:
            self.first_start = False
            self.dlg = TextWingisDialog()
            self.dlg.pushButton.clicked.connect(self.select_file)

        self.dlg.show()

        result = self.dlg.exec_()

        if result:
            filename = self.dlg.textEdit.toPlainText()
            self.dlg.textEdit.clear()
            spisok = filename.split('\n')
            for fi in spisok:
                with open(fi, "r", encoding='cp1251') as file:
                    text = file.readlines()
                    for wrong in text:
                        if 'Region ' in wrong:
                            proj_msg = QMessageBox()
                            proj_msg.setWindowTitle("Warning")
                            proj_msg.setText(
                                "Слой содержит не корректную геометрию (линии, полигоны)!\n"
                                "Слой должен содержать только подписи (точки), исправьте геометрию.")
                            proj_msg.exec_()
                            break
                        elif 'Pline ' in wrong:
                            proj_msg = QMessageBox()
                            proj_msg.setWindowTitle("Warning")
                            proj_msg.setText(
                                "Слой содержит не корректную геометрию (линии, полигоны)!\n"
                                "Слой должен содержать только подписи (точки), исправьте геометрию.")
                            proj_msg.exec_()
                            break
                    text.pop(1)
                    # Замена набора символов
                    text.insert(1, 'Charset "WindowsCyrillic"\n')
                    # Находим индекс сингнального слова "Text" и добавляем их в список
                    x = [i for i, ltr in enumerate(text) if ltr == "Text\n"]
                    # print(x)
                    # Увеличиваем значение индекса на 1, таким образом мы получим уже индекс самих надписей
                    # Создадим список значений
                    lst_label = []
                    for ind in x:
                        trind = ind + 1
                        label = text[trind]
                        # Уберём лишние знаки
                        lst_label.append(label[4:])
                        # print(label[4:-1])
                    # print(lst_label)
                # запись полученых значений
                with open(fi[:-4] + ".MID", 'w', encoding='cp1251') as f:
                    f.writelines(lst_label)
                # Смена кодировки
                with open(fi, "w", encoding='cp1251') as file:
                    file.writelines(text)
                path_to_airports_layer = fi
                layername = fi.rpartition('/')[2]
                layername = layername[:-4]
                vlayer = QgsVectorLayer(path_to_airports_layer, layername, "ogr",
                                        crs=QgsProject.instance().crs())
                if not vlayer.isValid():
                    print("Layer failed to load!")
                else:
                    # Открытие слоя
                    QgsProject.instance().addMapLayer(vlayer)
                    save_options = QgsVectorFileWriter.SaveVectorOptions()
                    # Добавление стиля для подписей
                    style_path = os.path.join(os.path.dirname(__file__), "Style.qml")
                    (errorMsg, result) = vlayer.loadNamedStyle(style_path)
        else:
            self.dlg.textEdit.clear()
