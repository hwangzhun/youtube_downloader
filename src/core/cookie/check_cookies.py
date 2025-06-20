import requests
import os
from typing import Dict, Optional, Tuple
import re

from src.utils.logger import LoggerManager

logger = LoggerManager().get_logger()

def parse_netscape_cookies(file_path: str) -> Dict[str, str]:
    """
    解析 Netscape 格式的 cookie 文件
    
    Args:
        file_path: cookie 文件路径
        
    Returns:
        Dict[str, str]: cookie 字典
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式错误
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cookie 文件不存在: {file_path}")
        
    cookies = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) == 7:
                    domain, flag, path, secure, expiry, name, value = parts
                    cookies[name] = value
                    
        # 移除对特定cookie字段的检查
        return cookies
    except Exception as e:
        raise ValueError(f"解析 cookie 文件失败: {str(e)}")

def verify_cookie(cookie_file: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    验证 cookie 是否有效，并返回用户 ID 和用户名
    
    Args:
        cookie_file: cookie 文件路径
        
    Returns:
        Tuple[bool, str, Optional[str], Optional[str]]: (是否有效, 错误信息, 用户ID, 用户名)
    """
    try:
        # 解析 cookie 文件
        cookies = parse_netscape_cookies(cookie_file)
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.youtube.com/'
        }
        
        # 访问用户个人页面
        response = requests.get(
            'https://www.youtube.com/feed/you',
            headers=headers,
            cookies=cookies,
            timeout=10
        )
        
        # 保存响应内容到文件
        with open('youtube_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.debug("响应内容已保存到 youtube_response.html")
        
        # 检查响应状态
        if response.status_code != 200:
            return False, f"请求失败，状态码: {response.status_code}", None, None
            
        # 检查是否重定向到登录页面
        if "accounts.google.com/signin" in response.url:
            return False, "Cookie 已过期，需要重新登录", None, None
            
        # 检查页面内容
        if "Sign in" in response.text:
            return False, "Cookie 无效，未登录", None, None
            
        # 从保存的文件中读取内容
        with open('youtube_response.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 从页面内容中提取用户 ID 和用户名
        # 匹配格式: [{"metadataParts":[{"text":{"content":"@用户名"}},{"text":{"content":"查看频道","commandRuns":[{"startIndex":0,"length":12,"onTap":{"innertubeCommand":{"clickTrackingParams":"...","commandMetadata":{"webCommandMetadata":{"url":"/channel/频道ID"
        username_pattern = r'"content":"@([^"]+)"'
        channel_id_pattern = r'"url":"/channel/([^"]+)"'
        
        username_match = re.search(username_pattern, content)
        channel_id_match = re.search(channel_id_pattern, content)
        
        if channel_id_match:
            user_id = channel_id_match.group(1)
            if username_match:
                username = username_match.group(1)
                logger.info(f"成功获取到用户信息: @{username}")
                logger.info(f"频道ID: {user_id}")
                return True, "Cookie 有效", user_id, username
            else:
                logger.info("无法获取用户名")
                return False, "无法获取用户名", user_id, None
        else:
            logger.info("无法获取频道ID")
            return False, "无法获取频道ID", None, None
            
    except Exception as e:
        return False, f"验证过程出错: {str(e)}", None, None

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='验证 YouTube Cookie 文件')
    parser.add_argument(
        '--cookie-file', 
        type=str,
        default='youtube_cookies.txt',
        help='Cookie 文件路径 (默认: youtube_cookies.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        is_valid, message, user_id, username = verify_cookie(args.cookie_file)
        if is_valid:
            logger.info("✅ " + message)
            logger.info("用户 ID: " + str(user_id))
            logger.info("用户名: " + str(username))
        else:
            logger.info("❌ " + message)
    except Exception as e:
        logger.error(f"❌ 验证失败: {str(e)}")

if __name__ == "__main__":
    main()
