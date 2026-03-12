import datetime
import os
import shutil
import logging
import functools


def find_file(source_dir, num, suffix):
    prefix = str(num) + suffix
    for entry in os.scandir(source_dir):
        if entry.is_file() and entry.name.startswith(prefix):
            return entry.name
    return None


def handle_file_errors(func):
    """装饰器，用于捕获文件操作中的异常"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as fnf_error:
            if fnf_error.filename.endswith(('_b', '_t')):
                logging.warning(f"文件未找到: {fnf_error.filename}")
        except PermissionError as perm_error:
            raise PermissionError(f"权限错误: {perm_error}")
        except FileExistsError as fef_error:
            logging.warning(f'文件已存在， 请检查是否复制成功 {fef_error.filename}')
        except IOError as io_error:
            raise IOError(f"IO错误: {io_error}")
        except Exception as e:
            raise Exception(f"未预见的错误: {e}")

    return wrapper


@handle_file_errors
def copy_with_error_handling(src, dst):
    shutil.copy2(src, dst)


@handle_file_errors
def copy_tree_with_error_handling(src, dst):
    shutil.copytree(src, dst)


def _make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def format_date(date_str):
    try:
        year_s, mon_s, day_s = date_str.split('/')
        date = datetime.date(int(year_s), int(mon_s), int(day_s))
        formatted_date_str = date.strftime('%Y-%m-%d')
        return formatted_date_str
    except ValueError:
        logging.error('日期格式不正确 date_str')
