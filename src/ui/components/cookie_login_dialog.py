"""
YouTube Cookie 登录对话框
使用 PyQt5 WebEngineView 内置浏览器让用户登录 Google/YouTube
"""
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Callable
from http.cookiejar import MozillaCookieJar, Cookie

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QByteArray
from PyQt5.QtGui import QIcon

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
    from PyQt5.QtWebEngineCore import QWebEngineCookieStore
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

from src.utils.logger import LoggerManager


class CookieLoginDialog(QDialog):
    """
    Cookie 登录对话框
    
    使用内置 WebView 让用户登录 Google 账户，
    自动收集 YouTube 相关的 Cookie。
    """
    
    # 信号：登录完成 (success, cookie_file_path, message)
    login_finished = pyqtSignal(bool, str, str)
    
    # YouTube 相关域名
    YOUTUBE_DOMAINS = [
        '.youtube.com',
        'youtube.com',
        '.google.com',
        'google.com',
        '.googlevideo.com',
        'googlevideo.com',
        '.accounts.google.com',
        'accounts.google.com',
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = LoggerManager().get_logger()
        self.cookies: List[dict] = []
        self.cookie_file_path: Optional[str] = None
        self._login_detected = False
        
        self.setWindowTitle("登录 YouTube")
        self.setMinimumSize(900, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部提示栏
        tip_bar = QHBoxLayout()
        tip_bar.setContentsMargins(15, 10, 15, 10)
        
        tip_label = QLabel("请在下方登录您的 Google 账户，登录成功后点击「完成登录」按钮")
        tip_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 5px;
                background-color: #f8f9fa;
                border-left: 3px solid #007bff;
            }
        """)
        tip_bar.addWidget(tip_label)
        tip_bar.addStretch()
        
        # Cookie 计数器
        self.cookie_count_label = QLabel("已收集: 0 个 Cookie")
        self.cookie_count_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
                padding: 5px;
            }
        """)
        tip_bar.addWidget(self.cookie_count_label)
        
        layout.addLayout(tip_bar)
        
        # 检查 WebEngine 是否可用
        if not WEBENGINE_AVAILABLE:
            error_label = QLabel("PyQtWebEngine 未安装\n\n请运行以下命令安装：\npip install PyQtWebEngine")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-size: 16px;
                    padding: 50px;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                }
            """)
            layout.addWidget(error_label)
        else:
            # WebView
            self.web_view = QWebEngineView()
            self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # 设置 Cookie 监听
            self.profile = QWebEngineProfile.defaultProfile()
            self.cookie_store = self.profile.cookieStore()
            self.cookie_store.cookieAdded.connect(self._on_cookie_added)
            
            # 监听 URL 变化以检测登录状态
            self.web_view.urlChanged.connect(self._on_url_changed)
            
            layout.addWidget(self.web_view)
        
        # 底部按钮栏
        button_bar = QHBoxLayout()
        button_bar.setContentsMargins(15, 10, 15, 10)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #27ae60; font-size: 12px;")
        button_bar.addWidget(self.status_label)
        
        button_bar.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                font-size: 13px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #f8f9fa;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        self.refresh_btn.clicked.connect(self._refresh_page)
        button_bar.addWidget(self.refresh_btn)
        
        # 按钮间距
        button_bar.addSpacing(10)
        
        # 完成按钮
        self.finish_btn = QPushButton("完成登录")
        self.finish_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 28px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                background-color: #28a745;
                color: white;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #94d3a2;
            }
        """)
        self.finish_btn.clicked.connect(self._finish_login)
        button_bar.addWidget(self.finish_btn)
        
        # 按钮间距
        button_bar.addSpacing(10)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                font-size: 13px;
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                color: #dc3545;
            }
            QPushButton:hover {
                background-color: #dc3545;
                color: white;
            }
            QPushButton:pressed {
                background-color: #c82333;
                color: white;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_bar.addWidget(self.cancel_btn)
        
        layout.addLayout(button_bar)
        
    def start_login(self):
        """开始登录流程"""
        if not WEBENGINE_AVAILABLE:
            self.logger.error("PyQtWebEngine 未安装")
            return
            
        self.cookies.clear()
        self._login_detected = False
        self.status_label.setText("")
        self._update_cookie_count()
        
        # 清除旧的 Cookie（可选）
        # self.cookie_store.deleteAllCookies()
        
        # 加载 Google 登录页面
        self.web_view.load(QUrl("https://accounts.google.com/ServiceLogin?continue=https://www.youtube.com/"))
        self.logger.info("开始 WebView 登录流程")
        
    def _on_cookie_added(self, cookie):
        """Cookie 添加回调"""
        domain = cookie.domain()
        
        # 检查是否是 YouTube 相关域名
        is_youtube_related = any(
            yt_domain in domain or domain.endswith(yt_domain)
            for yt_domain in self.YOUTUBE_DOMAINS
        )
        
        if is_youtube_related:
            cookie_dict = {
                'name': cookie.name().data().decode('utf-8', errors='ignore'),
                'value': cookie.value().data().decode('utf-8', errors='ignore'),
                'domain': domain,
                'path': cookie.path(),
                'secure': cookie.isSecure(),
                'httpOnly': cookie.isHttpOnly(),
                'expiry': cookie.expirationDate().toSecsSinceEpoch() if cookie.expirationDate().isValid() else 0
            }
            
            # 避免重复添加
            existing = next(
                (c for c in self.cookies 
                 if c['name'] == cookie_dict['name'] and c['domain'] == cookie_dict['domain']),
                None
            )
            
            if existing:
                # 更新现有 cookie
                existing.update(cookie_dict)
            else:
                self.cookies.append(cookie_dict)
            
            self._update_cookie_count()
            
    def _on_url_changed(self, url: QUrl):
        """URL 变化回调，用于检测登录状态"""
        url_str = url.toString()
        self.logger.debug(f"URL 变化: {url_str}")
        
        # 检测是否已登录到 YouTube
        if 'youtube.com' in url_str and 'accounts.google.com' not in url_str:
            if not self._login_detected:
                self._login_detected = True
                self.status_label.setText("✅ 检测到已登录 YouTube")
                self.status_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
                self.logger.info("检测到 YouTube 登录成功")
                
    def _update_cookie_count(self):
        """更新 Cookie 计数显示"""
        count = len(self.cookies)
        self.cookie_count_label.setText(f"已收集: {count} 个 Cookie")
        
        if count > 0:
            self.cookie_count_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
            
    def _refresh_page(self):
        """刷新页面"""
        if WEBENGINE_AVAILABLE:
            self.web_view.reload()
            
    def _finish_login(self):
        """完成登录，保存 Cookie"""
        if not self.cookies:
            reply = QMessageBox.warning(
                self,
                "警告",
                "未收集到任何 Cookie。\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 检查是否包含关键 Cookie
        cookie_names = [c['name'] for c in self.cookies]
        has_login_cookie = any(name in cookie_names for name in ['SID', 'SSID', 'HSID', 'LOGIN_INFO'])
        
        if not has_login_cookie:
            reply = QMessageBox.warning(
                self,
                "警告", 
                "未检测到登录相关的 Cookie。\n可能尚未完成登录。\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        try:
            # 保存 Cookie 到文件
            self.cookie_file_path = self._save_cookies_to_file()
            self.logger.info(f"Cookie 已保存到: {self.cookie_file_path}")
            
            self.login_finished.emit(True, self.cookie_file_path, "Cookie 获取成功")
            self.accept()
            
        except Exception as e:
            self.logger.error(f"保存 Cookie 失败: {e}")
            QMessageBox.critical(self, "错误", f"保存 Cookie 失败:\n{str(e)}")
            self.login_finished.emit(False, "", f"保存失败: {str(e)}")
            
    def _save_cookies_to_file(self) -> str:
        """
        将收集的 Cookie 保存为 Netscape 格式文件
        
        Returns:
            保存的文件路径
        """
        # 创建 Cookie 文件
        cookie_file = os.path.join(os.getcwd(), 'youtube_cookies.txt')
        
        # 创建 MozillaCookieJar
        cookie_jar = MozillaCookieJar(cookie_file)
        
        for cookie_data in self.cookies:
            try:
                # 处理域名格式
                domain = cookie_data['domain']
                domain_initial_dot = domain.startswith('.')
                
                # 创建 Cookie 对象
                cookie = Cookie(
                    version=0,
                    name=cookie_data['name'],
                    value=cookie_data['value'],
                    port=None,
                    port_specified=False,
                    domain=domain,
                    domain_specified=True,
                    domain_initial_dot=domain_initial_dot,
                    path=cookie_data['path'],
                    path_specified=True,
                    secure=cookie_data.get('secure', False),
                    expires=cookie_data.get('expiry', 0),
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest={'HttpOnly': cookie_data.get('httpOnly', False)},
                    rfc2109=False
                )
                cookie_jar.set_cookie(cookie)
            except Exception as e:
                self.logger.warning(f"处理 Cookie {cookie_data.get('name', 'unknown')} 时出错: {e}")
                continue
        
        # 保存到文件
        cookie_jar.save(ignore_discard=True, ignore_expires=True)
        
        return cookie_file
    
    def get_cookie_file_path(self) -> Optional[str]:
        """获取保存的 Cookie 文件路径"""
        return self.cookie_file_path
    
    def closeEvent(self, event):
        """关闭事件"""
        if WEBENGINE_AVAILABLE:
            # 停止加载
            self.web_view.stop()
        super().closeEvent(event)


def is_webengine_available() -> bool:
    """检查 WebEngine 是否可用"""
    return WEBENGINE_AVAILABLE
