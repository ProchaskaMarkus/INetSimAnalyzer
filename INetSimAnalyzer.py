##################################################################
#
#  @Author: Markus Prochaska
#  @Date: 2016
#  @File: INetSimViewer.py
#
###################################################################
import glob
import sys
import os
import re
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from Ui_INetSimAnalyzer import Ui_INetSimAnalyzer
import argparse

gINetSim = "inetsim"
gServiceLogPath = "var/log/inetsim/service.log"

class INetSimAnalyzerGui(QWidget, Ui_INetSimAnalyzer):
    def __init__(self, hostip, port, bDark, parent=None):
        super(INetSimAnalyzerGui, self).__init__(parent)
        self.setupUi(self)
        self.pushButton_Config.setVisible(False)
        self.pushButton_Refresh.setVisible(False)
        self.lineEdit_PathLogs.setEnabled(False)
        self.lineEdit_PathReport.setEnabled(False)
        self._port = port
        self._hostip = hostip
        if not bDark:
            self.activateDarkTheme()
        self._processInetSim = QProcess()
        self._UdpSocketAlarm = QUdpSocket(self)
        self._modelListView = QStandardItemModel()
        self.listView_FilterType.setModel(self._modelListView)
        self.dateTimeEdit_Start.setDate(QDateTime.currentDateTime().date())
        self.dateTimeEdit_End.setDate(QDateTime.currentDateTime().addDays(1).date())
        self._fileWatcher = QFileSystemWatcher()

        global gServiceLogPath
        gServiceLogPath = self.lineEdit_PathLogs.text() + "/service.log"
        self._fileWatcher.addPath(gServiceLogPath)
        self.connectStuff()
        self.refreshComboboxFiles()
        self.resizeAllColumns()

    def resizeAllColumns(self):
        self.tableWidget_Computer.resizeColumnToContents(0)
        self.tableWidget_Computer.setColumnWidth(0, self.tableWidget_Computer.columnWidth(0) + 10)
        self.tableWidget_Computer.resizeColumnToContents(1)
        self.tableWidget_Computer.setColumnWidth(1, self.tableWidget_Computer.columnWidth(1) + 10)
        self.tableWidget_Computer.resizeColumnToContents(2)
        self.tableWidget_Computer.setColumnWidth(2, self.tableWidget_Computer.columnWidth(2) + 10)
        self.tableWidget_Computer.resizeColumnToContents(3)
        self.tableWidget_Computer.setColumnWidth(3, self.tableWidget_Computer.columnWidth(3) + 10)


    def __del__(self):
        self._UdpSocketAlarm.close()
        self.stopINetSim()


    def activateDarkTheme(self):
        qApp.setStyle(QStyleFactory.create("fusion"))
        dark = QPalette()
        dark.setColor(QPalette.Window, QColor(53, 53, 53))
        dark.setColor(QPalette.WindowText, Qt.white)
        dark.setColor(QPalette.Base, QColor(25, 25, 25))
        dark.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark.setColor(QPalette.ToolTipBase, Qt.white)
        dark.setColor(QPalette.ToolTipText, Qt.white)
        dark.setColor(QPalette.Text, Qt.white)
        dark.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
        dark.setColor(QPalette.Disabled, QPalette.Button, Qt.darkGray)
        dark.setColor(QPalette.ButtonText, Qt.white)
        dark.setColor(QPalette.BrightText, Qt.red)
        dark.setColor(QPalette.Link, QColor(42, 130, 217))
        dark.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark.setColor(QPalette.HighlightedText, Qt.black)
        qApp.setPalette(dark);
        qApp.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")


    def connectStuff(self):
        self._processInetSim.finished.connect(self.on_inetSim_finished)
        self._processInetSim.readyReadStandardOutput.connect(self.on_readStdOutput)
        self.lineEdit_Search.textChanged.connect(self.on_lineEdit_Search_textChanged)
        self.checkBox_WatchMode.toggled.connect(self.on_checkBox_WachMode_toggled)
        self.checkBox_FilterTimeActive.toggled.connect(self.on_checkBox_FilterTimeActive_toggled)
        self.comboBox_FilterFiles.currentTextChanged.connect(self.on_comboBox_FilterFiles_currentTextChanged)
        self._modelListView.itemChanged.connect(self.listView_Filter_selectionChanged)
        self.dateTimeEdit_Start.dateTimeChanged.connect(self.dateTimeStart_changed)
        self.dateTimeEdit_End.dateTimeChanged.connect(self.dateTimeEnd_changed)
        self._fileWatcher.fileChanged.connect(self.serviceLogChanged)

        self._UdpSocketAlarm.bind(self._port)
        self._UdpSocketAlarm.readyRead.connect(self.receivedAlarm)


    def filterMessages(self):
        listFilters = []

        #Filter Types
        for row in range(self._modelListView.rowCount()):
            if self._modelListView.item(row).checkState() == Qt.Checked:
                listFilters.append(self._modelListView.item(row).text())
        for row in range(0, self.tableWidget_Computer.rowCount()):
            self.tableWidget_Computer.setRowHidden(row, True)
            #for col in range(0, self.tableWidget_Computer.columnCount() -1):
            textItem = self.tableWidget_Computer.item(row, 2).text()
            if any(sKey.lower() in textItem.lower() for sKey in listFilters) or textItem == "":
                self.tableWidget_Computer.setRowHidden(row, False)

        #Filter Search Text
        if len(self.lineEdit_Search.text()) > 0:
            for row in range(0, self.tableWidget_Computer.rowCount()):
                if not self.tableWidget_Computer.isRowHidden(row):
                    self.tableWidget_Computer.setRowHidden(row, True)
                    for col in range(0, self.tableWidget_Computer.columnCount() ):
                        textItem = self.tableWidget_Computer.item(row, col).text()
                        if self.lineEdit_Search.text().lower() in textItem.lower():
                            self.tableWidget_Computer.setRowHidden(row, False)

        #Filter Time
        if self.checkBox_FilterTimeActive.isChecked():
            for row in range(0, self.tableWidget_Computer.rowCount()):
                if not self.tableWidget_Computer.isRowHidden(row):
                    self.tableWidget_Computer.setRowHidden(row, True)
                    textTime = self.tableWidget_Computer.item(row, 0).text()
                    timeCell = QDateTime.fromString(textTime, "yyyy-MM-dd hh:mm:ss")
                    timeStart = self.dateTimeEdit_Start.dateTime()
                    timeEnd = self.dateTimeEdit_End.dateTime()
                    if timeStart <= timeCell <= timeEnd:
                        self.tableWidget_Computer.setRowHidden(row, False)


    @pyqtSlot()
    def serviceLogChanged(self):
        global gServiceLogPath
        file = open(gServiceLogPath, 'r')
        linesOfFile = file.readlines()
        self.sendMessage(linesOfFile[-1])
        #for line in file:
        #    self.sendMessage(str(line))
        #    break
        file.close()

    @pyqtSlot()
    def dateTimeStart_changed(self):
        self.filterMessages()


    @pyqtSlot()
    def dateTimeEnd_changed(self):
        self.filterMessages()


    @pyqtSlot()
    def on_pushButton_FilterSelectAll_clicked(self):
        for row in range(self._modelListView.rowCount()):
            self._modelListView.item(row).setCheckState(Qt.Checked)


    @pyqtSlot()
    def on_pushButton_FilterSelectNone_clicked(self):
        for row in range(self._modelListView.rowCount()):
            self._modelListView.item(row).setCheckState(Qt.Unchecked)


    @pyqtSlot()
    def listView_Filter_selectionChanged(self):
        self.filterMessages()


    @pyqtSlot()
    def receivedAlarm(self):

        while self._UdpSocketAlarm.hasPendingDatagrams():
            data, host, port = self._UdpSocketAlarm.readDatagram(self._UdpSocketAlarm.pendingDatagramSize())

            if self.checkBox_WatchMode.isChecked():
                self.graphicsView_Alarm.setStyleSheet("background-color: red;border-radius: 40px;border: 2px;border-style: solid;border-color: black;")
                self.tableWidget_Computer.insertRow(0)
                data = data.decode("utf-8")

                #GetTime
                indexStart = str(data).find("[", 0, len(data))
                indexEnd = str(data).find("]", indexStart + 1, len(data))
                strTime = str(data)[indexStart +1 : indexEnd]
                data = data[indexEnd:len(data)]
                item = QTableWidgetItem()
                item.setText(strTime)
                self.tableWidget_Computer.setItem(0, 0, item)

                #Get Session
                indexStart = str(data).find("[", 0, len(data))
                indexEnd = str(data).find("]", indexStart + 1, len(data))
                strTime = str(data)[indexStart +1 : indexEnd]
                data = data[indexEnd:len(data)]
                item = QTableWidgetItem()
                item.setText(strTime)
                self.tableWidget_Computer.setItem(0, 1, item)

                #Get Service
                indexStart = str(data).find("[", 0, len(data))
                indexEnd = str(data).find("]", indexStart + 1, len(data))

                strTime = str(data)[indexStart +1 : indexEnd]
                data = data[indexEnd:len(data)]
                item = QTableWidgetItem()
                item.setText(strTime)
                self.tableWidget_Computer.setItem(0, 2, item)
                indexEndService = strTime.find("_", 0, len(strTime))
                newFilterItem = strTime[0 : indexEndService]


                # Get IP
                indexStart = str(data).find("[", 0, len(data))
                indexEnd = str(data).find("]", indexStart + 1, len(data))
                strTime = str(data)[indexStart + 1: indexEnd]
                data = data[indexEnd + 2:len(data)]
                item = QTableWidgetItem()
                item.setText(strTime)
                self.tableWidget_Computer.setItem(0, 3, item)

                # Get Info
                item = QTableWidgetItem()
                item.setText(data)
                self.tableWidget_Computer.setItem(0, 4, item)

                #itemHost = QTableWidgetItem();
                #itemHost.setText(host.toString())
                #self.tableWidget_Computer.setItem(0, 3, itemHost)
                #self.addToTypesIfNoDuplicate(host.toString())

                self.addToTypesIfNoDuplicate(newFilterItem)

        self.resizeAllColumns()


    def addToTypesIfNoDuplicate(self, stext):
        if not self._modelListView.findItems(stext):
            item = QStandardItem()
            item.setCheckState(Qt.Checked)
            item.setCheckable(True)
            item.setText(stext)
            self._modelListView.insertRow(0)
            self._modelListView.setItem(0,0,item)
            self.filterMessages()


    def sendMessage(self, message):
        data = QByteArray()
        data.append(message)
        self._UdpSocketAlarm.writeDatagram(data.data(), QHostAddress(self._hostip), self._port)


    @pyqtSlot()
    def on_pushButton_Refresh_clicked(self):
        print("Refresh")

    @pyqtSlot()
    def on_pushButton_ResetAlarm_clicked(self):
        if self.checkBox_WatchMode.isChecked():
            self.graphicsView_Alarm.setStyleSheet("background-color: green;border-radius: 40px;border: 2px;border-style: solid;border-color: black;")
        else:
            self.graphicsView_Alarm.setStyleSheet("background-color: transparent;border-radius: 40px;border: 2px;border-style: solid;border-color: black;")


    @pyqtSlot()
    def on_pushButton_PathLogs_clicked(self):
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if os.path.exists(file):
            self.lineEdit_PathLogs.setText(file)
            global gServiceLogPath
            self._fileWatcher.removePath(gServiceLogPath)
            gServiceLogPath = self.lineEdit_PathLogs.text() + "/service.log"
            self._fileWatcher.addPath(gServiceLogPath)
            self.refreshComboboxFiles()
        self.lineEdit_Search.setFocus()


    @pyqtSlot()
    def on_pushButton_PathReport_clicked(self):
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if os.path.exists(file):
            self.lineEdit_PathReport.setText(file)
            self.refreshComboboxFiles()
        self.lineEdit_Search.setFocus()


    @pyqtSlot()
    def on_pushButton_ClearSearch_clicked(self):
        self.lineEdit_Search.clear()
        self.filterMessages()


    @pyqtSlot()
    def on_inetSim_finished(self):
        pidpath = "/var/run/inetsim.pid"
        if os.path.isfile(pidpath):
            os.remove(pidpath)
        self.pushButton_Stop.setEnabled(False)
        self.pushButton_Start.setEnabled(True)
        self.pushButton_Config.setEnabled(True)
        self.checkBox_WatchMode.setEnabled(True)
        self.pushButton_Refresh.setEnabled(True)
        self.textEdit_DebugOutput.append("INetSim closed!\n")
        self.textEdit_DebugOutput.verticalScrollBar().setValue(self.textEdit_DebugOutput.verticalScrollBar().maximum())


    @pyqtSlot()
    def on_readStdOutput(self):
        output = str(self._processInetSim.readAllStandardOutput().trimmed())
        ansi_escape = re.compile(r'\x1b[^m]*m')
        output = ansi_escape.sub('', output)
        self.textEdit_DebugOutput.append(output + "\n")
        self.textEdit_DebugOutput.verticalScrollBar().setValue(self.textEdit_DebugOutput.verticalScrollBar().maximum())


    @pyqtSlot()
    def on_lineEdit_Search_textChanged(self):
        self.filterMessages()


    @pyqtSlot()
    def on_checkBox_FilterTimeActive_toggled(self):
        self.filterMessages()


    @pyqtSlot()
    def on_pushButton_ClearLog_clicked(self):
        self.comboBox_FilterFiles.setCurrentIndex(0)

    @pyqtSlot()
    def on_pushButton_Config_clicked(self):
        print("show config")

    @pyqtSlot()
    def on_pushButton_Start_clicked(self):
        self.checkBox_WatchMode.setEnabled(False)
        self.pushButton_Start.setEnabled(False)
        self.pushButton_Config.setEnabled(False)
        self.pushButton_Stop.setEnabled(True)
        self.tableWidget_Computer.setColumnHidden(1, True)
        self.tableWidget_Computer.setColumnHidden(2, True)
        self.pushButton_Refresh.setEnabled(False)
        self.comboBox_FilterFiles.setEnabled(False)
        self.pushButton_PathLogs.setEnabled(False)
        self.pushButton_PathReport.setEnabled(False)
        self.checkBox_FilterTimeActive.setEnabled(False)
        self.pushButton_ResetAlarm.setEnabled(False)
        self.startINetSim()


    @pyqtSlot()
    def on_pushButton_Stop_clicked(self):
        self.checkBox_WatchMode.setEnabled(False)
        self.pushButton_Stop.setEnabled(False)
        self.pushButton_Start.setEnabled(True)
        self.pushButton_Config.setEnabled(True)
        self.tableWidget_Computer.setColumnHidden(1, True)
        self.tableWidget_Computer.setColumnHidden(2, True)
        self.pushButton_Refresh.setEnabled(True)
        self.comboBox_FilterFiles.setEnabled(True)
        self.pushButton_PathLogs.setEnabled(True)
        self.pushButton_PathReport.setEnabled(True)
        self.checkBox_FilterTimeActive.setEnabled(True)
        self.pushButton_ResetAlarm.setEnabled(True)
        self.stopINetSim()
        self.refreshComboboxFiles()


    @pyqtSlot()
    def on_checkBox_WachMode_toggled(self):
        self.pushButton_Stop.setEnabled(False)
        self._modelListView.clear()
        self.on_pushButton_ResetAlarm_clicked()
        self.listView_FilterType.setModel(self._modelListView)
        self.tableWidget_Computer.clearContents()
        self.tableWidget_Computer.setRowCount(0)
        self.tableWidget_Computer.setColumnHidden(0, False)
        self.tableWidget_Computer.setColumnHidden(1, False)
        self.tableWidget_Computer.setColumnHidden(2, False)
        self.tableWidget_Computer.setColumnHidden(3, False)
        self.tableWidget_Computer.setColumnHidden(4, False)
        if self.checkBox_WatchMode.isChecked():
            self.checkBox_FilterTimeActive.setChecked(False)
            self.pushButton_Start.setEnabled(False)
            self.pushButton_Config.setEnabled(False)
            self.pushButton_Refresh.setEnabled(False)
            self.comboBox_FilterFiles.setEnabled(False)
            self.pushButton_PathLogs.setEnabled(False)
            self.pushButton_PathReport.setEnabled(False)
        else:
            self.pushButton_Start.setEnabled(True)
            self.pushButton_Config.setEnabled(True)
            self.pushButton_Refresh.setEnabled(True)
            self.comboBox_FilterFiles.setEnabled(True)
            self.pushButton_PathLogs.setEnabled(True)
            self.pushButton_PathReport.setEnabled(True)
            self.setTimeMinAndMax()


    @pyqtSlot()
    def on_comboBox_FilterFiles_currentTextChanged(self):
        self.tableWidget_Computer.setColumnHidden(1, True)
        self.tableWidget_Computer.setColumnHidden(2, True)
        self.tableWidget_Computer.setColumnHidden(3, True)
        self.tableWidget_Computer.clearContents()
        self.tableWidget_Computer.setRowCount(0)
        self._modelListView.clear()
        self.listView_FilterType.setModel(self._modelListView)
        filename = self.comboBox_FilterFiles.currentText()
        if filename == "main.log":
            self.parseMainLog(filename)
        elif filename == "service.log":
            self.parseServiceLog(filename)
        elif "report" in filename and ".txt" in filename:
            self.parseReport(filename)
        else:
            return
        self.setTimeMinAndMax()
        self.resizeAllColumns()


    def setTimeMinAndMax(self):
        if self.tableWidget_Computer.rowCount() == 0:
            return

        minDateTime = QDateTime.fromString(self.tableWidget_Computer.item(0, 0).text(), "yyyy-MM-dd hh:mm:ss")
        maxDateTime = QDateTime.fromString(self.tableWidget_Computer.item(0, 0).text(), "yyyy-MM-dd hh:mm:ss")
        for row in range (0, self.tableWidget_Computer.rowCount()):
            minDateTime = QDateTime.fromString(self.tableWidget_Computer.item(row, 0).text(), "yyyy-MM-dd hh:mm:ss")
            maxDateTime = QDateTime.fromString(self.tableWidget_Computer.item(row, 0).text(), "yyyy-MM-dd hh:mm:ss")
            if minDateTime.isValid() and maxDateTime.isValid():
                break

        for row in range(0, self.tableWidget_Computer.rowCount()):
            textTime = self.tableWidget_Computer.item(row, 0).text()
            timeCell = QDateTime.fromString(textTime, "yyyy-MM-dd hh:mm:ss")
            if timeCell.isValid():
                if timeCell < minDateTime:
                    minDateTime = timeCell
                if timeCell > maxDateTime:
                    maxDateTime = timeCell

        self.dateTimeEdit_Start.setDateTime(minDateTime)
        self.dateTimeEdit_End.setDateTime(maxDateTime)


    def parseMainLog(self, filename):
        print("Not implemented AddOn")


    def parseServiceLog(self, filename):
        self.tableWidget_Computer.setColumnHidden(1, False)
        self.tableWidget_Computer.setColumnHidden(2, False)
        self.tableWidget_Computer.setColumnHidden(3, False)
        self.tableWidget_Computer.clearContents()
        seperator = "\\"
        if "/" in self.lineEdit_PathLogs.text():
            seperator = "/"
        filename = self.lineEdit_PathLogs.text() + seperator + filename
        file = open(str(filename), 'r')
        for data in file:
            # GetTime
            nRow = self.tableWidget_Computer.rowCount()
            self.tableWidget_Computer.insertRow(nRow)

            indexStart = str(data).find("[", 0, len(data))
            indexEnd = str(data).find("]", indexStart + 1, len(data))
            strTime = str(data)[indexStart + 1: indexEnd]
            data = data[indexEnd:len(data)]
            item = QTableWidgetItem()
            item.setText(strTime)
            self.tableWidget_Computer.setItem(nRow, 0, item)

            # Get Session
            indexStart = str(data).find("[", 0, len(data))
            indexEnd = str(data).find("]", indexStart + 1, len(data))
            strTime = str(data)[indexStart + 1: indexEnd]
            data = data[indexEnd:len(data)]
            item = QTableWidgetItem()
            item.setText(strTime)
            self.tableWidget_Computer.setItem(nRow, 1, item)

            # Get Service
            indexStart = str(data).find("[", 0, len(data))
            indexEnd = str(data).find("]", indexStart + 1, len(data))
            strTime = str(data)[indexStart + 1: indexEnd]
            data = data[indexEnd:len(data)]
            item = QTableWidgetItem()
            item.setText(strTime)
            self.tableWidget_Computer.setItem(nRow, 2, item)
            indexEndService = strTime.find("_", 0, len(strTime))
            newFilterItem = strTime[0: indexEndService]

            # Get IP
            indexStart = str(data).find("[", 0, len(data))
            indexEnd = str(data).find("]", indexStart + 1, len(data))
            strTime = str(data)[indexStart + 1: indexEnd]
            data = data[indexEnd + 2:len(data)]
            item = QTableWidgetItem()
            item.setText(strTime)
            self.tableWidget_Computer.setItem(nRow, 3, item)

            # Get Info
            item = QTableWidgetItem()
            item.setText(data)
            self.tableWidget_Computer.setItem(nRow, 4, item)

            self.addToTypesIfNoDuplicate(newFilterItem)


    def parseReport(self, filename):
        self.tableWidget_Computer.setColumnHidden(1, False)
        self.tableWidget_Computer.setColumnHidden(2, False)
        self.tableWidget_Computer.setColumnHidden(3, True)
        self.tableWidget_Computer.clearContents()
        seperator = "\\"
        if "/" in self.lineEdit_PathReport.text():
            seperator = "/"
        filename = self.lineEdit_PathReport.text() + seperator + filename
        file = open(str(filename), 'r')
        nLineNumber = -1
        #if sum(1 for line in file) < 12:
        #    return
        session = ""

        for data in file:
            nLineNumber = nLineNumber + 1
            if len(data) < 3:
                continue

            nRow = self.tableWidget_Computer.rowCount()
            self.tableWidget_Computer.insertRow(nRow)

            if nLineNumber == 0:
                indexStart = str(data).find("'", 0, len(data))
                indexEnd = str(data).find("'", indexStart + 1, len(data))
                strText = str(data)[indexStart + 1 : indexEnd]
                item = QTableWidgetItem()
                item.setText(strText)
                session = strText
                self.tableWidget_Computer.setItem(nRow, 1, item)
                self.tableWidget_Computer.setItem(nRow, 0, QTableWidgetItem(""))
                self.tableWidget_Computer.setItem(nRow, 2, QTableWidgetItem(""))
                self.tableWidget_Computer.setItem(nRow, 3, QTableWidgetItem(""))

                item = QTableWidgetItem()
                item.setText(data)
                self.tableWidget_Computer.setItem(nRow, 4, item)
                continue

            if nLineNumber == 2 or nLineNumber == 3 or nLineNumber == 4 or "===" in str(data):
                self.tableWidget_Computer.setItem(nRow, 0, QTableWidgetItem(""))
                self.tableWidget_Computer.setItem(nRow, 1, QTableWidgetItem(session))
                self.tableWidget_Computer.setItem(nRow, 2, QTableWidgetItem(""))
                self.tableWidget_Computer.setItem(nRow, 3, QTableWidgetItem(""))
                item = QTableWidgetItem()
                item.setText(data)
                self.tableWidget_Computer.setItem(nRow, 4, item)
                continue


            #Get Time
            indexEnd = str(data).find("  ", 0, len(data))
            strTime = str(data)[0 : indexEnd]
            data = data[indexEnd:len(data)]
            item = QTableWidgetItem()
            item.setText(strTime)
            self.tableWidget_Computer.setItem(nRow, 0, item)

            bNewFilterItem = False

            self.tableWidget_Computer.setItem(nRow, 1, QTableWidgetItem(session))
            if str(data).find("connection", 0, len(data)) == -1:
                self.tableWidget_Computer.setItem(nRow, 2, QTableWidgetItem(""))
            else:
            # Get Service
                indexEnd = str(data).find("connection", 0, len(data))
                strTime = str(data)[1: indexEnd + len("connection") ]
                data = data[indexEnd + len("connection,"):len(data)]
                item = QTableWidgetItem()
                item.setText(strTime)
                self.tableWidget_Computer.setItem(nRow, 2, item)
                newFilterItem = strTime.replace(" connection", "")
                bNewFilterItem = True

            self.tableWidget_Computer.setItem(nRow, 3, QTableWidgetItem(""))

            # Get Info
            item = QTableWidgetItem()
            item.setText(data)
            self.tableWidget_Computer.setItem(nRow, 4, item)

            if bNewFilterItem:
                self.addToTypesIfNoDuplicate(newFilterItem)


    def refreshComboboxFiles(self):
        self.comboBox_FilterFiles.clear()
        self.comboBox_FilterFiles.addItem("None")
        if os.path.isdir(self.lineEdit_PathLogs.text().replace("\\", "\\\\")):
            os.chdir(self.lineEdit_PathLogs.text())
            for file in glob.glob("service.log"):
                self.comboBox_FilterFiles.addItem(str(file))
        if os.path.isdir(self.lineEdit_PathReport.text().replace("\\","\\\\")):
            os.chdir(self.lineEdit_PathReport.text())
            for file in glob.glob("*.txt"):
                self.comboBox_FilterFiles.addItem(str(file))


    def startINetSim(self):
        global gINetSim
        self._processInetSim.start(gINetSim)

    def stopINetSim(self):
        if self._processInetSim.isOpen():
            #self._processInetSim.kill()
            self._processInetSim.terminate()
            while self._processInetSim.waitForFinished():
                self.on_readStdOutput()
            self._processInetSim.close()



def handleArgs():
    parser = argparse.ArgumentParser(description='Script to control and analyse INetSim M108 by Markus Prochaska')
    parser.add_argument('-i','--ip', help='Host IP for alarms', required=False, type=str, default="127.0.0.1")
    parser.add_argument('-p', '--port', help='Port to send/receive alarms', required=False, type=int, default=46000)
    parser.add_argument('-s', '--start', help='Start INetSim automatically', required=False, action='store_true')
    parser.add_argument('-d', '--dark', help='Disables dark theme', required=False, action='store_true')
    args = parser.parse_args()
    return str(args.ip), int(args.port), bool(args.start), bool(args.dark)


def main():
    app = QApplication(sys.argv)
    hostIp, port, bStart, bDark = handleArgs()
    window = INetSimAnalyzerGui(hostIp, port, bDark)
    window.show()
    if bStart:
        window.startINetSim()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
