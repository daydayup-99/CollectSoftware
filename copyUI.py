import os.path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

import settings
from progress_bar import CustomProgressBar


class JobSelectionDialog(QtWidgets.QDialog):
    def __init__(self, car_path, parent=None):
        super().__init__(parent)
        self.car_path = car_path
        self.selected_folders = []
        self.all_folders = []
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("选择文件夹")
        self.setMinimumSize(400, 500)

        layout = QtWidgets.QVBoxLayout(self)

        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("搜索：")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词过滤...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        self.label = QtWidgets.QLabel("请选择需要的文件夹：")
        layout.addWidget(self.label)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        self.container = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container)
        self.scroll_area.setWidget(self.container)

        self.checkboxes = []
        if os.path.exists(self.car_path):
            self.all_folders = [f for f in os.listdir(self.car_path) if os.path.isdir(os.path.join(self.car_path, f))]
        self._update_folder_list()

        button_layout = QtWidgets.QHBoxLayout()
        self.select_all_btn = QtWidgets.QPushButton("全选")
        self.select_none_btn = QtWidgets.QPushButton("全不选")
        self.ok_btn = QtWidgets.QPushButton("确定")
        self.cancel_btn = QtWidgets.QPushButton("取消")

        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.select_none_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.select_all_btn.clicked.connect(self.select_all)
        self.select_none_btn.clicked.connect(self.select_none)
        self.ok_btn.clicked.connect(self.accept_selection)
        self.cancel_btn.clicked.connect(self.reject)
        self.search_edit.textChanged.connect(self.filter_folders)

    def _update_folder_list(self, filter_text=""):
        for checkbox in self.checkboxes:
            checkbox.deleteLater()
        self.checkboxes.clear()
        filtered_folders = [f for f in self.all_folders if filter_text.lower() in f.lower()]
        for folder in sorted(filtered_folders):
            checkbox = QtWidgets.QCheckBox(folder)
            self.container_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

    def filter_folders(self, text):
        self._update_folder_list(text)

    def select_all(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def select_none(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def accept_selection(self):
        self.selected_folders = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        self.accept()

    def get_selected_folders(self):
        return self.selected_folders


class Ui_PreimageWindow(object):
    progress_updated = QtCore.pyqtSignal(int)

    def __init__(self):
        self.level_padding = 10
        self.vertical_padding = 50
        self.path_edit_width = 400
        self.path_edit_height = 30
        self.date_edit_width = 160
        self.name_edit_width = 200
        self.startX = 40
        self.startY = 30
        self.progress_updated.connect(self.update_progress)
        self.selected_batch_numbers = []

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def getY(self, n):
        return self.startY + self.vertical_padding * n

    def setupUi(self, PreimageWindow):
        PreimageWindow.setObjectName("PreimageWindow")
        PreimageWindow.resize(1600, 850)
        self.centralwidget = QtWidgets.QWidget(PreimageWindow)
        self.centralwidget.setObjectName("centralwidget")

        # AOI和AVI勾选框
        self.aoiLabel = QtWidgets.QLabel(self.centralwidget)
        self.aoiLabel.setGeometry(QtCore.QRect(self.startX + 80, self.startY, 40, 30))
        self.aoiLabel.setObjectName("aoiLabel")
        self.aoiCheckBox = QtWidgets.QCheckBox(self.centralwidget)
        self.aoiCheckBox.setGeometry(QtCore.QRect(self.startX + 120, self.startY, 20, 30))
        self.aoiCheckBox.setObjectName("aoiCheckBox")

        self.aviLabel = QtWidgets.QLabel(self.centralwidget)
        self.aviLabel.setGeometry(QtCore.QRect(self.startX + 280 + self.level_padding + 120, self.startY, 40, 30))
        self.aviLabel.setObjectName("aviLabel")
        self.aviCheckBox = QtWidgets.QCheckBox(self.centralwidget)
        self.aviCheckBox.setGeometry(QtCore.QRect(self.startX + 280 + self.level_padding + 160, self.startY, 20, 30))
        self.aviCheckBox.setObjectName("aviCheckBox")

        # CAR路径配置
        self.carLabel = QtWidgets.QLabel(self.centralwidget)
        self.carLabel.setGeometry(QtCore.QRect(self.startX, self.getY(1), 80, 30))
        self.carLabel.setObjectName("carLabel")
        self.carEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.carEdit.setGeometry(
            QtCore.QRect(self.startX + 80, self.getY(1), self.path_edit_width, self.path_edit_height))
        self.carEdit.setObjectName("carEdit")
        self.carButton = QtWidgets.QPushButton(self.centralwidget)
        self.carButton.setGeometry(QtCore.QRect(self.startX + 80 + self.path_edit_width, self.getY(1), 50, 30))
        self.carButton.setObjectName("carButton")

        # JOB路径配置
        self.jobLabel = QtWidgets.QLabel(self.centralwidget)
        self.jobLabel.setGeometry(QtCore.QRect(self.startX, self.getY(2), 80, 30))
        self.jobLabel.setObjectName("jobLabel")
        self.jobEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.jobEdit.setGeometry(
            QtCore.QRect(self.startX + 80, self.getY(2), self.path_edit_width, self.path_edit_height))
        self.jobEdit.setObjectName("jobEdit")
        self.jobButton = QtWidgets.QPushButton(self.centralwidget)
        self.jobButton.setGeometry(QtCore.QRect(self.startX + 80 + self.path_edit_width, self.getY(2), 50, 30))
        self.jobButton.setObjectName("jobButton")

        # Study路径配置
        self.studyLabel = QtWidgets.QLabel(self.centralwidget)
        self.studyLabel.setGeometry(QtCore.QRect(self.startX, self.getY(3), 80, 30))
        self.studyLabel.setObjectName("saveLabel")
        self.studyEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.studyEdit.setGeometry(
            QtCore.QRect(self.startX + 80, self.getY(3), self.path_edit_width, self.path_edit_height))
        self.studyEdit.setObjectName("saveEdit")
        self.studyButton = QtWidgets.QPushButton(self.centralwidget)
        self.studyButton.setGeometry(QtCore.QRect(self.startX + 80 + self.path_edit_width, self.getY(3), 50, 30))
        self.studyButton.setObjectName("saveButton")

        # LOG路径配置
        self.logLabel = QtWidgets.QLabel(self.centralwidget)
        self.logLabel.setGeometry(QtCore.QRect(self.startX, self.getY(4), 80, 30))
        self.logLabel.setObjectName("logLabel")
        self.logEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.logEdit.setGeometry(
            QtCore.QRect(self.startX + 80, self.getY(4), self.path_edit_width, self.path_edit_height))
        self.logEdit.setObjectName("logEdit")
        self.logButton = QtWidgets.QPushButton(self.centralwidget)
        self.logButton.setGeometry(QtCore.QRect(self.startX + 80 + self.path_edit_width, self.getY(4), 50, 30))
        self.logButton.setObjectName("logButton")

        # 保存路径配置
        self.saveLabel = QtWidgets.QLabel(self.centralwidget)
        self.saveLabel.setGeometry(QtCore.QRect(self.startX, self.getY(5), 80, 30))
        self.saveLabel.setObjectName("saveLabel")
        self.saveEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.saveEdit.setGeometry(
            QtCore.QRect(self.startX + 80, self.getY(5), self.path_edit_width, self.path_edit_height))
        self.saveEdit.setObjectName("saveEdit")
        self.saveButton = QtWidgets.QPushButton(self.centralwidget)
        self.saveButton.setGeometry(QtCore.QRect(self.startX + 80 + self.path_edit_width, self.getY(5), 50, 30))
        self.saveButton.setObjectName("saveButton")

        # 开始时间
        self.date_label = QtWidgets.QLabel(self.centralwidget)
        self.date_label.setGeometry(QtCore.QRect(self.startX, self.getY(6), 80, 30))
        self.date_label.setObjectName("date_label")
        self.dateEdit = QtWidgets.QDateEdit(self.centralwidget)
        startDateX = self.startX + 80
        self.dateEdit.setGeometry(QtCore.QRect(startDateX, self.getY(6), self.date_edit_width, 30))
        self.dateEdit.setObjectName("dateEdit")

        # 结束时间
        self.dateEndLabel = QtWidgets.QLabel(self.centralwidget)
        self.dateEndLabel.setGeometry(
            QtCore.QRect(startDateX + self.date_edit_width + self.level_padding + 40, self.getY(6), 80, 30))
        self.dateEndLabel.setObjectName("dateEndLabel")
        self.dateEndEdit = QtWidgets.QDateEdit(self.centralwidget)
        endDateX = startDateX + self.date_edit_width + self.level_padding + 120
        self.dateEndEdit.setGeometry(QtCore.QRect(endDateX, self.getY(6), self.date_edit_width, 30))
        self.dateEndEdit.setObjectName("dateEndEdit")

        # 存储方式
        self.savingModeLabel = QtWidgets.QLabel(self.centralwidget)
        self.savingModeLabel.setGeometry(QtCore.QRect(self.startX, self.getY(7), 80, 30))
        self.savingModeLabel.setObjectName("savingModeLabel")
        self.saveset_comboBox = QtWidgets.QComboBox(self.centralwidget)
        self.saveset_comboBox.setGeometry(QtCore.QRect(self.startX + 80, self.getY(7), 160, 30))
        self.saveset_comboBox.setObjectName("saveset_comboBox")
        self.saveset_comboBox.addItems(["按日期存储", "按料号存储", "按批量存储(从0开始)", "按批量存储", "手动机存储"])

        # 批量名称， 用于拷贝批量下的文件， 只用于按批量存储(从0开始)
        self.copyModelLabel = QtWidgets.QLabel(self.centralwidget)
        self.copyModelLabel.setGeometry(QtCore.QRect(self.startX + 280 + self.level_padding, self.getY(7), 80, 30))
        self.copyMode_comboBox = QtWidgets.QComboBox(self.centralwidget)
        self.copyMode_comboBox.setGeometry(QtCore.QRect(self.startX + 360 + self.level_padding, self.getY(7), 160, 30))
        self.copyMode_comboBox.addItems(["按日期拷贝", "按板号拷贝", "定时拷贝", "一键拷贝", "离线机拷贝"])

        # 料号选择
        self.chooseJob_button = QtWidgets.QPushButton(self.centralwidget)
        self.chooseJob_button.setGeometry(QtCore.QRect(self.startX, self.getY(10), 160, 30))
        self.chooseJob_button.setObjectName("chooseJob_button")
        self.chooseJob_button.setText("料号选择")
        self.chooseJob_button.clicked.connect(self.chooseJob_button_clicked_handler)

        #最大批次数
        self.maxPlNumLabel = QtWidgets.QLabel(self.centralwidget)
        self.maxPlNumLabel.setGeometry(QtCore.QRect(self.startX, self.getY(8), 100, 30))
        self.maxPlNumLabel.setObjectName("maxPlNumLabel")
        self.maxPlNumLabel.setText("最大批次数")
        self.maxPlNumEdit = QtWidgets.QLineEdit(self.centralwidget)
        startNumX = self.startX + 100
        self.maxPlNumEdit.setGeometry(QtCore.QRect(startNumX, self.getY(8), 80, 30))
        self.maxPlNumEdit.setObjectName("maxPlNumEdit")
        self.maxPlNumEdit.setText(str(5))

        # 机器类型
        self.machineTypeLabel = QtWidgets.QLabel(self.centralwidget)
        self.machineTypeLabel.setGeometry(QtCore.QRect(self.startX + 280 + self.level_padding, self.getY(8), 80, 30))
        self.machineTypeLabel.setObjectName("machineTypeLabel")
        self.machineType_comboBox = QtWidgets.QComboBox(self.centralwidget)
        self.machineType_comboBox.setGeometry(QtCore.QRect(self.startX + 360 + self.level_padding, self.getY(8), 160, 30))
        self.machineType_comboBox.setObjectName("machineType_comboBox")
        self.machineType_comboBox.addItems(["在线机", "离线机"])
        self.machineType_comboBox.setEnabled(False)
        if self.machineType_comboBox.currentText() == "在线机":
            self.chooseJob_button.setVisible(False)
            self.maxPlNumEdit.setEnabled(False)

        # 板号相关
        self.startNumLabel = QtWidgets.QLabel(self.centralwidget)
        self.startNumLabel.setGeometry(QtCore.QRect(self.startX, self.getY(9), 100, 30))
        self.startNumLabel.setObjectName("startNumLabel")
        self.startEdit = QtWidgets.QLineEdit(self.centralwidget)
        startNumX = self.startX + 80
        self.startEdit.setGeometry(QtCore.QRect(startNumX, self.getY(9), 80, 30))
        self.startEdit.setObjectName("startEdit")

        self.endNumLabel = QtWidgets.QLabel(self.centralwidget)
        self.endNumLabel.setGeometry(QtCore.QRect(startNumX + 100 + self.level_padding, self.getY(9), 100, 30))
        self.endNumLabel.setObjectName("endNumLabel")
        endNumX = startNumX + 180 + self.level_padding
        self.endEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.endEdit.setGeometry(QtCore.QRect(endNumX, self.getY(9), 80, 30))
        self.endEdit.setObjectName("endEdit")

        self.maxNumLabel = QtWidgets.QLabel(self.centralwidget)
        self.maxNumLabel.setGeometry(QtCore.QRect(endNumX + 100 + self.level_padding, self.getY(9), 100, 30))
        self.maxNumLabel.setObjectName("maxNumLabel")
        maxNumX = endNumX + 180 + self.level_padding
        self.maxEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.maxEdit.setGeometry(QtCore.QRect(maxNumX, self.getY(9), 80, 30))
        self.maxEdit.setObjectName("maxEdit")

        # 进度条
        self.progress_bar = CustomProgressBar(self.centralwidget)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setGeometry(QtCore.QRect(650, self.startY, 35, 750))

        # 拷贝按钮相关
        self.copy_aidataButton = QtWidgets.QPushButton(self.centralwidget)
        self.copy_aidataButton.setGeometry(QtCore.QRect(self.startX + 140 + 140, self.getY(10), 120, 50))
        self.copy_aidataButton.setObjectName("copy_aidataButton")

        # self.copy_all_dayButton = QtWidgets.QPushButton(self.centralwidget)
        # self.copy_all_dayButton.setGeometry(QtCore.QRect(self.startX + 140, self.getY(7), 120, 50))
        # self.copy_all_dayButton.setObjectName("copy_all_dayButton")
        #
        # self.copy_timer_button = QtWidgets.QPushButton(self.centralwidget)
        # self.copy_timer_button.setGeometry(QtCore.QRect(self.startX + 140 + 140, self.getY(7), 120, 50))
        # self.copy_timer_button.setObjectName("copy_timer_button")

        self.stop_Button = QtWidgets.QPushButton(self.centralwidget)
        self.stop_Button.setGeometry(QtCore.QRect(self.startX + 140 + 140 + 140, self.getY(10), 120, 50))
        self.stop_Button.setObjectName("stop_Button")

        # 日志输出
        self.log_output = QtWidgets.QTextBrowser(self.centralwidget)
        self.log_output.setReadOnly(True)
        self.log_output.setGeometry(QtCore.QRect(700, self.startY, 400, 750))

        self.warning_browser = QtWidgets.QTextBrowser(self.centralwidget)
        self.warning_browser.setGeometry(QtCore.QRect(700 + 400 + self.level_padding, self.startY, 400, 750))
        self.warning_browser.setObjectName("warning_browser")

        # 创建滚动区域和标签
        scroll_area = QtWidgets.QScrollArea(self.centralwidget)
        scroll_area.setGeometry(QtCore.QRect(self.startX, self.getY(11) + 30, 550, 350))
        scroll_area.setWidgetResizable(True)  # 设置滚动区域自适应内容大小
        scroll_area.setObjectName("scroll_area")

        self.label_10 = QtWidgets.QLabel()
        self.label_10.setObjectName("label_10")
        self.label_10.setWordWrap(True)  # 启用文本自动换行
        self.label_10.setAlignment(Qt.AlignTop)  # 设置文本顶部对齐

        # 将标签放置在滚动区域中
        scroll_area.setWidget(self.label_10)

        PreimageWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(PreimageWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 837, 23))
        self.menubar.setObjectName("menubar")
        PreimageWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(PreimageWindow)
        self.statusbar.setObjectName("statusbar")
        PreimageWindow.setStatusBar(self.statusbar)

        self.retranslateUi(PreimageWindow)
        QtCore.QMetaObject.connectSlotsByName(PreimageWindow)
        self.aoiCheckBox.stateChanged.connect(self.on_aoi_changed)
        self.aviCheckBox.stateChanged.connect(self.on_avi_changed)
        self.machineType_comboBox.currentIndexChanged.connect(self.on_machine_type_changed)
    #     self.timer1 = QTimer(self)
    #     self.timer1.timeout.connect(self.updateProgress)
    #     self.timer1.start(1000)  # 每秒钟增加一次进度
    #
    # def updateProgress(self):
    #     curVal = self.progress_bar.value()
    #     if curVal < 100:
    #         self.progress_bar.setValue(curVal + 10)
    #     else:
    #         return
    def on_aoi_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.aviCheckBox.setChecked(False)

    def on_avi_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.aoiCheckBox.setChecked(False)
            self.machineType_comboBox.setEnabled(True)
        else:
            self.machineType_comboBox.setEnabled(False)
            
    def on_machine_type_changed(self, index):
        machine_type = self.machineType_comboBox.currentText()
        if machine_type == '在线机':
            self.saveset_comboBox.setEnabled(True)
            self.copyMode_comboBox.setCurrentIndex(1)
            self.startEdit.setEnabled(True)
            self.endEdit.setEnabled(True)
            self.maxEdit.setEnabled(True)
            self.chooseJob_button.setVisible(False)
            self.maxPlNumEdit.setEnabled(False)
        else:
            self.startEdit.setEnabled(False)
            self.endEdit.setEnabled(False)
            self.maxEdit.setEnabled(False)
            self.saveset_comboBox.setEnabled(False)
            self.copyMode_comboBox.setCurrentIndex(4)
            self.saveset_comboBox.setCurrentIndex(3)
            self.chooseJob_button.setVisible(True)
            self.maxPlNumEdit.setEnabled(True)

    def chooseJob_button_clicked_handler(self):
        car_path = self.carEdit.text()
        dialog = JobSelectionDialog(car_path, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.selected_batch_numbers = dialog.get_selected_folders()

    def retranslateUi(self, PreimageWindow):
        _translate = QtCore.QCoreApplication.translate
        PreimageWindow.setWindowTitle(_translate("PreimageWindow", "MainWindow"))
        self.carButton.setText(_translate("PreimageWindow", "..."))
        self.carLabel.setText(_translate("PreimageWindow", "CAR路径"))

        self.jobButton.setText(_translate("PreimageWindow", "..."))
        self.jobLabel.setText(_translate("PreimageWindow", "JOB路径"))

        self.saveButton.setText(_translate("PreimageWindow", "..."))
        self.saveLabel.setText(_translate("PreimageWindow", "保存路径"))

        self.studyButton.setText(_translate("PreimageWindow", "..."))
        self.studyLabel.setText(_translate("PreimageWindow", "STD路径"))

        self.logButton.setText(_translate("PreimageWindow", "..."))
        self.logLabel.setText(_translate("PreimageWindow", "LOG路径"))

        self.date_label.setText(_translate("PreimageWindow", "开始时间"))
        self.dateEndLabel.setText(_translate("PreimageWindow", "结束时间"))

        self.aoiLabel.setText(_translate("PreimageWindow", "AOI"))
        self.aviLabel.setText(_translate("PreimageWindow", "AVI"))

        self.copyModelLabel.setText(_translate("PreimageWindow", "拷贝方式"))
        self.machineTypeLabel.setText(_translate("PreimageWindow", "机器类型"))
        self.copy_aidataButton.setText(_translate("PreimageWindow", "开始拷贝"))
        # self.copy_all_dayButton.setText(_translate("PreimageWindow", "按日期拷贝"))
        # self.copy_timer_button.setText(_translate("PreimageWindow", "定时拷贝"))
        self.stop_Button.setText(_translate("PreimageWindow", "停止拷贝"))

        self.savingModeLabel.setText(_translate("PreimageWindow", "存储方式"))
        self.saveset_comboBox.setItemText(0, _translate("PreimageWindow", "按日期存储"))
        self.saveset_comboBox.setItemText(1, _translate("PreimageWindow", "按料号存储"))
        self.saveset_comboBox.setItemText(2, _translate("PreimageWindow", "按批量存储(从0开始)"))
        self.saveset_comboBox.setItemText(3, _translate("PreimageWindow", "按批量存储"))
        self.saveset_comboBox.setItemText(4, _translate("PreimageWindow", "手动机存储"))

        self.startNumLabel.setText(_translate("PreimageWindow", "起始板号"))
        self.endNumLabel.setText(_translate("PreimageWindow", "结束板号"))
        self.maxNumLabel.setText(_translate("PreimageWindow", "最大板数"))

        # 读取文本并设置到label
        with open("readme.txt", "r", encoding="utf-8") as file:
            annotation = file.read().strip()
            self.label_10.setText(annotation)
        self.label_10.setStyleSheet('color:blue')

    @staticmethod
    def validate_BN(edit, field_name):
        text = edit.text()
        if not text:
            raise Exception(f'请输入{field_name}')
        try:
            value = int(text)
            if not (settings.min_BN <= value <= settings.max_BN):
                raise Exception(f'{field_name}必须在{settings.min_BN}到{settings.max_BN}之间')
        except ValueError:
            raise Exception(f'无效的{field_name}')

    @staticmethod
    def validate_folder(folder_edit, field_name):
        text = str(folder_edit.text())
        if not os.path.exists(text):
            raise Exception(f'{field_name}不存在')

    def validate_inputs_by_num(self):
        if self.saveset_comboBox.currentIndex() == 4:
            raise Exception('手动机存储不支持按板号拷贝')
        self.validate_BN(self.startEdit, self.startNumLabel.text())
        self.validate_BN(self.endEdit, self.endNumLabel.text())
        self.validate_folder(self.carEdit, self.carLabel.text())
        self.validate_folder(self.jobEdit, self.jobLabel.text())
        self.validate_folder(self.saveEdit, self.saveLabel.text())
        if self.startEdit.text() > self.endEdit.text():
            raise Exception(f'{self.startNumLabel.text()}必须小于等于{self.endNumLabel.text()}')

    def validate_inputs_by_date(self):
        self.validate_folder(self.carEdit, self.carLabel.text())
        self.validate_folder(self.jobEdit, self.jobLabel.text())
        self.validate_folder(self.saveEdit, self.saveLabel.text())
        self.validate_BN(self.maxEdit, self.maxNumLabel.text())

    def setEnable(self, enabled):
        # Enable or disable all widgets
        for widget in [
            self.carEdit, self.carButton, self.jobEdit, self.jobButton,
            self.studyEdit, self.studyButton, self.logEdit, self.logButton,
            self.saveEdit, self.saveButton,
            self.dateEdit, self.dateEndEdit, self.saveset_comboBox,
            self.startEdit, self.endEdit, self.maxEdit, self.copy_aidataButton,
            self.copyMode_comboBox,
            self.aoiCheckBox, self.aviCheckBox, self.machineType_comboBox,
        ]:
            widget.setEnabled(enabled)
        self.stop_Button.setEnabled(not enabled)
