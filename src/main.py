"""
YouTube 视频下载工具的主入口模块
"""
import os
import sys

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

# 导入自定义模块
from src.ui.main_window import MainWindow
from src.utils.logger import LoggerManager

def main():
    """主函数"""
    # 初始化日志
    logger = LoggerManager().get_logger()
    logger.info("应用程序启动")
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    splash_path = os.path.join(base_dir, 'resources', 'icons', 'splash.png')
    
    # 创建启动画面
    splash = None
    if os.path.exists(splash_path):
        splash_pixmap = QPixmap(splash_path)
        if not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
            splash.show()
            app.processEvents()
    
    # 创建主窗口
    window = MainWindow(splash)
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 