"""
YouTube Downloader Cookie标签页模块
负责创建和管理Cookie标签页界面
"""
import os
import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QMessageBox, QGroupBox, QStatusBar,
    QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# 使用绝对导入
from src.core.cookie_manager import CookieManager
from src.utils.logger import LoggerManager
from src.ui.components.cookie_login_dialog import CookieLoginDialog, is_webengine_available

class CookieTab(QWidget):
    """Cookie标签页类"""
    
    def __init__(self, status_bar: QStatusBar = None):
        """
        初始化Cookie标签页
        
        Args:
            status_bar: 状态栏
        """
        super().__init__()
        
        # 初始化日志
        self.logger = LoggerManager().get_logger()
        self.status_bar = status_bar
        
        # 初始化Cookie管理器
        self.cookie_manager = CookieManager()
        
        # 添加Cookie状态显示
        self.cookie_status = "未使用"  # 添加状态属性
        
        # 登录对话框引用
        self.login_dialog: Optional[CookieLoginDialog] = None
        
        # 初始化UI
        self.init_ui()
        
        # 记录日志
        self.logger.info("Cookie标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建Cookie状态区域
        status_group = QGroupBox("Cookie状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态显示
        self.status_label = QLabel("当前状态：未使用")
        self.status_label.setWordWrap(True)  # 允许文本换行
        self.status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 文本左对齐
        self.status_label.setTextFormat(Qt.RichText)  # 启用富文本格式
        status_layout.addWidget(self.status_label)
        
        # 按钮水平布局
        status_button_layout = QHBoxLayout()

        # 验证按钮
        self.verify_button = QPushButton("验证Cookie")
        self.verify_button.clicked.connect(self.verify_cookies)
        status_button_layout.addWidget(self.verify_button)

        # 清除按钮
        self.clear_button = QPushButton("清除Cookie")
        self.clear_button.clicked.connect(self.clear_loaded_cookie)
        status_button_layout.addWidget(self.clear_button)

        status_layout.addLayout(status_button_layout)
        
        # 添加状态区域到主布局
        main_layout.addWidget(status_group)
        
        # 创建Cookie文件区域
        cookie_file_group = QGroupBox("Cookie文件")
        cookie_file_layout = QVBoxLayout(cookie_file_group)
        
        # Cookie文件路径输入框
        file_path_layout = QHBoxLayout()
        self.cookie_file_input = QLineEdit()
        self.cookie_file_input.setPlaceholderText("")  # 清空占位符
        file_path_layout.addWidget(self.cookie_file_input)
        
        # 浏览按钮
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_cookie_file)
        file_path_layout.addWidget(self.browse_button)
        
        cookie_file_layout.addLayout(file_path_layout)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 登录获取按钮
        self.login_button = QPushButton("登录获取 Cookie")
        self.login_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #0062cc;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.login_button.clicked.connect(self.open_login_dialog)
        button_layout.addWidget(self.login_button)
        
        # 添加说明文字
        note_label = QLabel("点击按钮将打开内置浏览器，请登录您的 Google 账户")
        note_label.setStyleSheet("color: #666; font-size: 10px;")
        note_label.setWordWrap(True)
        cookie_file_layout.addWidget(note_label)
        
        # 检查 WebEngine 是否可用
        if not is_webengine_available():
            self.login_button.setEnabled(False)
            self.login_button.setToolTip("需要安装 PyQtWebEngine")
            note_label.setText("⚠️ 请先安装 PyQtWebEngine: pip install PyQtWebEngine")
            note_label.setStyleSheet("color: #e74c3c; font-size: 10px;")
        
        
        cookie_file_layout.addLayout(button_layout)
        
        # 添加Cookie文件区域到主布局
        main_layout.addWidget(cookie_file_group)
        
        # 添加Cookie说明文字
        note_label = QLabel("⚠️ Cookie 使用说明：")
        note_label.setStyleSheet("color: #e67e22; font-size: 12px; font-weight: bold; margin: 10px 0;")
        main_layout.addWidget(note_label)
        
        note_content = QLabel("Cookie 不是必需的，仅在以下情况需要：\n1. 下载会员专属视频\n2. 下载年龄限制视频\n3. 下载私人视频")
        note_content.setStyleSheet("color: #e67e22; font-size: 11px; margin: 5px 0 15px 0;")
        note_content.setWordWrap(True)
        main_layout.addWidget(note_content)
        
        # 创建Cookie内容区域
        cookie_content_group = QGroupBox("Cookie内容")
        cookie_content_layout = QVBoxLayout(cookie_content_group)
        
        # Cookie内容显示
        self.cookie_content = QTextEdit()
        self.cookie_content.setReadOnly(True)
        self.cookie_content.setPlaceholderText("Cookie内容将显示在这里")
        cookie_content_layout.addWidget(self.cookie_content)
        
        # 添加Cookie内容区域到主布局
        main_layout.addWidget(cookie_content_group)
        
        # 添加弹性空间
        main_layout.addStretch()
    
    def clear_loaded_cookie(self):
        """清除已加载的Cookie信息，但不删除文件。"""
        # 1. 清空UI组件
        self.cookie_file_input.clear()
        self.cookie_content.clear()
        
        # 2. 重置状态标签
        self.status_label.setText("当前状态：未使用")
        
        # 3. 更新内部和外部状态
        self.update_cookie_status(False)
        self.update_status_message("已清除加载的 Cookie")
        
        # 4. 通知用户
        QMessageBox.information(self, "操作成功", "已清除加载的 Cookie 信息。")
        self.logger.info("用户清除了已加载的 Cookie 信息。")

    def verify_cookies(self):
        """验证Cookie"""
        cookie_file = self.cookie_file_input.text()
        
        if not cookie_file:
            QMessageBox.warning(self, "警告", "请先选择或获取Cookie文件")
            return
        
        if not os.path.exists(cookie_file):
            QMessageBox.warning(self, "警告", "Cookie文件不存在")
            return
        
        try:
            # 导入验证函数
            from src.core.cookie.check_cookies import verify_cookie
            is_valid, message, user_id, username = verify_cookie(cookie_file)
            
            if is_valid:
                self.update_cookie_status(True)
                # 使用HTML格式化状态文本
                status_text = f"""
                <div style='margin: 10px 0;'>
                    <p style='color: #2ecc71; font-weight: bold; margin-bottom: 10px;'>Cookie验证成功</p>
                    <p style='margin: 5px 0;'><b>用户ID:</b> <span style='color: #3498db;'>{user_id}</span></p>
                    <p style='margin: 5px 0;'><b>用户名:</b> <span style='color: #3498db;'>@{username}</span></p>
                </div>
                """
                self.status_label.setText(status_text)
                self.update_status_message("Cookie验证成功")
                QMessageBox.information(self, "成功", f"Cookie验证成功！\n\n用户ID: {user_id}\n用户名: @{username}")
            else:
                self.update_cookie_status(False)
                self.update_status_message(f"Cookie验证失败: {message}")
                QMessageBox.warning(self, "警告", f"Cookie验证失败:\n{message}")
        except Exception as e:
            self.logger.error(f"验证Cookie失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"验证Cookie失败:\n{str(e)}")
            self.update_status_message("Cookie验证失败")
    
    def open_login_dialog(self):
        """打开内置浏览器登录对话框"""
        try:
            if not is_webengine_available():
                QMessageBox.critical(
                    self, 
                    "错误", 
                    "PyQtWebEngine 未安装。\n\n请运行以下命令安装：\npip install PyQtWebEngine"
                )
                return
            
            self.logger.info("打开登录对话框...")
            self.update_status_message("正在打开登录窗口...")
            
            # 创建登录对话框
            self.login_dialog = CookieLoginDialog(self)
            self.login_dialog.login_finished.connect(self.handle_login_result)
            
            # 开始登录流程
            self.login_dialog.start_login()
            
            # 显示对话框（模态）
            self.login_dialog.exec_()
            
        except Exception as e:
            self.logger.error(f"打开登录对话框失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"打开登录对话框失败:\n{str(e)}")
            self.update_status_message("打开登录对话框失败")
    
    def handle_login_result(self, success: bool, cookie_file: str, message: str):
        """处理登录结果"""
        try:
            self.logger.info(f"收到登录结果: success={success}, message={message}")
            
            if success and cookie_file and os.path.exists(cookie_file):
                # 加载生成的 cookie 文件
                self.logger.debug(f"设置Cookie文件路径: {cookie_file}")
                self.cookie_file_input.setText(cookie_file)
                self.load_cookie_content(cookie_file)
                self.update_status_message("Cookie 获取成功")
                self.logger.info("Cookie 获取成功并已加载")
                
                # 显示成功消息
                QMessageBox.information(
                    self, 
                    "成功", 
                    f"Cookie 获取成功！\n\n文件已保存至：{cookie_file}\n\n建议点击「验证Cookie」按钮验证是否有效。"
                )
            else:
                self.logger.warning(f"Cookie 获取失败: {message}")
                self.update_status_message(f"Cookie 获取失败: {message}")
                
        except Exception as e:
            self.logger.error(f"处理登录结果失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"处理登录结果失败:\n{str(e)}")
            self.update_status_message("处理登录结果失败")
    
    def browse_cookie_file(self):
        """浏览Cookie文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Cookie文件",
            "",
            "Netscape Cookie文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            self.cookie_file_input.setText(file_path)
            self.load_cookie_content(file_path)
    
    def load_cookie_content(self, file_path: str):
        """加载Cookie内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.cookie_content.setText(content)
                self.update_status_message("Cookie文件加载成功")
        except Exception as e:
            self.logger.error(f"加载Cookie文件失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载Cookie文件失败:\n{str(e)}")
            self.update_status_message("Cookie文件加载失败")
    
    def update_status_message(self, message: str):
        """更新状态栏消息"""
        if self.status_bar:
            self.status_bar.showMessage(message)
    
    def update_cookie_status(self, is_using: bool):
        """更新Cookie使用状态"""
        self.cookie_status = "使用中" if is_using else "未使用"
        
        # 设置状态文本样式
        if is_using:
            status_style = "color: #2ecc71; font-weight: bold;"  # 绿色
        else:
            status_style = "color: #e74c3c; font-weight: bold;"  # 红色
        
        self.status_label.setText(f'<span style="{status_style}">当前状态：{self.cookie_status}</span>')
        
        # 更新状态栏
        self.update_status_message(f"Cookie状态已更新：{self.cookie_status}")
    
    def get_cookie_file(self) -> str:
        """获取当前Cookie文件路径"""
        return self.cookie_file_input.text()
    
    def is_cookie_available(self) -> bool:
        """检查Cookie是否可用"""
        return bool(self.cookie_file_input.text() and os.path.exists(self.cookie_file_input.text())) 