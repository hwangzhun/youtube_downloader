import undetected_chromedriver as uc
import time
import os
from http.cookiejar import MozillaCookieJar, Cookie
import logging
import json
import tkinter as tk
from tkinter import messagebox

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def show_success_message(cookie_count):
    """显示成功消息框"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 构建详细的消息内容
    message = f"""Cookie 已成功保存！

详细信息：
- 获取到 {cookie_count} 个 cookies
- 保存位置：youtube_cookies.txt
- 格式：Netscape 格式

您现在可以关闭此窗口。"""
    
    messagebox.showinfo("Cookie 获取成功", message)
    root.destroy()

def get_youtube_cookies():
    """通过浏览器窗口获取 YouTube cookies"""
    try:
        # 创建 Chrome 选项
        options = uc.ChromeOptions()
        
        # 添加更多选项来模拟真实浏览器
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        
        # 使用自动版本管理
        driver = uc.Chrome(
            options=options,
            version_main=136  # 指定您当前的 Chrome 版本
        )
        
        try:
            # 访问 YouTube
            driver.get('https://www.youtube.com')
            
            # 等待用户登录
            logger.info("请在浏览器中登录 YouTube...")
            logger.info("登录成功后，程序将自动获取 cookies")
            
            # 等待用户登录完成
            max_wait_time = 300  # 最多等待5分钟
            start_time = time.time()
            is_logged_in = False
            
            while time.time() - start_time < max_wait_time:
                try:
                    # 检查是否已登录
                    # 1. 检查是否存在登录按钮
                    sign_in_button = driver.find_elements("xpath", "//a[contains(@href, 'accounts.google.com/signin')]")
                    # 2. 检查是否存在用户头像
                    avatar = driver.find_elements("xpath", "//button[@id='avatar-btn']")
                    
                    if not sign_in_button and avatar:
                        is_logged_in = True
                        logger.info("检测到已登录，正在获取 cookies...")
                        break
                        
                    time.sleep(1)
                except Exception as e:
                    logger.debug(f"检查登录状态时出错: {str(e)}")
                    time.sleep(1)
                    continue
            
            if not is_logged_in:
                logger.error("❌ 等待登录超时，请确保已成功登录")
                return False
            
            # 获取所有 cookies
            cookies = driver.get_cookies()
            if not cookies:
                logger.error("❌ 未获取到任何 cookies")
                return False
                
            cookie_count = len(cookies)
            logger.info(f"✅ 成功获取到 {cookie_count} 个 cookies")
            
            # 创建 cookie jar
            cookie_jar = MozillaCookieJar('youtube_cookies.txt')
            
            # 处理每个 cookie
            for cookie in cookies:
                try:
                    # 创建 Cookie 对象
                    c = Cookie(
                        version=0,
                        name=cookie['name'],
                        value=cookie['value'],
                        port=None,
                        port_specified=False,
                        domain=cookie['domain'],
                        domain_specified=True,
                        domain_initial_dot=cookie['domain'].startswith('.'),
                        path=cookie['path'],
                        path_specified=True,
                        secure=cookie.get('secure', False),
                        expires=cookie.get('expiry', 0),
                        discard=False,
                        comment=None,
                        comment_url=None,
                        rest={'HttpOnly': cookie.get('httpOnly', False)},
                        rfc2109=False
                    )
                    cookie_jar.set_cookie(c)
                except Exception as e:
                    logger.debug(f"处理cookie {cookie.get('name', 'unknown')} 时出错: {str(e)}")
                    continue
            
            # 保存 cookies
            cookie_jar.save(ignore_discard=True, ignore_expires=True)
            logger.info("✅ Cookie 已保存为 Netscape 格式！")
            
            # 显示成功消息
            show_success_message(cookie_count)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 获取 Cookie 时出错: {str(e)}")
            return False
            
        finally:
            # 自动关闭浏览器
            try:
                driver.quit()
            except:
                pass
            
    except Exception as e:
        logger.error(f"❌ 启动浏览器时出错: {str(e)}")
        return False

if __name__ == '__main__':
    logger.info("正在启动浏览器获取 YouTube Cookie...")
    get_youtube_cookies()