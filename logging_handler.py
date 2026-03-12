import logging

from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
import functools

# 设置全局的日志记录格式和日志等级
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO)


class QTextBrowerHandler(logging.Handler):
    """
    接收一个接数text_browser，他是一个pyqt5的QTextBrowser控件，特征是不可编辑的文本框，适合用来记录日志
    """

    def __init__(self, text_browser: QTextBrowser, level=logging.NOTSET):
        super().__init__(level)
        self.text_browser = text_browser

        # 给此handler定义日志的格式
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """日志处理函数，格式化日志数据后，写入到QTextBrower控件中"""
        msg = self.format(record)
        if record.levelno == logging.WARNING:
            msg = f'<span style="color: #FFA500;">{msg}</span>'
        elif record.levelno == logging.ERROR:
            msg = f'<span style="color: red; font-weight: bold;">{msg}</span>'
        # 使用 functools.partial 包装方法调用
        append_text = functools.partial(self.text_browser.append, msg)
        # 使用 invokeMethod 在主线程中调用方法
        QMetaObject.invokeMethod(self.text_browser, "append", Qt.QueuedConnection, Q_ARG(str, msg))


# 创建一个logger实例，其他模块引用该实例来记录日志
logger = logging.getLogger()
