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
from PyQt5.QtCore import QDate, QTimer, QDateTime
import json
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
        # AOI和AVI状态
        self.aoiCheckBox.setChecked(config['DEFAULT'].get('useAOI', 'True').lower() == 'true')
        self.aviCheckBox.setChecked(config['DEFAULT'].get('useAVI', 'False').lower() == 'true')
        # MES IP地址
        mes_ip = config['DEFAULT'].get('mesIp', '127.0.0.1')
        self.mes_ip_edit.setText(mes_ip)

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
            'mesIp': str(self.mes_ip_edit.text()), 
        }
        self.config['DEFAULT'] = config_data
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def open_dir(self, edit_components):
        try:
            current_path = str(edit_components.text()).strip()
            start_path = self.cwd
            if current_path and os.path.exists(current_path):
                start_path = current_path
            selected_dir = PyQt5.QtWidgets.QFileDialog.getExistingDirectory(self, "选取文件夹", start_path)
            if selected_dir:
                edit_components.setText(str(selected_dir))
        except Exception as e:
            print('获取文件夹路径失败', e)

    def start_copy_thread(self):
        self._save_setting()
        self.progress_updated.emit(0)
        self.setEnable(False)
        self._running = True

        # 根据当前选中的tab决定拷贝方式
        current_tab_index = self.tabWidget.currentIndex()
        
        if current_tab_index == 1:  # 第二个tab: 按MES收集
            # 使用MES收集逻辑
            collect_mode = self.get_mes_collect_mode()
            t = threading.Thread(target=self._copy_by_mes_new, args=(collect_mode,), name='startCopy')
        else:  # 第一个tab: 按资料收集（原来的逻辑）
            copy_set = int(self.default_config.get('copyMode', '0'))
            copy_func_map = {
                0: self._copy_by_date,
                1: self._copy_by_num,
                2: self.start_copy_timer,
                3: self._copy_by_mes,
                4: self._copy_by_avi
            }
            copy_func = copy_func_map.get(copy_set, self._copy_by_date)
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

    def get_mes_collect_mode(self):
        """
        获取MES收集模式下选中的收集条件
        :return: {'mode': 'ai_report'|'filter_rate', 'value': int}
        """
        if self.ai_report_checkbox.isChecked():
            value = int(self.ai_report_value.text())
            return {'mode': 'ai_report', 'value': value}
        elif self.filter_rate_checkbox.isChecked():
            value = int(self.filter_rate_value.text())
            return {'mode': 'filter_rate', 'value': value}

    def _copy_by_mes_new(self, collect_mode):
        """
        新的MES拷贝方法，支持根据条件过滤
        :param collect_mode: {'mode': 'ai_report'|'filter_rate', 'value': int}
        """
        try:
            logger.info(f"MES收集模式: {collect_mode['mode']}, 阈值: {collect_mode['value']}")
            selected_machines = self.machine_combo.get_selected_items()
            if not selected_machines:
                logger.warning("请选择至少一个机台！")
                self.setEnable(True)
                self._running = False
                return
            mes_ip = self.mes_ip_edit.text()
            if not mes_ip:
                logger.warning("请输入MES IP地址！")
                self.setEnable(True)
                self._running = False
                return
            
            if collect_mode['mode'] == 'ai_report':
                self._query_ai_report_data(mes_ip, selected_machines, collect_mode['value'])
            elif collect_mode['mode'] == 'filter_rate':
                self._query_filter_rate_data(mes_ip, selected_machines, collect_mode['value'])
            
        except Exception as e:
            logger.error(f"MES收集失败: {e}")
            self.setEnable(True)
        self._running = False
    
    def _query_filter_rate_data(self, mes_ip, machines, threshold):
        """
        查询料号过滤率数据
        """
        try:
            start_time = self.dateEdit.date().toString("yyyy-MM-dd") + " 00:00:00"
            end_time = self.dateEndEdit.date().toString("yyyy-MM-dd") + " 23:59:59"
            
            url = f"http://{mes_ip}:9099/GetLowRatioJob"
            logger.info(f"请求URL: {url}")
            logger.info(f"机台: {machines}, 时间范围: {start_time} - {end_time}, 阈值: {threshold}")
            
            request_data = {
                "dates": [start_time, end_time],
                "avis": machines,
                "err_count": threshold,
            }
            
            response = requests.post(url, json=request_data, timeout=(3, 10))
            
            if response.status_code == 200:
                response_data = response.json()
                data_str = response_data.get('data', '')
                
                if not data_str or data_str == "{}" or data_str == "{}\\n":
                    logger.warning("未找到数据，请调整时间范围或料号过滤率阈值！")
                    return
                
                # 解析返回的数据
                try:
                    # 移除可能的换行符
                    data_str = data_str.strip()
                    mes_data = json.loads(data_str)
                    
                    if not mes_data:
                        logger.warning("返回的数据为空！")
                        return
                    
                    logger.info(f"获取到 {len(mes_data)} 个料号的数据")
                    
                    self.mes_copy_data = mes_data  # 存储到实例变量
                    self._process_mes_data(mes_data)  # 直接执行拷贝
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 响应数据: {data_str}")

            elif response.status_code == 404:
                logger.error("URL不存在，请检查MES系统是否启动或可用")
            elif response.status_code == 400:
                error_msg = response.json().get('error', '请求参数错误')
                logger.error(f"请求错误: {error_msg}")
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("请求超时，请检查MES系统是否启动或可用")
        except Exception as e:
            logger.error(f"查询料号过滤率数据失败: {e}")

    def _query_ai_report_data(self, mes_ip, machines, threshold):
        """
        查询AI后报点数据
        """
        try:
            start_time = self.dateEdit.date().toString("yyyy-MM-dd") + " 00:00:00"
            end_time = self.dateEndEdit.date().toString("yyyy-MM-dd") + " 23:59:59"

            url = f"http://{mes_ip}:9099/api/test/list"
            logger.info(f"请求URL: {url}")
            logger.info(f"机台: {machines}, 时间范围: {start_time} - {end_time}, 阈值: {threshold}")

            request_data = {
                "dates": [start_time, end_time],
                "avis": machines,
                "err_count": threshold,
            }

            response = requests.post(url, json=request_data, timeout=(3, 10))
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('data', '')
                if not data or data == "{}" or data == "{}\\n":
                    logger.warning("未找到数据，请调整时间范围或料号过滤率阈值！")
                    return
                if isinstance(data, list):
                    mes_data = data
                if not mes_data:
                    logger.warning("返回的数据为空！")
                    return
                logger.info(f"获取到 {len(mes_data)} 条数据记录")
                # 直接传入列表，每条记录单独处理
                self._process_mes_data(mes_data)  # 传入原始列表数据
            elif response.status_code == 404:
                logger.error("URL不存在，请检查MES系统是否启动或可用")
            elif response.status_code == 400:
                error_msg = response.json().get('error', '请求参数错误')
                logger.error(f"请求错误: {error_msg}")
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error("请求超时，请检查MES系统是否启动或可用")
        except Exception as e:
            logger.error(f"查询料号过滤率数据失败: {e}")

    def _process_mes_data(self, mes_data):
        """
        处理MES返回的数据并执行拷贝
        :param mes_data: MES返回的JSON数据（列表格式，每条记录单独处理）
        """
        try:
            if not mes_data:
                logger.warning("没有需要处理的数据")
                return
            
            total_records = len(mes_data)
            logger.info(f"开始处理 {total_records} 条记录")
            
            save_path = self.saveEdit.text()
            if not save_path:
                logger.error("保存路径不能为空")
                return
            
            # 统计成功/失败的记录数
            success_count = 0
            fail_count = 0
            total_copy_count = 0
            
            # 记录已经处理过的料号（用于后续拷贝JOB和STD）
            processed_jobs = set()
            
            # 初始化进度跟踪
            completed_tasks = 0
            estimated_total = total_records + len(set(r.get('job_name') for r in mes_data)) * 2
            
            for i, record in enumerate(mes_data):
                if not self._running:
                    logger.info("用户停止拷贝")
                    break
                
                try:
                    job_name = record.get('job_name', '')
                    err_path = record.get('err_path', '')
                    std_path = record.get('std_path', '')
                    plno = record.get('plno', '')
                    is_top = record.get('is_top', False)
                    pcbno = record.get('pcbno', '')
                    
                    if err_path:
                        err_path = err_path.replace('\\\\', '\\')
                    if std_path:
                        std_path = std_path.replace('\\\\', '\\')
                    
                    if not err_path:
                        logger.warning(f"记录没有err_path，跳过")
                        fail_count += 1
                        continue
                    
                    if not os.path.exists(err_path):
                        logger.warning(f"源路径不存在: {err_path}")
                        fail_count += 1
                        continue
                    logger.info(f"处理记录 {i+1}/{total_records} - 料号 {job_name} ({plno}):")
                    logger.info(f"  源路径: {err_path}")
                    
                    # 1. 拷CAR
                    if 'car' in err_path:
                        # 提取相对路径（从car/开始）
                        relative_path = err_path[err_path.find('car'):]
                        target_car_path = os.path.join(save_path, relative_path)
                        
                        # 创建目标目录
                        target_car_dir = os.path.dirname(target_car_path)
                        os.makedirs(target_car_dir, exist_ok=True)
                        
                        # 拷贝文件
                        import shutil
                        shutil.copy2(err_path, target_car_path)
                        
                        logger.info(f"  CAR拷贝成功: {target_car_path}")
                        total_copy_count += 1
                        
                        # 2. 拷study文件（如果存在）
                        # study文件路径: std_path/job_name/pl_name/file_study
                        pl_name = plno
                        pcb_filename = os.path.basename(err_path)
                        study_file = os.path.join(std_path, job_name, pl_name, f"{pcb_filename}_study")
                        
                        if os.path.exists(study_file):
                            target_study_path = os.path.join(save_path, 'std', job_name, pl_name, f"{pcb_filename}_study")
                            target_study_dir = os.path.dirname(target_study_path)
                            os.makedirs(target_study_dir, exist_ok=True)
                            
                            shutil.copy2(study_file, target_study_path)
                            logger.info(f"  STUDY拷贝成功: {target_study_path}")
                    
                    success_count += 1
                    processed_jobs.add(job_name)
                    
                except Exception as e:
                    logger.error(f"处理记录失败: {e}")
                    fail_count += 1
                
                completed_tasks += 1
                progress = int(completed_tasks / estimated_total * 70) if estimated_total > 0 else 0
                self.progress_updated.emit(progress)
            
            # 3. 拷JOB文件（在所有CAR处理完成后，每个料号只需拷贝一次）
            if processed_jobs:
                logger.info("开始拷贝JOB文件...")
                job_count = len(processed_jobs)
                for idx, job_name in enumerate(processed_jobs):
                    try:
                        job_path = None
                        for record in mes_data:
                            if record.get('job_name') == job_name:
                                job_path = record.get('job_path', '')
                                break
                        
                        if not job_path:
                            continue
                        else:
                            job_path = job_path.replace('\\\\', '\\')
                        # 拷贝.top和.bot文件
                        for ext in ['.top', '.bot']:
                            src_job_file = os.path.join(job_path, f"{job_name}{ext}")
                            if os.path.exists(src_job_file):
                                target_job_dir = os.path.join(save_path, 'job')
                                os.makedirs(target_job_dir, exist_ok=True)
                                target_job_file = os.path.join(target_job_dir, f"{job_name}{ext}")
                                
                                # 检查目标文件是否存在，如果源文件更新则拷贝
                                should_copy = True
                                if os.path.exists(target_job_file):
                                    src_mtime = os.path.getmtime(src_job_file)
                                    dest_mtime = os.path.getmtime(target_job_file)
                                    should_copy = src_mtime > dest_mtime
                                
                                if should_copy:
                                    shutil.copy2(src_job_file, target_job_file)
                                    logger.info(f"  JOB拷贝成功: {target_job_file}")
                        
                        completed_tasks += 1
                        progress = int(70 + (completed_tasks / estimated_total * 15)) if estimated_total > 0 else 70
                        self.progress_updated.emit(progress)
                    
                    except Exception as e:
                        logger.error(f"拷贝JOB文件失败 {job_name}: {e}")
            
            # 4. 拷STD文件
            if processed_jobs:
                logger.info("开始拷贝STD文件...")
                job_count = len(processed_jobs)
                for idx, job_name in enumerate(processed_jobs):
                    try:
                        std_path = None
                        for record in mes_data:
                            if record.get('job_name') == job_name:
                                std_path = record.get('std_path', '')
                                break
                        
                        if not std_path:
                            continue
                        else:
                            std_path = std_path.replace('\\\\', '\\')
                        # 拷贝_View目录
                        src_std_view = os.path.join(std_path, f"{job_name}_View")
                        if os.path.exists(src_std_view):
                            target_std_view = os.path.join(save_path, 'job', f"{job_name}_View")
                            logger.info(f"  STD View开始拷贝: {target_std_view}")
                            os.makedirs(os.path.dirname(target_std_view), exist_ok=True)
                            shutil.copytree(src_std_view, target_std_view, dirs_exist_ok=True)
                            logger.info(f"  STD View拷贝成功: {target_std_view}")
                        
                        # 拷贝StudyTemp目录（如果存在）
                        src_std_study = os.path.join(std_path, job_name, "StudyTemp")
                        if os.path.exists(src_std_study):
                            target_std_study = os.path.join(save_path, 'job', job_name, "StudyTemp")
                            os.makedirs(os.path.dirname(target_std_study), exist_ok=True)
                            shutil.copytree(src_std_study, target_std_study, dirs_exist_ok=True)
                            logger.info(f"  STD StudyTemp拷贝成功: {target_std_study}")
                        
                        completed_tasks += 1
                        progress = int(85 + (completed_tasks / estimated_total * 15)) if estimated_total > 0 else 85
                        self.progress_updated.emit(progress)
                    
                    except Exception as e:
                        logger.error(f"拷贝STD文件失败 {job_name}: {e}")
            else:
                # 如果没有STD文件，直接设置100%
                self.progress_updated.emit(100)
            
            logger.info(f"MES数据拷贝完成！成功: {success_count}, 失败: {fail_count}, 总拷贝文件数: {total_copy_count}, 处理料号数: {len(processed_jobs)}")
        except Exception as e:
            logger.error(f"处理MES数据失败: {e}")

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
