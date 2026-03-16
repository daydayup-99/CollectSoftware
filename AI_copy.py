import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import PyQt5
import PyQt5.QtGui
import PyQt5.QtWidgets
import requests

import copyUI
import threading
import datetime
from PyQt5.QtCore import QDate, QTimer
import configparser

import save_modes
from logging_handler import QTextBrowerHandler, logger
from settings import MES_URL
from utils import format_date, handle_file_errors, _make_dir


# pyinstaller AI_copy.spec

class Copy(PyQt5.QtWidgets.QMainWindow, copyUI.Ui_PreimageWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setupUi(self)
            self.setWindowTitle(u'AI资料拷贝')
            self.setWindowIcon(PyQt5.QtGui.QIcon(r'ai.ico'))
            _make_dir("setting")
            self.config_path = './setting/config.ini'
            # 创建一个 QTextEdit 用于显示日志信息
            self.cwd = os.getcwd()
            self.tid = 0
            self.setEnable(True)

            # 初始化mes的拷贝信息
            self.mes_copy_data = None

        except Exception as e:
            logger.error(f'界面初始化失败, {e}')
        # 设置日志记录器
        self.setup_logging()

        # 加载配置
        self.config = self.load_config()
        self.default_config = self.config['DEFAULT']
        self._running = False
        self._run_timer = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_copy)

        # 链接按钮
        self.connect_button()
        self.warning_browser.verticalScrollBar().valueChanged.connect(self.on_warning_scrollbar_value_changed)

    # 按钮链接
    def connect_button(self):
        self.carButton.clicked.connect(lambda: self.open_dir(edit_components=self.carEdit))
        self.jobButton.clicked.connect(lambda: self.open_dir(edit_components=self.jobEdit))
        self.saveButton.clicked.connect(lambda: self.open_dir(edit_components=self.saveEdit))
        self.studyButton.clicked.connect(lambda: self.open_dir(edit_components=self.studyEdit))
        self.logButton.clicked.connect(lambda: self.open_dir(edit_components=self.logEdit))
        # 开始拷贝
        self.copy_aidataButton.clicked.connect(self.start_copy_thread)
        # 停止拷贝
        self.stop_Button.clicked.connect(self.stop_copy_thread)

    def load_config(self):
        logger.info(f'尝试加载配置文件: {self.config_path}')
        config = configparser.ConfigParser()
        try:
            config.read(self.config_path)
            logger.info('配置文件加载成功')
            self._load_config_values(config)
        except configparser.Error as e:
            logger.error(f'读取配置文件时出错: {self.config_path} - {e}')
        except Exception as e:
            logger.error(f'未预见的错误: {e}')
        return config

    def _load_config_values(self, config):
        # aoicar路径
        self.carEdit.setText(config['DEFAULT'].get('carPath', ''))
        # 保存路径
        self.saveEdit.setText(config['DEFAULT'].get('savePath', ''))
        # std路径
        self.studyEdit.setText(config['DEFAULT'].get('studyPath', ''))
        # log路径
        self.logEdit.setText(config['DEFAULT'].get('logPath', ''))
        # 存储方式
        self.saveset_comboBox.setCurrentIndex(int(config['DEFAULT'].get('saveMode', '0')))
        # 开始日期
        self.dateEdit.setDate(
            QDate.fromString(config['DEFAULT'].get('startDate', '').replace('/', '-'), 'yyyy-MM-d'))
        # 开始板号
        self.startEdit.setText(config['DEFAULT'].get('startNum', '0'))
        # 结束板号
        self.endEdit.setText(config['DEFAULT'].get('endNum', '0'))
        # 结束日期
        self.dateEndEdit.setDate(
            QDate.fromString(config['DEFAULT'].get('endDate', '').replace('/', '-'), 'yyyy-MM-d'))
        # aoijob路径
        self.jobEdit.setText(config['DEFAULT'].get('jobPath', ''))
        # 最大板数
        self.maxEdit.setText(config['DEFAULT'].get('maxNum', '0'))

        # 拷贝方式
        self.copyMode_comboBox.setCurrentIndex(int(config['DEFAULT'].get('copyMode', '0')))
        # AOI和AVI状态（默认都勾选）
        self.aoiCheckBox.setChecked(config['DEFAULT'].get('useAOI', 'True').lower() == 'true')
        self.aviCheckBox.setChecked(config['DEFAULT'].get('useAVI', 'False').lower() == 'true')

    def setup_logging(self):
        logger.handlers = []
        info_error_handler = QTextBrowerHandler(self.log_output, level=logging.INFO)
        warning_handler = QTextBrowerHandler(self.warning_browser, level=logging.WARNING)
        info_error_handler.addFilter(self._create_filter(logging.INFO, logging.ERROR))
        warning_handler.addFilter(self._create_filter(logging.WARNING))
        logger.addHandler(info_error_handler)
        logger.addHandler(warning_handler)
        _make_dir('./copyLog')
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        file_handler = TimedRotatingFileHandler(f'./copyLog/{current_date}.log', when='midnight', interval=1)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.suffix = "%Y%m%d.log"
        logger.addHandler(file_handler)

    @staticmethod
    def _create_filter(*levels):
        class LevelFilter(logging.Filter):
            def filter(self, record):
                return record.levelno in levels

        return LevelFilter()

    def clear_log(self):
        self.log_output.clear()
        self.warning_browser.clear()

    def on_warning_scrollbar_value_changed(self, value):
        # TODO: 需要清除警告框的
        if value >= self.warning_browser.verticalScrollBar().maximum() - 10:
            self.warning_browser.clear()

    def _choose_save_mode_cls(self, date):
        save_set = int(self.default_config.get('saveMode', '0'))
        dirs = ['carPath', 'jobPath', 'savePath', 'studyPath', 'logPath']
        car_dir, job_dir, save_dir, study_dir, log_dir = (self.default_config.get(key, '') for key in dirs)
        use_aoi = self.aoiCheckBox.isChecked()
        use_avi = self.aviCheckBox.isChecked()
        machine_type = self.machineType_comboBox.currentText()
        save_cls_map = {
            0: save_modes.DateSaveMode,
            1: save_modes.JobSaveMode,
            2: save_modes.Batch0SaveMode,
            3: save_modes.BatchSaveMode,
            4: save_modes.ManualSaveMode
        }
        save_cls = save_cls_map.get(save_set, save_modes.DateSaveMode)
        save_cls_obj = save_cls(car_dir, job_dir, save_dir, study_dir, log_dir, date, use_aoi=use_aoi, use_avi=use_avi, machine_type=machine_type)
        return save_cls_obj

    @handle_file_errors
    def _save_setting(self):
        config_data = {
            'carPath': str(self.carEdit.text()),
            'jobPath': str(self.jobEdit.text()),
            'studyPath': str(self.studyEdit.text()),
            'logPath': str(self.logEdit.text()),
            'savePath': str(self.saveEdit.text()),
            'saveMode': str(self.saveset_comboBox.currentIndex()),
            'startDate': format_date(self.dateEdit.text()),
            'endDate': format_date(self.dateEndEdit.text()),
            'startNum': int(self.startEdit.text()),
            'endNum': int(self.endEdit.text()),
            'maxNum': str(self.maxEdit.text()),
            'copyMode': str(self.copyMode_comboBox.currentIndex()),
            'useAOI': str(self.aoiCheckBox.isChecked()),
            'useAVI': str(self.aviCheckBox.isChecked()),
        }
        self.config['DEFAULT'] = config_data
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def open_dir(self, edit_components):
        try:
            dir_path = Path(PyQt5.QtWidgets.QFileDialog.getExistingDirectory(self, "选取文件夹", self.cwd))  # 起始路径
            edit_components.setText(str(dir_path))
        except Exception as e:
            print('获取文件夹路径失败', e)

    def start_copy_thread(self):
        self._save_setting()
        self.progress_updated.emit(0)
        self.setEnable(False)
        self._running = True

        copy_set = int(self.default_config.get('copyMode', '0'))
        copy_func_map = {
            0: self._copy_by_date,
            1: self._copy_by_num,
            2: self.start_copy_timer,
            3: self._copy_by_mes,
            4: self._copy_by_avi
        }
        copy_func = copy_func_map.get(copy_set, save_modes.DateSaveMode)
        t = threading.Thread(target=copy_func, name='startCopy')
        t.setDaemon(True)
        t.start()
        self.tid = t.ident

    def stop_copy_thread(self):
        self.setEnable(True)
        self._running = False
        self._run_timer = False
        self.timer.stop()  # 停止定时器

    def _execute_copy(self, get_items_func, process_item_func, item_label):
        """
        通用的拷贝方法。
        :param get_items_func: 获取需要拷贝的项目列表（如板号列表或日期列表）的函数
        :param process_item_func: 对单个项目进行处理的函数
        :param item_label: 项目类型（如 "板号" 或 "日期"），用于日志记录
        """
        try:
            def is_running():
                return self._running

            def log_item_finish(row):
                if isinstance(row, dict):
                    logger.info(f'{row["date"]} 拷贝完成!')
                else:
                    logger.info(f'{row} 拷贝完成!')

            logger.info(f'按{item_label}拷贝开始...')

            items = get_items_func()
            total_items = len(items)

            if not items:
                logger.warning(f'没有找到需要拷贝的{item_label}！')
                return

            for index, item in enumerate(items):
                if not is_running():
                    raise Exception('已停止')

                process_item_func(item, is_running)
                progress = int((index + 1) / total_items * 100)
                self.progress_updated.emit(progress)
                log_item_finish(item)

            logger.info(f'按{item_label}拷贝已完成！')

        except Exception as e:
            logger.error(e)

        self.setEnable(True)

    def _copy_by_mes(self):
        try:
            def read_data():
                """
                :return: [{'date': date1, 'pcbnos': [...]},
                            {'date': date2, 'pcbnos': [...]},
                            ]
                """
                try:
                    response = requests.get(f'http://{MES_URL}/get_copy_json', timeout=(3, 10))
                    if response.status_code == 200:
                        data = response.json()['data']
                    elif response.status_code == 404:
                        raise Exception("url不存在，请检查MES系统是否启动或可用")
                    elif response.status_code == 400:
                        error = response.json().get('error', '未向MES系统中请求到拷贝配置，请从MES系统分析报告里导出拷贝！')
                        raise Exception(error)
                    else:
                        raise Exception("请检查MES系统是否启动或可用")
                except requests.exceptions.Timeout:
                    raise Exception("请求超时，请检查MES系统是否启动或可用")
                except Exception:
                    raise Exception("连接mes系统失败，请检查MES系统是否启动或可用")
                self.mes_copy_data = data
                return data

            def get_dates():
                data = read_data()
                return data

            def process_date(date, is_running_callback, **kwargs):
                date_nums = date.get('pcbnos', [])
                copy_mode_cls = self._choose_save_mode_cls(date["date"])
                logger.info(f'日期 {date["date"]} 开始拷贝!')
                if not date_nums:
                    logger.warning(f'mes系统下关于日期{date}没有存储板号信息')
                    return
                return copy_mode_cls.copy(date_nums,
                                          is_running_callback,
                                          max_num=int(self.default_config.get('maxNum', '0')))

            self._execute_copy(get_dates, process_date, "日期")
        except Exception as e:
            logger.error(e)
            self.setEnable(True)
        self._running = False

    def _copy_by_date(self):
        try:
            self.validate_inputs_by_date()
            self._date_copy()
        except Exception as e:
            logger.error(e)
            self.setEnable(True)
        self._running = False
        if self._run_timer:
            return

    def _date_copy(self):
        def get_dates():
            start_date = self.default_config.get('startDate', '20000102').replace('-', '')
            end_date = self.default_config.get('endDate', '20000101').replace('-', '')
            if int(start_date) > int(end_date):
                raise Exception('开始日期在结束日期之后，请重新输入！')
            return self._get_dates_interval(start_date, end_date)

        def process_date(date, is_running_callback, **kwargs):
            copy_mode_cls = self._choose_save_mode_cls(date)
            logger.info(f'日期 {date} 开始拷贝!')
            date_nums = copy_mode_cls.get_date_num_list(self.saveset_comboBox.currentText())
            if not date_nums:
                logger.warning(f'请检查{copy_mode_cls.car_date_dir}文件夹下是否有数据')
                return
            return copy_mode_cls.copy(date_nums,
                                      is_running_callback,
                                      max_num=int(self.default_config.get('maxNum', '0')))

        self._execute_copy(get_dates, process_date, "日期")

    @staticmethod
    def _get_dates_interval(start_date, end_date):
        start_year, start_month, start_day = int(start_date[:4]), int(start_date[4:6]), int(start_date[6:])
        end_year, end_month, end_day = int(end_date[:4]), int(end_date[4:6]), int(end_date[6:])
        d1 = datetime.date(start_year, start_month, start_day)
        d2 = datetime.date(end_year, end_month, end_day)
        return [(d1 + datetime.timedelta(days=x)).strftime('%Y%m%d') for x in range((d2 - d1).days + 1)]

    def _copy_log_path(self, start_date, end_date):
        """
        拷贝指定日期范围内的日志文件
        :param start_date: 开始日期 (QDate对象)
        :param end_date: 结束日期 (QDate对象)
        """
        try:
            log_dir = self.logEdit.text()
            if not log_dir or not os.path.exists(log_dir):
                logger.warning(f'日志路径不存在: {log_dir}')
                return

            # 确保日期是QDate对象
            if isinstance(start_date, str):
                start_date = QDate.fromString(start_date, 'yyyy-MM-dd')
            if isinstance(end_date, str):
                end_date = QDate.fromString(end_date, 'yyyy-MM-dd')

            # 获取目标日志目录
            save_cls_obj = self._choose_save_mode_cls(start_date.toString('yyyyMMdd'))
            target_dir = save_cls_obj.save_log_dir

            # 遍历源日志目录
            if os.path.isdir(log_dir):
                for file_name in os.listdir(log_dir):
                    if not file_name.endswith('.txt'):
                        continue
                    try:
                        # 文件格式: YYYY_M_D.txt
                        date_str = file_name.replace('.txt', '')
                        # 将 YYYY_M_D 转换为 datetime
                        date_parts = date_str.split('_')
                        if len(date_parts) != 3:
                            continue
                        year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                        file_date = QDate(year, month, day)

                        # 检查日期是否在范围内
                        if start_date <= file_date <= end_date:
                            source_file = os.path.join(log_dir, file_name)
                            target_file = os.path.join(target_dir, file_name)
                            if os.path.exists(target_file) is False:
                                from utils import copy_with_error_handling
                                copy_with_error_handling(source_file, target_file)
                                logger.info(f'已复制日志文件: {file_name}')
                    except Exception as e:
                        logger.warning(f'处理日志文件 {file_name} 时出错: {e}')
                        continue
        except Exception as e:
            logger.error(f'拷贝日志文件时出错: {e}')

    def _copy_by_num(self):
        try:
            start_date = self.default_config.get('startDate', QDate.currentDate())
            end_date = self.default_config.get('enddate', QDate.currentDate())
            self._copy_log_path(start_date, end_date)

            def get_nums():
                start_num = int(self.default_config.get('startNum', '-1'))
                end_num = int(self.default_config.get('endNum', '-2'))
                return list(range(start_num, end_num + 1))

            def process_num(num, is_running_callback, *args, **kwargs):
                date = self.default_config.get('startDate', '20000101').replace('-', '')
                save_cls_obj = self._choose_save_mode_cls(date)
                logger.info(f'板号 {num} 开始拷贝!')
                save_cls_obj.copy([num], is_running_callback, by_date=False)

            self._execute_copy(get_nums, process_num, "板号")
        except Exception as e:
            logger.error(e)
            self.setEnable(True)

    def _copy_by_avi(self):
        try:
            selected_batch_numbers = self.selected_batch_numbers
            if not selected_batch_numbers:
                logger.warning('请先选择批次号')
                self.setEnable(True)
                return
            max_pl = int(self.maxPlNumEdit.text())
            logger.info(f'选择的料号: {", ".join(selected_batch_numbers)}')
            start_date = self.default_config.get('startDate', QDate.currentDate().addDays(-7).toString('yyyyMMdd')).replace('-', '')
            end_date = self.default_config.get('enddate', QDate.currentDate().toString('yyyyMMdd')).replace('-', '')
            car_path = self.carEdit.text()
            def get_nums():
                valid_date_path = []
                for job in selected_batch_numbers:
                    job_path = os.path.join(car_path, job)
                    if not os.path.exists(job_path):
                        logger.warning(f'料号路径不存在: {job_path}')
                        continue
                    if os.path.isdir(job_path):
                        pl_count = 0
                        for pl in os.listdir(job_path):
                            pl_path = os.path.join(job_path, pl)
                            if os.path.isdir(pl_path):
                                if pl == 'AiTestErr':
                                    valid_date_path.append(pl_path)
                                elif pl_count < max_pl:
                                    modify_time = os.path.getmtime(pl_path)
                                    modify_date = datetime.datetime.fromtimestamp(modify_time).strftime('%Y%m%d')
                                    if start_date <= modify_date <= end_date:
                                        valid_date_path.append(pl_path)
                                        pl_count += 1
                return valid_date_path
            # lst = get_nums()
            # if not lst:
            #     logger.warning(f'在日期范围 {start_date} 至 {end_date} 内没有找到符合条件的批量')
            #     self.setEnable(True)
            #     return
            # logger.info(f'共找到 {len(lst)} 个符合条件日期的批量')

            def process_num(num, is_running_callback, *args, **kwargs):
                save_cls_obj = self._choose_save_mode_cls(start_date)
                logger.info(f'料号 {num} 开始拷贝!')
                save_cls_obj.copyAVI([num], is_running_callback)

            self._execute_copy(get_nums, process_num, "板号")
        except Exception as e:
            logger.error(e)
            self.setEnable(True)

    def start_copy_timer(self):
        # 设置定时器
        logger.info('定时开启')
        self._run_timer = True
        self.run_copy(first_copy=True)
        self.timer.start(1000 * 60 * 60)

    def run_copy(self, first_copy=False):
        if self._running:
            return
        logger.info('开始定时任务')
        current_date = QDate.currentDate()
        if not first_copy:
            self.dateEdit.setDate(current_date)
        self.dateEndEdit.setDate(current_date)
        self._copy_by_date()


if __name__ == '__main__':
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    if os.path.exists("style.qss"):
        with open("style.qss", "r", encoding="utf-8") as f:
            style = f.read()
            app.setStyleSheet(style)
    md = Copy()
    md.show()
    sys.exit(app.exec_())
