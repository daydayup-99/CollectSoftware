from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtGui import QPainter, QColor, QLinearGradient
from PyQt5.QtWidgets import QProgressBar


class CustomProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('QProgressBar { border: 8px solid grey; border-radius: 20px; background-color: #f0f0f0; }')
        self.setOrientation(Qt.Vertical)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(30)
        self.animation_alpha = 100  # 初始动画透明度
        self.animation_direction = 1  # 动画方向：1为逐渐变亮，-1为逐渐变暗

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景
        bg_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        painter.drawRoundedRect(bg_rect, 8, 8)

        # 绘制进度条
        progress_rect = QRect(
            int(bg_rect.x()),
            int(bg_rect.y() + bg_rect.height() * (1 - self.value() / self.maximum())),
            int(bg_rect.width()),
            int(bg_rect.height() * self.value() / self.maximum())
        )

        # 计算渐变色
        gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.bottomLeft())
        gradient.setColorAt(0.0, QColor(77, 208, 225, self.animation_alpha))
        gradient.setColorAt(1.0, QColor(77, 208, 225, self.animation_alpha))
        painter.setBrush(gradient)
        painter.drawRoundedRect(progress_rect, 8, 8)

        # 绘制文字（进度百分比）
        painter.save()  # 保存当前绘图状态

        # 将绘图原点移动到进度条中心
        painter.translate(progress_rect.center())

        # 旋转90度以使文本垂直显示
        painter.rotate(-90)

        # 恢复文本矩形的位置
        text_rect = QRect(-progress_rect.height() // 2, -progress_rect.width() // 2,
                          progress_rect.height(), progress_rect.width())

        painter.setPen(Qt.black)
        painter.drawText(text_rect, Qt.AlignCenter, f"{int(100 * self.value() / self.maximum())}%")

        # 恢复到保存的绘图状态
        painter.restore()

    def updateAnimation(self):
        if self.value() == self.maximum():  # 当进度达到最大值时停止动画
            return
        self.animation_alpha += self.animation_direction * 5  # 调整透明度变化步长
        if self.animation_alpha <= 50 or self.animation_alpha >= 200:
            self.animation_direction *= -1  # 到达边界时改变方向
        self.update()