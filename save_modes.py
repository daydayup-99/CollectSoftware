import glob
import os
from collections import defaultdict

import pandas as pd

from settings import should_copy_suffixes, study_suffixes, defect_suffixes
from utils import copy_tree_with_error_handling, copy_with_error_handling, _make_dir, find_file
from logging_handler import logger


# 存储方式的基类
class SaveMode:
    def __init__(self, car_dir, job_dir, save_dir, study_dir, log_dir, date, use_aoi=True, use_avi=False, machine_type='在线机', need_compress=False, compress_name=''):
        """
        :param car_dir: 缺陷资料存储路径
        :param job_dir: Gerber资料存储路径
        :param save_dir: 拷贝资料保存路径
        :param study_dir: 学板资料路径
        :param log_dir: 日志资料路径
        :param date: 日期
        :param use_aoi: 是否使用aoi模式
        :param use_avi: 是否使用avi模式
        :param need_compress: 是否需要压缩
        :param compress_name: 压缩包名称
        """
        self.car_dir = car_dir
        self.job_dir = job_dir
        self.save_dir = save_dir
        self.study_dir = study_dir
        self.log_dir = log_dir
        self.date = date
        self.have_msg = True
        self.use_aoi = use_aoi
        self.use_avi = use_avi
        self.machine_type = machine_type
        self.need_compress = need_compress
        self.compress_name = compress_name
        self.car_date_dir = os.path.join(self.car_dir, self.date)
        self.save_car_dir = os.path.join(self.save_dir, 'aoicar' if use_aoi else 'car')
        self.save_job_dir = os.path.join(self.save_dir, 'aoijob' if use_aoi else 'job')
        if machine_type == '离线机':
            self.save_study_dir = os.path.join(self.save_dir, 'aoijob' if use_aoi else 'job')
        else:
            self.save_study_dir = os.path.join(self.save_dir, 'aoicar' if use_aoi else 'car')
            if use_avi:
                self.save_log_dir = os.path.join(self.save_dir, 'avilog')
        self.save_car_date_dir = os.path.join(self.save_car_dir, self.date)
        self._make_save_dirs()

        # 按日期拷贝存储各个料号对应的板号 {'job_name1': [1, 2],
        #                              'job_name2': [3, 4], ...}
        self.job_name_nums = defaultdict(list)

    def _make_save_dirs(self):
        """
        创建存储资料的路径，与拷贝资料路径一致
        """
        paths = [self.save_job_dir, self.save_study_dir]
        if self.machine_type != '离线机':
            paths.append(self.save_car_date_dir)
            if self.use_avi:
                paths.append(self.save_log_dir)
        for path in paths:
            _make_dir(path)

    def copy(self, copy_num_range: list, is_running_callback, by_date=True, max_num=0):
        """
        :param max_num: 按日期拷贝的最大板数
        :param copy_num_range: 需要拷贝板号的范围 兼容按日期拷贝
        :param is_running_callback: 程序是否在运行
        :param by_date: 如果是False，就是按板号拷贝
        """
        for index, num in enumerate(copy_num_range):
            if not is_running_callback():
                raise Exception('已停止')

            try:
                batch_name = self._get_batch_name(num)
                job_name = batch_name.split("\\")[0]
                if by_date and len(self.job_name_nums[job_name]) >= max_num:
                    continue
                if self.use_avi:
                    self._copy_bgr(job_name)
                self._copy_num(num, batch_name)
                self._copy_job(job_name)
                self.job_name_nums[job_name].append(num)
            except Exception as e:
                logger.warning(f"Error processing num {num}: {e}")
                continue

    def copyAVI(self, copy_num_range: list, is_running_callback, max_num=0):
        """
        :param copy_num_range: 需要拷贝板号的范围
        :param is_running_callback: 程序是否在运行
        :param max_num: 拷贝的最大板数
        """
        for index, file_path in enumerate(copy_num_range):
            if not is_running_callback():
                raise Exception('已停止')
            try:
                job_dir = os.path.dirname(file_path)
                job_name = os.path.basename(job_dir)
                pl_name = os.path.basename(file_path)
                file_paths = []
                if os.path.isdir(file_path):
                    for file_name in os.listdir(file_path):
                        full_file_path = os.path.join(file_path, file_name)
                        if os.path.isfile(full_file_path):
                            for suffix in should_copy_suffixes:
                                if file_name.endswith(suffix):
                                    file_paths.append(full_file_path)
                                    break
                if file_paths:
                    target_dir = os.path.join(self.save_car_dir, job_name, pl_name)
                    self._copy_files_from_paths(file_paths, target_dir)
                self._copy_job(job_name)
            except Exception as e:
                logger.warning(f"Error processing num {file_path}: {e}")
                continue
    def _copy_bgr(self, job):
        if not job:
            return
        bgr_dir = os.path.join(self.study_dir, job)
        save_bgr_dir = os.path.join(self.save_dir, "car", job)
        if not os.path.exists(save_bgr_dir):
            _make_dir(save_bgr_dir)
            bgr_path = os.path.join(bgr_dir, '1_t')
            bgr_path_b = os.path.join(bgr_dir, '1_b')
            save_bgr_path = os.path.join(save_bgr_dir, '1_t')
            save_bgr_path_b = os.path.join(save_bgr_dir, '1_b')
            copy_with_error_handling(bgr_path, save_bgr_path)
            copy_with_error_handling(bgr_path_b, save_bgr_path_b)

    def _copy_num(self, num, batch_name):
        self._copy_defect(num, batch_name)
        if self.use_aoi:
            self._copy_vrs(num, batch_name)
        if self.machine_type == "在线机":
            self._copy_study(num, batch_name)

    def _copy_defect(self, num, batch_name):
        if self.have_msg:
            self._copy_source(num, self.car_date_dir, self.save_car_date_dir, '_msg')
        self._copy_items(num, batch_name, self.get_save_defect_dir, should_copy_suffixes)

    def _copy_study(self, num, batch_name):
        self._copy_items(num, batch_name, self.get_save_study_dir, study_suffixes)

    def _copy_vrs(self, num, batch_name):
        defect_dir, save_defect_dir = self.get_save_defect_dir(batch_name)
        vrs_dir = os.path.join(defect_dir, str(num))
        save_vrs_dir = os.path.join(save_defect_dir, str(num))
        if not os.path.isdir(vrs_dir):
            return
        _make_dir(save_vrs_dir)
        vrs_path = os.path.join(vrs_dir, 'A.vrs')
        vrs_path_b = os.path.join(vrs_dir, 'B.vrs')
        save_vrs_path = os.path.join(save_vrs_dir, 'A.vrs')
        save_vrs_path_b = os.path.join(save_vrs_dir, 'B.vrs')
        copy_with_error_handling(vrs_path, save_vrs_path)
        copy_with_error_handling(vrs_path_b, save_vrs_path_b)

    # 拷贝所有资料的共性
    def _copy_items(self, num, batch_name, get_dir_func, suffixes):
        source_dir, target_dir = get_dir_func(batch_name)
        _make_dir(target_dir)
        for suffix in suffixes:
            self._copy_source(num, source_dir, target_dir, suffix)

    @staticmethod
    def _copy_source(num, source_dir, target_dir, suffix):
        origin_path = os.path.join(source_dir, (str(num) + suffix))
        target_path = os.path.join(target_dir, (str(num) + suffix))
        if os.path.exists(origin_path):
            copy_with_error_handling(origin_path, target_path)

    def _copy_files_from_paths(self, file_paths, target_dir):
        """
        从文件路径列表复制文件到目标目录
        :param file_paths: 文件完整路径列表
        :param target_dir: 目标目录
        """
        if not file_paths:
            return
        _make_dir(target_dir)
        for file_path in file_paths:
            if os.path.isfile(file_path):
                file_name = os.path.basename(file_path)
                target_path = os.path.join(target_dir, file_name)
                copy_with_error_handling(file_path, target_path)
                logger.info(f'已复制文件: {file_name} 到 {target_dir}')

    def _copy_job(self, job_name: str):
        if not job_name:
            return
        job_path = os.path.join(self.job_dir, job_name)
        save_job_path = os.path.join(self.save_job_dir, job_name)
        if os.path.exists(save_job_path) is False and os.path.isdir(job_path):
            copy_tree_with_error_handling(job_path, save_job_path)

        # if not os.path.isdir(job_path):不用这个, 主软软件还能傻逼到生成空的job文件夹#
        # 如果用了这个, 就会只拷贝空的文件夹,真的job资料会拷贝不到
        job_files = glob.glob(os.path.join(self.job_dir, f'{job_name}.*'))
        if len(job_files) > 0:
            for file in job_files:
                save_file_path = os.path.join(self.save_job_dir, os.path.basename(file))
                if os.path.exists(save_file_path) is False:
                    copy_with_error_handling(file, self.save_job_dir)
        elif self.use_avi and self.machine_type == '在线机':
            all_files = glob.glob(os.path.join(self.job_dir, '*'))
            for file in all_files:
                save_file_path = os.path.join(self.save_job_dir, os.path.basename(file))
                if os.path.exists(save_file_path) is False:
                    copy_with_error_handling(file, self.save_job_dir)
        std_dir = glob.glob(os.path.join(self.job_dir, f'{job_name}_View'))
        if len(std_dir) > 0 and self.use_avi and self.machine_type == "离线机":
            src_dir = std_dir[0]
            target_dir = os.path.join(self.save_job_dir, os.path.basename(src_dir))
            if os.path.exists(target_dir) is False:
                copy_tree_with_error_handling(src_dir, target_dir)
                logger.info(f'已拷贝文件夹: {os.path.basename(src_dir)} 到 {self.save_job_dir}')
    def get_save_defect_dir(self, batch_name):
        raise NotImplementedError('必须在子类中定义')

    def get_save_study_dir(self, batch_name):
        raise NotImplementedError('必须在子类中定义')

    def get_job_name(self, num):
        try:
            job_name = self._get_job_name(num)
            return job_name
        except FileNotFoundError as fnf:
            raise Exception(f'读取文件未找到: {fnf.filename}')
        except Exception as e:
            raise Exception(f'在日期{self.date}里的板号{num}出错 读取文件出错：{e}')

    def get_date_num_list(self, save_set_text):
        try:
            date_num_list = self._get_date_num_list()
            return date_num_list
        except Exception as e:
            logger.error(f'请检查是否是{save_set_text}: {e}')
            return []

    def _get_job_name(self, num):
        raise NotImplementedError('必须在子类中定义')

    def _get_date_num_list(self):
        raise NotImplementedError('必须在子类中定义')

    def _get_batch_name(self, num):
        r"""
        :param num: 板号
        :return: job_name or job_name\batch_name
        """
        return self.get_job_name(num)

    def compress_folder(self):
        """
        压缩目标文件夹
        """
        if not self.need_compress or not self.compress_name:
            logger.info('不需要压缩或压缩名称为空，跳过压缩')
            return
        
        import zipfile
        
        compress_name = self.compress_name
        if not compress_name.endswith('.zip'):
            compress_name += '.zip'
        
        zip_path = os.path.join(self.save_dir, compress_name)
        try:
            logger.info(f'开始压缩文件夹: {self.save_dir} -> {zip_path}')
            
            if not os.path.exists(self.save_dir):
                logger.error(f'源目录不存在: {self.save_dir}')
                return
            if not os.listdir(self.save_dir):
                logger.warning(f'源目录为空: {self.save_dir}')
                return
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.save_dir):
                    for file in files:
                        if file == compress_name:
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.save_dir)
                        zipf.write(file_path, arcname)

            if os.path.exists(self.save_dir):
                import shutil
                for item in os.listdir(self.save_dir):
                    item_path = os.path.join(self.save_dir, item)
                    if item == compress_name:
                        continue
                    
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        logger.info(f'删除文件: {item_path}')
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f'删除文件夹: {item_path}')
                
        except Exception as e:
            logger.error(f'压缩失败: {e}', exc_info=True)

class DateSaveMode(SaveMode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.have_msg = False

    def get_save_defect_dir(self, batch_name):
        return self.car_date_dir, self.save_car_date_dir

    def get_save_study_dir(self, batch_name):
        study_date_dir = os.path.join(self.study_dir, self.date)
        save_study_date_dir = os.path.join(self.save_study_dir, self.date)
        return study_date_dir, save_study_date_dir

    def _get_job_name(self, num):
        if self.use_avi:
            date = os.path.basename(self.car_date_dir)
            return date
        file_path = os.path.join(self.car_date_dir, str(num), 'A.vrs')
        with open(file_path, 'r') as file:
            data = file.readlines()
        return data[6].rstrip()

    def _get_date_num_list(self):
        return sorted([int(name) for name in os.listdir(self.car_date_dir) if name.isdigit()])


class JobSaveMode(SaveMode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read_msg(self, num):
        file_path = os.path.join(self.car_date_dir, str(num) + '_msg')
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = f.readlines()
                return data
        return []

    def get_save_defect_dir(self, batch_name):
        car_job_date_dir = os.path.join(self.car_dir, batch_name, self.date)
        save_car_job_date_dir = os.path.join(self.save_car_dir, batch_name, self.date)
        return car_job_date_dir, save_car_job_date_dir

    def get_save_study_dir(self, batch_name):
        study_job_date_dir = os.path.join(self.study_dir, batch_name, self.date)
        save_study_job_date_dir = os.path.join(self.save_study_dir, batch_name, self.date)
        return study_job_date_dir, save_study_job_date_dir

    def _get_job_name(self, num):
        data = self.read_msg(num)
        return data[0].replace('\n', '').rstrip()

    def _get_date_num_list(self):
        return sorted([int(str(num).replace('_msg', '')) for num in os.listdir(self.car_date_dir) if
                       str(num).replace('_msg', '').isdigit()])


class BatchSaveMode(JobSaveMode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_batch_name(self, num):
        data = self.read_msg(num)
        return data[1].replace('\n', '').rstrip()

    def get_save_defect_dir(self, batch_name):
        car_job_date_dir = os.path.join(self.car_dir, batch_name)
        save_car_job_date_dir = os.path.join(self.save_car_dir, batch_name)
        return car_job_date_dir, save_car_job_date_dir

    def get_save_study_dir(self, batch_name):
        study_job_date_dir = os.path.join(self.study_dir, batch_name)
        save_study_job_date_dir = os.path.join(self.save_study_dir, batch_name)
        return study_job_date_dir, save_study_job_date_dir


class ManualSaveMode(BatchSaveMode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.have_msg = False
        formatted_date = f"{self.date[:4]}_{int(self.date[4:6])}_{int(self.date[6:])}"
        self.log_path = os.path.join(os.path.dirname(self.car_dir), 'aoilog', f'{formatted_date}.txt')

    @staticmethod
    def _copy_source(num, source_dir, target_dir, suffix):
        if not os.path.exists(source_dir):
            return
        origin_path = os.path.join(source_dir, (str(num) + suffix))
        target_path = os.path.join(target_dir, (str(num) + suffix))
        if suffix in defect_suffixes:
            defect_filename = find_file(source_dir, num, suffix)
            if not defect_filename:
                logger.warning(f'文件未找到:{os.path.join(source_dir, (str(num) + suffix))}')
            origin_path = os.path.join(source_dir, defect_filename)
            target_path = os.path.join(target_dir, defect_filename)

        copy_with_error_handling(origin_path, target_path)

    def _make_save_dirs(self):
        """
        创建存储资料的路径，与拷贝资料路径一致
        """
        for path in [self.save_job_dir, self.save_study_dir]:
            _make_dir(path)

    def _get_date_num_list(self):
        """
        与其他存储方式不同，需要读取日志
        :return: {'job_name/batch_name':[nums]}
        """
        if not os.path.exists(self.log_path):
            raise FileNotFoundError(f'日志路径{self.log_path}不存在')

        data = pd.read_csv(self.log_path, sep=r"\s+", header=None, engine="python")
        data = data.iloc[:, :5]
        data.columns = ["Time", "Job", "User", 'Batch', 'Value']

        results = defaultdict(set)
        for job, batch in zip(data['Job'], data['Batch']):
            batch_parts = str(batch).split(':')
            batch_name = batch_parts[0]
            num = batch_parts[1]
            path = os.path.join(job, batch_name)
            results[path].add(num)

        return results

    def copy(self, copy_num_range: dict, is_running_callback, by_date=True, max_num=0):
        """
        :param max_num: 按日期拷贝的最大板数
        :param copy_num_range: {'job_name/batch_name':[nums]}
        :param is_running_callback: 程序是否在运行
        :param by_date: 如果是False，就是按板号拷贝, 该类暂时不按板号拷贝
        """
        for batch_name, nums in copy_num_range.items():
            nums_to_copy = list(nums)[:max_num + 1]
            job_name = batch_name.split("\\")[0]

            for num in nums_to_copy:
                if not is_running_callback():
                    raise Exception('已停止')

                try:
                    self._copy_num(num, batch_name)
                    self._copy_job(job_name)
                except Exception as e:
                    logger.warning(f"Error processing num {num}: {e}")
                    continue


class Batch0SaveMode(BatchSaveMode):
    """
    按批量存储(从0开始)：msg文件存储板号的料号名、批量名以及板号序号（msg的序号和实际_b的序号不一样，因为实际的都是从0开始）
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_batch_info(self, num):
        data = self.read_msg(num)
        if len(data) < 3:
            raise Exception('msg文件格式错误, 格式应为第一行：料号名，第二行：批量名，第三行：序号')
        job_name, batch_name, date_num = [item.replace('\n', '').rstrip() for item in data[:3]]
        return job_name, batch_name, date_num

    def copy(self, copy_num_range: list, is_running_callback, by_date=True, max_num=0):
        """
        :param max_num: 按日期拷贝的最大板数
        :param copy_num_range: 需要拷贝板号的范围 兼容按日期拷贝
        :param is_running_callback: 程序是否在运行
        :param by_date: 如果是False，就是按板号拷贝
        """
        for index, num in enumerate(copy_num_range):
            if not is_running_callback():
                raise Exception('已停止')

            try:
                job_name, batch_name, date_num = self._get_batch_info(num)
                if by_date and len(self.job_name_nums[job_name]) >= max_num:
                    continue
                self._copy_num({'msg': num, 'date_num': date_num}, f'{job_name}/{batch_name}')
                self._copy_job(job_name)
                self.job_name_nums[job_name].append(num)
            except Exception as e:
                logger.warning(f"Error processing num {num}: {e}")
                continue

    def _copy_num(self, num: dict, batch_name):
        self._copy_defect(num, batch_name)
        self._copy_vrs(num['date_num'], batch_name)
        self._copy_study(num['date_num'], batch_name)

    def _copy_defect(self, num: dict, batch_name):
        if self.have_msg:
            self._copy_source(num['msg'], self.car_date_dir, self.save_car_date_dir, '_msg')
        self._copy_items(num['date_num'], batch_name, self.get_save_defect_dir, should_copy_suffixes)
