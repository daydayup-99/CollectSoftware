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
    """
    将各种常见日期字符串统一为 yyyy-MM-dd。
    兼容中文区的 yyyy/M/d，以及国外常见的 M/D/yyyy、d/M/yyyy、带点分隔等。
    """
    if date_str is None:
        return datetime.date.today().strftime('%Y-%m-%d')
    text = str(date_str).strip()
    if not text:
        return datetime.date.today().strftime('%Y-%m-%d')

    # 已是标准格式
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d',
                '%m/%d/%Y', '%d/%m/%Y', '%d.%m.%Y', '%m-%d-%Y', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(text, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue

    # 兼容无补零的 yyyy/M/d 或 yyyy-M-d
    for sep in ('/', '-', '.'):
        if sep in text:
            parts = text.split(sep)
            if len(parts) == 3:
                try:
                    a, b, c = (int(p) for p in parts)
                    # 年在前
                    if a >= 1000:
                        return datetime.date(a, b, c).strftime('%Y-%m-%d')
                    # 年在后：优先按月/日/年（美式），失败再试日/月/年
                    try:
                        return datetime.date(c, a, b).strftime('%Y-%m-%d')
                    except ValueError:
                        return datetime.date(c, b, a).strftime('%Y-%m-%d')
                except ValueError:
                    pass

    logging.error(f'日期格式不正确: {text!r}')
    return datetime.date.today().strftime('%Y-%m-%d')
