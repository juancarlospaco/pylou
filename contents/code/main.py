# -*- coding: utf-8 -*-


# This is a Fork of Kulo, trying to make it looks like Milou, without Baloo.


#   Copyright 2009, 2010 Francesco Ricci <frankyricci@gmail.com>
#   Copyleft  2010, 2015 Juan Carlos     <juancarlospaco@gmail.com>
#
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU Library General Public License as
#   published by the Free Software Foundation; either version 2 or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#
#   GNU General Public License for more details
#
#
#   You should have received a copy of the GNU Library General Public
#   License along with this program; if not, write to the
#   Free Software Foundation, Inc.,


""" Pylou """


from datetime import datetime
from os import listdir, path
from re import purge, search
from subprocess import call, PIPE, Popen
from tempfile import mkstemp

from PyKDE4.kdecore import KConfig
from PyKDE4.kdeui import (KColorButton, KDialog, KFontRequester, KLineEdit,
                          KPushButton, KTextEdit, KTitleWidget)
from PyKDE4.plasma import Plasma
from PyKDE4.plasmascript import Applet
from PyQt4.QtCore import pyqtSignature, QEvent, QStringList, QVariant, SIGNAL
from PyQt4.QtGui import (QCheckBox, QColor, QCompleter, QFont,
                         QGraphicsLinearLayout, QGraphicsWidget, QGridLayout,
                         QIcon, QLabel, QMessageBox, QStringListModel)


HISTORY_FILE_PATH = mkstemp()[1]
DISABLE_BALOO_CMD = ("kwriteconfig --file baloofilerc --group 'Basic Settings' "
                     "--key 'Indexing-Enabled' {}")


def delete_my_history():
    """Delete the HISTORY_FILE_PATH file contents."""
    with open(HISTORY_FILE_PATH, "w") as my_history_file:
        my_history_file.write("\n")  # Fully Empty the file
        QMessageBox.information(None, __doc__, "<b>History File Deleted !")


class PylouWidget(QGraphicsWidget):
    def __init__(self, parent):
        QGraphicsWidget.__init__(self)
        self.applet = parent

    def init(self):
        """Start Pylou Widget."""
        self.layou, self.stringlist = QGraphicsLinearLayout(self), QStringList()
        self.model = QStringListModel(self.applet)
        self.model.setStringList(self.stringlist)
        self.treeview = MyTreeView(self)
        self.treeview.setModel(self.model)
        self.lineEdit, self.label = MyLineEdit(self), Plasma.Label(self)
        self.label.setText("Search")
        self.layou.setOrientation(0x2)  # Qt.Vertical
        self.layou.addItem(self.treeview)
        self.layou.addItem(self.label)
        self.layou.addItem(self.lineEdit)
        self.setLayout(self.layou)
        self.lineEdit.returnPressed.connect(self.addItem)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(666, 666)
        self.resize(self.minimumSize())
        # custom user choosed fonts
        user_font_family = QVariant(
            self.applet.configurations.readEntry("TextFont", QVariant(QFont())))
        self.treeview.nativeWidget().setFont(QFont(user_font_family))
        # custom user choosed styles
        user_style_sheet = "color:{};alternate-background-color:{}".format(
            self.applet.configurations.readEntry("TextColor"),
            self.applet.configurations.readEntry("AlternateBColor"))
        self.treeview.nativeWidget().setStyleSheet(user_style_sheet)
        # Qt connecting people
        Applet.connect(
            self.lineEdit, SIGNAL("keyUPPressed"), self.prevHistoryItem)
        Applet.connect(
            self.lineEdit, SIGNAL("keyDownPressed"), self.nextHistoryItem)
        Applet.connect(self.treeview, SIGNAL("DblClick"), self.openFile)
        Applet.connect(self.treeview, SIGNAL("Click"), self.openDirectory)
        self.applet.appletDestroyed.connect(self.saveHistory)
        # History file
        self.histfile = HISTORY_FILE_PATH
        with open(self.histfile, 'r') as history_file:
            self.history = history_file.readlines()
        self.historyCurrentItem = 0

    def saveHistory(self):
        """Write History to History file."""
        with open(self.histfile, 'w') as history_file:
            history_file.writelines(self.history)

    def prevHistoryItem(self):
        """Navigate the History 1 Item Backwards."""
        if self.historyCurrentItem < len(self.history):
            self.historyCurrentItem = self.historyCurrentItem + 1
        try:
            self.lineEdit.setText(str(self.history[-self.historyCurrentItem]))
        except IndexError as error:
            print(error)
            self.label.setText("ERROR: History Empty.")

    def nextHistoryItem(self):
        """Navigate the History 1 Item Forwards."""
        if self.historyCurrentItem > 1:
            self.historyCurrentItem = self.historyCurrentItem - 1
        try:
            self.lineEdit.setText(str(self.history[-self.historyCurrentItem]))
        except IndexError as error:
            print(error)
            self.label.setText("ERROR: History Empty.")

    def addItem(self):
        """Add Items from Locate command."""
        start_time = datetime.now().second
        self.stringlist.clear()
        lineText = self.lineEdit.text()
        if len(lineText) and str(lineText).strip() not in self.history:
            self.history.append(lineText + "\n")
            self.historyCurrentItem = 1
            self.saveHistory()
        self.historyCurrentItem = self.historyCurrentItem - 1
        comand = "chrt -i 0 /usr/bin/locate --ignore-case --existing --quiet {}"
        command_to_run = comand.format(lineText)
        locate_output = Popen(command_to_run, shell=True, stdout=PIPE).stdout
        results = tuple(locate_output.readlines())
        banned = self.applet.configurations.readEntry("Banned")
        bannedword_regex_pattern = str(banned).strip().lower().replace(" ", "|")
        for item in results:
            if not search(bannedword_regex_pattern, str(item)):  # banned words
                self.stringlist.append(item[:-1])
        purge()  # Purge RegEX Cache
        self.model.setStringList(self.stringlist)
        self.treeview.nativeWidget().resizeColumnToContents(0)
        number_of_results = len(results)
        if number_of_results:  # if tems found Focus on item list
            self.lineEdit.nativeWidget().clear()
            self.label.setText("Found {} results on {} seconds !".format(
                number_of_results, abs(datetime.now().second - start_time)))
            self.resize(500, 12 * number_of_results)
            self.treeview.nativeWidget().setFocus()
        else:  # if no items found Focus on LineEdit
            self.label.setText("Search")
            self.resize(self.minimumSize())
            self.lineEdit.nativeWidget().setFocus()

    def openDirectory(self, index):
        """Take a model index and find the folder name then open the folder."""
        item_to_open = path.dirname(str(self.model.data(index, 0).toString()))
        Popen("xdg-open '{}'".format(item_to_open), shell=True)

    def openFile(self, index):
        """Take a model index and find the filename then open the file."""
        item_to_open = self.model.data(index, 0).toString()
        Popen("xdg-open '{}'".format(item_to_open), shell=True)


class MyLineEdit(Plasma.LineEdit):
    def __init__(self, *args):
        Plasma.LineEdit.__init__(self, *args)
        self.nativeWidget().setClearButtonShown(True)
        self.nativeWidget().setPlaceholderText("Type to Search...")
        self.nativeWidget().setToolTip("""<p>Type and press ENTER: to Search<br>
        UP-DOWN: History navigation<br>Search Empty Query: Clear out""")
        self.completer = QCompleter(tuple(sorted(set(
            [_ for _ in listdir(path.expanduser("~")) if not _.startswith(".")]
        ))), self.nativeWidget())
        self.completer.setCompletionMode(QCompleter.InlineCompletion)
        self.completer.setCaseSensitivity(0)  # Qt.CaseInsensitive
        self.nativeWidget().setCompleter(self.completer)

    def event(self, event):
        """Override to enable History Navigation."""
        # Qt.Key_Up
        if event.type() == QEvent.KeyPress and event.key() == 0x01000013:
            self.emit(SIGNAL("keyUPPressed"))
            return True
        # Qt.Key_Down
        if event.type() == QEvent.KeyPress and event.key() == 0x01000015:
            self.emit(SIGNAL("keyDownPressed"))
            return True
        return Plasma.LineEdit.event(self, event)


class MyTreeView(Plasma.TreeView):
    def __init__(self, *args):
        Plasma.TreeView.__init__(self, *args)
        self.nativeWidget().header().hide()
        self.nativeWidget().setAnimated(True)
        self.nativeWidget().setUniformRowHeights(True)
        self.nativeWidget().setAlternatingRowColors(True)

    def mouseDoubleClickEvent(self, event):
        """Method to handle the double click mouse event."""
        if event.button() == 1:
            index = self.nativeWidget().indexAt(event.pos().toPoint())
            self.emit(SIGNAL("DblClick"), index)

    def mouseReleaseEvent(self, event):
        """Method to handle the release mouse event."""
        if event.button() == 4:
            index = self.nativeWidget().indexAt(event.pos().toPoint())
            self.emit(SIGNAL("Click"), index)


class PylouApplet(Applet):
    def __init__(self, parent, args=None):
        Applet.__init__(self, parent)

    def init(self):
        """Start the Applet."""
        self._widget = None
        self.setHasConfigurationInterface(True)
        self.setAspectRatioMode(Plasma.IgnoreAspectRatio)
        self.configurations = self.config()
        self._widget = PylouWidget(self)
        self._widget.init()
        self.setGraphicsWidget(self._widget)
        self.applet.setPassivePopup(True)
        self.setPopupIcon(QIcon.fromTheme("edit-find"))
        # for some odd reason this has to be called twice?
        self.setGraphicsWidget(self._widget)
        self.prepareConfigDialog()

    def prepareConfigDialog(self):
        """Prepare the Configuration Dialog."""
        self.bcolor, self.dialog = QColor(), KDialog()
        self.dialog.setWindowTitle(__doc__ + "Settings")
        self.layBox = QGridLayout(self.dialog.mainWidget())
        self.title = KTitleWidget(self.dialog)
        self.title.setText(__doc__ + " !")
        self.title.setAutoHideTimeout(3000)
        self.FontButton = KFontRequester(self.dialog)
        self.tfont = QFont(QVariant(self.configurations.readEntry("TextFont",
                           QVariant(QFont()))))
        self.FontButton.setFont(self.tfont)
        self.ColorButton = KColorButton(self.dialog)
        self.tcolor = QColor(self.configurations.readEntry("TextColor",
                             QColor("#000").name()))
        self.ColorButton.setColor(self.tcolor)
        self.BColorButton = KColorButton(self.dialog)
        # button to update the DB via sudo updatedb
        clk = lambda: call("kdesudo --noignorebutton -c updatedb", shell=True)
        self.UpdateDB = KPushButton("Update Database", self.dialog, clicked=clk)
        self.UpdateDB.setToolTip("Database is Updated every Reboot and Daily !")
        self.Histor = KPushButton("Delete my History", self.dialog,
                                  clicked=delete_my_history)
        self.Histor.setToolTip("History is Deleted every Reboot !")
        # list of banned words separated by spaces
        self.banned = KTextEdit(self.dialog)
        self.banned.setPlainText(self.configurations.readEntry(
            "Banned", "sex porn drugs suicide decapitated religion").toString())
        # set the colors
        cg = KConfig("kdeglobals")
        color = cg.group("Colors:View").readEntry(
            "BackgroundAlternate").split(",")
        self.bcolor = QColor(int(color[0]), int(color[1]), int(color[2]))
        self.BColorButton.setColor(self.bcolor)
        self.history_file_path_field = KLineEdit(HISTORY_FILE_PATH)
        self.history_file_path_field.setDisabled(True)
        self.python_file_path_field = KLineEdit(__file__)
        self.python_file_path_field.setDisabled(True)
        self.kill_baloo = QCheckBox("Disable Baloo")
        self.kill_baloo.setToolTip("Enable/Disable KDE Desktop Search Indexing")
        self.kill_baloo.stateChanged.connect(lambda: call(
            DISABLE_BALOO_CMD.format(str(
                not self.kill_baloo.isChecked()).lower()), shell=True))
        self.kill_baloo.stateChanged.connect(lambda: QMessageBox.information(
            self.dialog, __doc__, """
            <b>Indexing Disabled, Baloo is Dead !
            """ if self.kill_baloo.isChecked() else """
            <b>Indexing Enabled, Baloo is Running !"""))
        # pack all widgets
        self.layBox.addWidget(self.title, 0, 1)
        self.layBox.addWidget(QLabel("Font"), 1, 0)
        self.layBox.addWidget(self.FontButton, 1, 1)
        self.layBox.addWidget(QLabel("Text Color"), 2, 0)
        self.layBox.addWidget(self.ColorButton, 2, 1)
        self.layBox.addWidget(QLabel("Alternate Color"), 3, 0)
        self.layBox.addWidget(self.BColorButton, 3, 1)
        self.layBox.addWidget(QLabel(), 4, 0)
        self.layBox.addWidget(QLabel("Mainteniance"), 5, 0)
        self.layBox.addWidget(self.UpdateDB, 5, 1)
        self.layBox.addWidget(QLabel("Privacy"), 6, 0)
        self.layBox.addWidget(self.Histor, 6, 1)
        self.layBox.addWidget(QLabel("History file"), 7, 0)
        self.layBox.addWidget(self.history_file_path_field, 7, 1)
        self.layBox.addWidget(QLabel(__doc__ + "file"), 8, 0)
        self.layBox.addWidget(self.python_file_path_field, 8, 1)
        self.layBox.addWidget(QLabel("Banned Words"), 9, 0)
        self.layBox.addWidget(self.banned, 9, 1)

        self.layBox.addWidget(QLabel("<b>Disable Indexing"), 11, 0)
        self.layBox.addWidget(self.kill_baloo, 11, 1)
        # button box on the bottom
        self.dialog.setButtons(KDialog.ButtonCodes(
            KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel | KDialog.Apply)))
        # connect
        self.dialog.applyClicked.connect(self.configAccepted)
        self.dialog.okClicked.connect(self.configAccepted)

    @pyqtSignature("configAccepted()")
    def configAccepted(self):
        """Save configuration settings."""
        self.tcolor = self.ColorButton.color()
        self.bcolor = self.BColorButton.color()
        self._widget.treeview.nativeWidget().setFont(self.tfont)
        self._widget.treeview.nativeWidget().setStyleSheet(
            "color:{};alternate-background-color:{}".format(self.tcolor.name(),
                                                            self.bcolor.name()))
        self.configurations.writeEntry("TextColor", self.tcolor.name())
        self.configurations.writeEntry("AlternateBColor", self.bcolor.name())
        self.configurations.writeEntry("TextFont", QVariant(self.tfont))
        self.configurations.writeEntry("Banned", self.banned.toPlainText())

    def showConfigurationInterface(self):
        """Show configuration dialog."""
        self.dialog.show()
        self.dialog.raise_()


def CreateApplet(parent):
    """Hook to return the whole Applet."""
    return PylouApplet(parent)
