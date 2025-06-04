"""
YouTube Downloader 的主程序入口
"""
import os
import sys
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

from src.ui.main_window import MainWindow
from src.utils.logger import LoggerManager
from src.core.video_info.format_parser import FormatParser, VideoInfoCache
from src.config.get_software_version import get_software_version


def main():
    """主程序入口"""
    # 初始化日志
    logger = LoggerManager().get_logger()
    logger.info("应用程序启动")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
    splash_path = os.path.join(base_dir, 'resources', 'icons', 'splash.png')
    
    # 设置应用程序图标
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建启动画面
    splash = None
    if os.path.exists(splash_path):
        splash_pixmap = QPixmap(splash_path)
        if not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
            splash.show()
            splash.showMessage("正在加载应用程序...", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
            app.processEvents()
    
    # 创建主窗口
    main_window = MainWindow(splash)
    main_window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
