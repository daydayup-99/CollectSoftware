from PyQt5.QtWidgets import QLabel
import os.path
import json
import logging

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

import settings
from progress_bar import CustomProgressBar

logger = logging.getLogger(__name__)


class CheckableComboBox(QtWidgets.QComboBox):
    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QtGui.QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)  
    
    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)
        self.updateText()
    
    def updateText(self):
        checked_items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == QtCore.Qt.Checked:
                checked_items.append(item.text())
        self.setEditText(', '.join(checked_items) if checked_items else '')
    
    def addItems(self, items):
        for text in items:
            item = QtGui.QStandardItem(text)
            item.setCheckState(QtCore.Qt.Unchecked)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            self.model().appendRow(item)
    
    def clear(self):
        self.model().clear()
        self.setEditText('')
    
    def addCheckableItem(self, text):
        item = QtGui.QStandardItem(text)
        item.setCheckState(QtCore.Qt.Unchecked)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.model().appendRow(item)
    
    def get_selected_items(self):
        checked_items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == QtCore.Qt.Checked:
                checked_items.append(item.text())
        return checked_items


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

        self.label = QtWidgets.QLabel("请选择需要的文件夹(已按时间由新到旧排序)：")
        layout.addWidget(self.label)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        self.container = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container)
        self.scroll_area.setWidget(self.container)

        self.checkboxes = []
        if os.path.exists(self.car_path):
            folders = [f for f in os.listdir(self.car_path) if os.path.isdir(os.path.join(self.car_path, f))]
            self.all_folders = sorted(
                folders,
                key=lambda f: os.path.getmtime(os.path.join(self.car_path, f)),
                reverse=True  # 由新到旧
            )
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
        for folder in filtered_folders:
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
        self.progress_updated.connect(self.update_progress)
        self.selected_batch_numbers = []
        # 初始化网络管理器
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_machine_data_received)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def setupUi(self, PreimageWindow):
        PreimageWindow.setObjectName("PreimageWindow")
        PreimageWindow.resize(1600, 850)
        self.centralwidget = QtWidgets.QWidget(PreimageWindow)
        self.centralwidget.setObjectName("centralwidget")

        # 创建主布局
        main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 左侧控制面板
        control_widget = QtWidgets.QWidget()
        control_widget.setMaximumWidth(650)  # 设置最大宽度，限制左侧界面大小
        control_layout = QtWidgets.QVBoxLayout(control_widget)
        control_layout.setSpacing(15)

        # AOI和AVI选择区域（在Tab外面，顶部）
        type_group = QtWidgets.QGroupBox("设备类型")
        type_layout = QtWidgets.QHBoxLayout(type_group)
        type_layout.setSpacing(20)
        
        self.aoiLabel = QtWidgets.QLabel("AOI")
        self.aoiLabel.setObjectName("aoiLabel")
        self.aoiCheckBox = QtWidgets.QCheckBox()
        self.aoiCheckBox.setObjectName("aoiCheckBox")
        
        self.aviLabel = QtWidgets.QLabel("AVI")
        self.aviLabel.setObjectName("aviLabel")
        self.aviCheckBox = QtWidgets.QCheckBox()
        self.aviCheckBox.setObjectName("aviCheckBox")
        
        type_layout.addWidget(self.aoiLabel)
        type_layout.addWidget(self.aoiCheckBox)
        type_layout.addStretch()
        type_layout.addWidget(self.aviLabel)
        type_layout.addWidget(self.aviCheckBox)
        type_layout.addStretch()
        
        control_layout.addWidget(type_group)

        # 创建Tab Widget
        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.setObjectName("tabWidget")
        
        # Tab 1: 按资料收集
        self.tab_manual = QtWidgets.QWidget()
        self.tab_manual.setObjectName("tab_manual")
        tab_manual_layout = QtWidgets.QVBoxLayout(self.tab_manual)
        tab_manual_layout.setSpacing(15)

        # 路径配置区域
        paths_group = QtWidgets.QGroupBox("路径配置")
        paths_layout = QtWidgets.QGridLayout(paths_group)
        paths_layout.setSpacing(10)

        # CAR路径
        self.carLabel = QtWidgets.QLabel("CAR路径")
        self.carLabel.setObjectName("carLabel")
        self.carEdit = QtWidgets.QLineEdit()
        self.carEdit.setObjectName("carEdit")
        self.carButton = QtWidgets.QPushButton("...")
        self.carButton.setObjectName("carButton")
        paths_layout.addWidget(self.carLabel, 0, 0)
        paths_layout.addWidget(self.carEdit, 0, 1)
        paths_layout.addWidget(self.carButton, 0, 2)

        # JOB路径
        self.jobLabel = QtWidgets.QLabel("JOB路径")
        self.jobLabel.setObjectName("jobLabel")
        self.jobEdit = QtWidgets.QLineEdit()
        self.jobEdit.setObjectName("jobEdit")
        self.jobButton = QtWidgets.QPushButton("...")
        self.jobButton.setObjectName("jobButton")
        paths_layout.addWidget(self.jobLabel, 1, 0)
        paths_layout.addWidget(self.jobEdit, 1, 1)
        paths_layout.addWidget(self.jobButton, 1, 2)

        # STD路径
        self.studyLabel = QtWidgets.QLabel("STD路径")
        self.studyLabel.setObjectName("studyLabel")
        self.studyEdit = QtWidgets.QLineEdit()
        self.studyEdit.setObjectName("studyEdit")
        self.studyButton = QtWidgets.QPushButton("...")
        self.studyButton.setObjectName("studyButton")
        paths_layout.addWidget(self.studyLabel, 2, 0)
        paths_layout.addWidget(self.studyEdit, 2, 1)
        paths_layout.addWidget(self.studyButton, 2, 2)

        # LOG路径
        self.logLabel = QtWidgets.QLabel("LOG路径")
        self.logLabel.setObjectName("logLabel")
        self.logEdit = QtWidgets.QLineEdit()
        self.logEdit.setObjectName("logEdit")
        self.logButton = QtWidgets.QPushButton("...")
        self.logButton.setObjectName("logButton")
        paths_layout.addWidget(self.logLabel, 3, 0)
        paths_layout.addWidget(self.logEdit, 3, 1)
        paths_layout.addWidget(self.logButton, 3, 2)

        paths_layout.setColumnStretch(1, 1)
        tab_manual_layout.addWidget(paths_group)

        # 参数设置区域
        params_group = QtWidgets.QGroupBox("参数设置")
        params_layout = QtWidgets.QGridLayout(params_group)
        params_layout.setSpacing(10)

        # 存储方式
        self.savingModeLabel = QtWidgets.QLabel("存储方式")
        self.savingModeLabel.setObjectName("savingModeLabel")
        self.saveset_comboBox = QtWidgets.QComboBox()
        self.saveset_comboBox.setObjectName("saveset_comboBox")
        self.saveset_comboBox.addItems(["按日期存储", "按料号存储", "按批量存储(从0开始)", "按批量存储", "手动机存储"])
        
        # 拷贝方式
        self.copyModelLabel = QtWidgets.QLabel("拷贝方式")
        self.copyModelLabel.setObjectName("copyModelLabel")
        self.copyMode_comboBox = QtWidgets.QComboBox()
        self.copyMode_comboBox.addItems(["按日期拷贝", "按板号拷贝", "定时拷贝", "一键拷贝", "离线机拷贝"])
        
        params_layout.addWidget(self.savingModeLabel, 0, 0)
        params_layout.addWidget(self.saveset_comboBox, 0, 1)
        params_layout.addWidget(self.copyModelLabel, 0, 2)
        params_layout.addWidget(self.copyMode_comboBox, 0, 3)

        # 最大批次数
        self.maxPlNumLabel = QtWidgets.QLabel("最大批次数")
        self.maxPlNumLabel.setObjectName("maxPlNumLabel")
        self.maxPlNumEdit = QtWidgets.QLineEdit()
        self.maxPlNumEdit.setObjectName("maxPlNumEdit")
        self.maxPlNumEdit.setText(str(5))
        
        # 机器类型
        self.machineTypeLabel = QtWidgets.QLabel("机器类型")
        self.machineTypeLabel.setObjectName("machineTypeLabel")
        self.machineType_comboBox = QtWidgets.QComboBox()
        self.machineType_comboBox.setObjectName("machineType_comboBox")
        self.machineType_comboBox.addItems(["在线机", "离线机"])
        self.machineType_comboBox.setEnabled(False)
        
        params_layout.addWidget(self.maxPlNumLabel, 2, 0)
        params_layout.addWidget(self.maxPlNumEdit, 2, 1)
        params_layout.addWidget(self.machineTypeLabel, 2, 2)
        params_layout.addWidget(self.machineType_comboBox, 2, 3)

        # 板号范围
        self.startNumLabel = QtWidgets.QLabel("起始板号")
        self.startNumLabel.setObjectName("startNumLabel")
        self.startEdit = QtWidgets.QLineEdit()
        self.startEdit.setObjectName("startEdit")
        
        self.endNumLabel = QtWidgets.QLabel("结束板号")
        self.endNumLabel.setObjectName("endNumLabel")
        self.endEdit = QtWidgets.QLineEdit()
        self.endEdit.setObjectName("endEdit")
        
        self.maxNumLabel = QtWidgets.QLabel("最大板数")
        self.maxNumLabel.setObjectName("maxNumLabel")
        self.maxEdit = QtWidgets.QLineEdit()
        self.maxEdit.setObjectName("maxEdit")
        
        params_layout.addWidget(self.startNumLabel, 3, 0)
        params_layout.addWidget(self.startEdit, 3, 1)
        params_layout.addWidget(self.endNumLabel, 3, 2)
        params_layout.addWidget(self.endEdit, 3, 3)
        params_layout.addWidget(self.maxNumLabel, 3, 4)
        params_layout.addWidget(self.maxEdit, 3, 5)
        
        tab_manual_layout.addWidget(params_group)

        # 将Tab 1添加到Tab Widget
        self.tabWidget.addTab(self.tab_manual, "按资料收集")
        
        # Tab 2: 按Mes收集
        self.tab_mes = QtWidgets.QWidget()
        self.tab_mes.setObjectName("tab_mes")
        tab_mes_layout = QtWidgets.QVBoxLayout(self.tab_mes)
        tab_mes_layout.setSpacing(15)
        
        # MES相关配置区域
        mes_group = QtWidgets.QGroupBox("MES配置")
        mes_layout = QtWidgets.QVBoxLayout(mes_group)
        mes_layout.setSpacing(10)
        
        # MES IP地址
        mes_ip_layout = QtWidgets.QHBoxLayout()
        mes_ip_label = QtWidgets.QLabel("MES IP地址")
        self.mes_ip_edit = QtWidgets.QLineEdit()
        self.mes_ip_edit.setText("127.0.0.1")
        self.mes_ip_edit.textChanged.connect(self.on_mes_ip_changed)  # IP改变时自动获取机台数据
        mes_ip_layout.addWidget(mes_ip_label)
        mes_ip_layout.addWidget(self.mes_ip_edit)
        mes_layout.addLayout(mes_ip_layout)
        
        # 机台号选择和全选
        machine_layout = QtWidgets.QHBoxLayout()
        machine_label: QLabel = QtWidgets.QLabel("机台号")
        
        self.machine_combo = CheckableComboBox()
        self.machine_combo.setObjectName("machine_combo")
        self.machine_combo.setMinimumWidth(200)
        self.select_all_machines = QtWidgets.QCheckBox("全选")
        self.select_all_machines.setObjectName("select_all_machines")

        machine_layout.addWidget(machine_label)
        machine_layout.addWidget(self.machine_combo, 1)  # 设置拉伸因子，让下拉框占满剩余空间
        machine_layout.addWidget(self.select_all_machines)
        mes_layout.addLayout(machine_layout)
        tab_mes_layout.addWidget(mes_group)
        
        # 收集功能配置区域
        collect_group = QtWidgets.QGroupBox("收集功能配置")
        collect_layout = QtWidgets.QVBoxLayout(collect_group)
        collect_layout.setSpacing(10)
        self.collect_mode_group = QtWidgets.QButtonGroup(self)
        self.collect_mode_group.setExclusive(True)  # 设置互斥
        
        mode_layout = QtWidgets.QHBoxLayout()
        self.ai_report_checkbox = QtWidgets.QCheckBox("AI后报点小于")
        self.ai_report_checkbox.setObjectName("ai_report")
        self.collect_mode_group.addButton(self.ai_report_checkbox)
        
        self.ai_report_value = QtWidgets.QLineEdit()
        self.ai_report_value.setObjectName("ai_report_value")
        self.ai_report_value.setFixedWidth(60)
        self.ai_report_value.setText("0")  
        
        self.filter_rate_checkbox = QtWidgets.QCheckBox("料号过滤率小于")
        self.filter_rate_checkbox.setObjectName("filter_rate")
        self.collect_mode_group.addButton(self.filter_rate_checkbox)
        
        self.filter_rate_value = QtWidgets.QLineEdit()
        self.filter_rate_value.setObjectName("filter_rate_value")
        self.filter_rate_value.setFixedWidth(60)
        self.filter_rate_value.setText("0")  
        
        # # 触发收集模式
        # self.trigger_collect_checkbox = QtWidgets.QCheckBox("触发收集")
        # self.trigger_collect_checkbox.setObjectName("trigger_collect")
        # self.collect_mode_group.addButton(self.trigger_collect_checkbox)
        
        # # 自动收集模式
        # self.auto_collect_checkbox = QtWidgets.QCheckBox("自动收集")
        # self.auto_collect_checkbox.setObjectName("auto_collect")
        # self.collect_mode_group.addButton(self.auto_collect_checkbox)
        
        mode_layout.addWidget(self.ai_report_checkbox)
        mode_layout.addWidget(self.ai_report_value)
        
        mode_layout.addWidget(self.filter_rate_checkbox)
        mode_layout.addWidget(self.filter_rate_value)
        
        # mode_layout.addWidget(self.timer_collect_checkbox)
        # mode_layout.addWidget(self.trigger_collect_checkbox)
        # mode_layout.addWidget(self.auto_collect_checkbox)
        mode_layout.addStretch()
        
        collect_layout.addLayout(mode_layout)
        
        tab_mes_layout.addWidget(collect_group)
        tab_mes_layout.addStretch()
        
        # 将Tab 2添加到Tab Widget
        self.tabWidget.addTab(self.tab_mes, "按Mes收集")
        
        # 将Tab Widget添加到控制面板
        control_layout.addWidget(self.tabWidget)

        # 公共操作区域
        date_action_group = QtWidgets.QGroupBox()
        date_action_layout = QtWidgets.QVBoxLayout(date_action_group)
        date_action_layout.setSpacing(15)
        
        press_save_layout = QtWidgets.QHBoxLayout()
        # 压缩包名称
        self.pressCheckBox = QtWidgets.QCheckBox("压缩包名")
        self.pressCheckBox.setObjectName("pressCheckBox")
        self.pressEdit = QtWidgets.QLineEdit()
        self.pressEdit.setObjectName("pressEdit")
        self.pressEdit.setFixedWidth(120)  # 设置合适宽度
        
        # 保存路径
        self.saveLabel = QtWidgets.QLabel("保存路径")
        self.saveLabel.setObjectName("saveLabel")
        self.saveEdit = QtWidgets.QLineEdit()
        self.saveEdit.setObjectName("saveEdit")
        self.saveButton = QtWidgets.QPushButton("...")
        self.saveButton.setObjectName("saveButton")
        
        press_save_layout.addWidget(self.pressCheckBox)
        press_save_layout.addWidget(self.pressEdit)
        press_save_layout.addSpacing(10)  # 添加间距
        press_save_layout.addWidget(self.saveLabel)
        press_save_layout.addWidget(self.saveEdit, 1)  # 设置拉伸因子
        press_save_layout.addWidget(self.saveButton)
        
        date_action_layout.addLayout(press_save_layout)

        # 日期范围
        date_range_layout = QtWidgets.QHBoxLayout()
        self.date_label = QtWidgets.QLabel("开始时间")
        self.date_label.setObjectName("date_label")
        self.dateEdit = QtWidgets.QDateEdit()
        self.dateEdit.setObjectName("dateEdit")
        self.dateEdit.setMinimumWidth(150)
        
        self.dateEndLabel = QtWidgets.QLabel("结束时间")
        self.dateEndLabel.setObjectName("dateEndLabel")
        self.dateEndEdit = QtWidgets.QDateEdit()
        self.dateEndEdit.setObjectName("dateEndEdit")
        self.dateEndEdit.setMinimumWidth(150)
        
        date_range_layout.addWidget(self.date_label)
        date_range_layout.addWidget(self.dateEdit)
        date_range_layout.addWidget(self.dateEndLabel)
        date_range_layout.addWidget(self.dateEndEdit)
        date_range_layout.addStretch()
        date_action_layout.addLayout(date_range_layout)
        
        # 按钮区域
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        self.chooseJob_button = QtWidgets.QPushButton("料号选择")
        self.chooseJob_button.setObjectName("chooseJob_button")
        self.chooseJob_button.clicked.connect(self.chooseJob_button_clicked_handler)
        
        self.copy_aidataButton = QtWidgets.QPushButton("开始拷贝")
        self.copy_aidataButton.setObjectName("copy_aidataButton")
        self.copy_aidataButton.setMinimumHeight(40)
        
        self.stop_Button = QtWidgets.QPushButton("停止拷贝")
        self.stop_Button.setObjectName("stop_Button")
        self.stop_Button.setMinimumHeight(40)
        
        buttons_layout.addWidget(self.chooseJob_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.copy_aidataButton)
        buttons_layout.addWidget(self.stop_Button)
        
        date_action_layout.addLayout(buttons_layout)
        
        control_layout.addWidget(date_action_group)

        # 使用说明区域
        info_group = QtWidgets.QGroupBox("使用说明")
        info_layout = QtWidgets.QVBoxLayout(info_group)
        
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scroll_area")
        
        self.label_10 = QtWidgets.QLabel()
        self.label_10.setObjectName("label_10")
        self.label_10.setWordWrap(True)
        self.label_10.setAlignment(Qt.AlignTop)
        
        scroll_area.setWidget(self.label_10)
        info_layout.addWidget(scroll_area)
        
        control_layout.addWidget(info_group, 1)  # 设置拉伸因子
        
        main_layout.addWidget(control_widget)

        # 中间区域（进度条）
        progress_widget = QtWidgets.QWidget()
        progress_widget.setMaximumWidth(60)
        progress_layout = QtWidgets.QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = CustomProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setObjectName("progress_bar")
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_widget)

        # 右侧日志区域
        log_widget = QtWidgets.QWidget()
        log_layout = QtWidgets.QHBoxLayout(log_widget)
        log_layout.setSpacing(10)
        
        # 日志输出
        self.log_output = QtWidgets.QTextBrowser()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_output")
        self.log_output.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        
        # 警告输出
        self.warning_browser = QtWidgets.QTextBrowser()
        self.warning_browser.setObjectName("warning_browser")
        self.warning_browser.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        
        # 创建右键菜单
        self._create_context_menus()
        
        log_layout.addWidget(self.log_output, 1)
        log_layout.addWidget(self.warning_browser, 1)
        
        main_layout.addWidget(log_widget, 2)  # 设置较大的拉伸因子

        PreimageWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(PreimageWindow)
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
        self.select_all_machines.stateChanged.connect(self.on_select_all_machines)
        self.on_mes_ip_changed(self.mes_ip_edit.text())

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
    
    def on_select_all_machines(self, state):
        for i in range(self.machine_combo.model().rowCount()):
            item = self.machine_combo.model().item(i)
            if state == QtCore.Qt.Checked:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
        self.machine_combo.updateText()
    
    def on_mes_ip_changed(self, text):
        if not text or not self.is_valid_ip(text):
            return
        self.machine_combo.clear()
        self.get_machine_data_from_mes(text)
    
    def is_valid_ip(self, ip):
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False
    
    def get_machine_data_from_mes(self, mes_ip):
        try:
            port = 9099
            url_str = f"http://{mes_ip}:{port}/api/report/conds"
            url = QUrl(url_str)
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
            start_date = self.dateEdit.date().toString("yyyy-MM-dd") + " 00:00:00"
            end_date = self.dateEndEdit.date().toString("yyyy-MM-dd") + " 23:59:59"
            json_data = {
                "dates": [
                    start_date,
                    end_date
                ]
            }
            json_str = json.dumps(json_data)
            from PyQt5.QtCore import QByteArray
            data = QByteArray(json_str.encode('utf-8'))
            reply = self.network_manager.post(request, data)
            
        except Exception as e:
            print(f"获取机台数据失败: {e}")
    
    def on_machine_data_received(self, reply):
        if reply.error() == QNetworkReply.NoError:
            try:
                data = reply.readAll()
                json_str = str(data, 'utf-8')
                json_doc = json.loads(json_str)
                if 'data' in json_doc and isinstance(json_doc['data'], dict):
                    data_dict = json_doc['data']
                    if 'avis' in data_dict and isinstance(data_dict['avis'], list):
                        avis_list = data_dict['avis']
                        self.machine_combo.clear()
                        for avi in avis_list:
                            if isinstance(avi, str):
                                self.machine_combo.addCheckableItem(avi)
                        self.machine_combo.updateText()
                        print(f"成功加载 {len(avis_list)} 个机台")
            except Exception as e:
                print(f"解析机台数据失败: {e}")
        else:
            print(f"请求失败: {reply.errorString()}")
        reply.deleteLater()

    def chooseJob_button_clicked_handler(self):
        car_path = self.carEdit.text()
        dialog: JobSelectionDialog = JobSelectionDialog(car_path, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.selected_batch_numbers = dialog.get_selected_folders()

    def retranslateUi(self, PreimageWindow):
        _translate = QtCore.QCoreApplication.translate
        PreimageWindow.setWindowTitle(_translate("PreimageWindow", "AI数据拷贝工具"))
        
        # 读取readme.txt并设置到使用说明标签
        try:
            with open("readme.txt", "r", encoding="utf-8") as file:
                annotation = file.read().strip()
                self.label_10.setText(annotation)
            self.label_10.setStyleSheet('color:blue')
        except:
            self.label_10.setText("使用说明文件未找到")
            self.label_10.setStyleSheet('color:red')

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
            self.mes_ip_edit, self.machine_combo, self.select_all_machines,
        ]:
            widget.setEnabled(enabled)
        self.stop_Button.setEnabled(not enabled)

    def _create_context_menus(self):
        self.log_context_menu = QtWidgets.QMenu(self.log_output)
        clear_log_action = self.log_context_menu.addAction("清空日志")
        clear_log_action.triggered.connect(self.clear_log_browser)
        self.log_output.customContextMenuRequested.connect(
            lambda pos: self.log_context_menu.exec_(self.log_output.mapToGlobal(pos))
        )
        
        self.warning_context_menu = QtWidgets.QMenu(self.warning_browser)
        clear_warning_action = self.warning_context_menu.addAction("清空警告")
        clear_warning_action.triggered.connect(self.clear_warning_browser)
        self.warning_browser.customContextMenuRequested.connect(
            lambda pos: self.warning_context_menu.exec_(self.warning_browser.mapToGlobal(pos))
        )
    
    def clear_log_browser(self):
        self.log_output.clear()
        logger.info("日志已清空")
    
    def clear_warning_browser(self):
        self.warning_browser.clear()
        logger.info("警告信息已清空")
