"""
YouTube 視頻下載工具的格式轉換模塊
負責處理視頻格式轉換和質量選擇
"""
import os
import subprocess
import re
import json
from typing import List, Dict, Tuple, Optional


class FormatConverter:
    """格式轉換類"""
    
    def __init__(self, ffmpeg_path: str = None):
        """
        初始化格式轉換器
        
        Args:
            ffmpeg_path: ffmpeg 可執行文件路徑，如果為 None 則使用內置路徑
        """
        # 獲取當前腳本所在目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 設置 ffmpeg 路徑
        self.ffmpeg_path = ffmpeg_path or os.path.join(base_dir, 'resources', 'binaries', 'ffmpeg', 'ffmpeg.exe')
    
    def convert_to_mp4(self, input_file: str, output_file: str = None) -> Tuple[bool, str]:
        """
        將視頻轉換為 MP4 格式
        
        Args:
            input_file: 輸入文件路徑
            output_file: 輸出文件路徑，如果為 None 則自動生成
            
        Returns:
            (成功標誌, 輸出文件路徑或錯誤信息)
        """
        if not os.path.exists(input_file):
            return False, f"輸入文件不存在: {input_file}"
        
        # 如果未指定輸出文件，則自動生成
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}.mp4"
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-c:v', 'libx264',  # 使用 H.264 編碼
                '-c:a', 'aac',      # 使用 AAC 音頻編碼
                '-movflags', '+faststart',  # 優化網絡播放
                '-y',               # 覆蓋現有文件
                output_file
            ]
            
            # 執行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, output_file
            else:
                return False, f"轉換失敗: {result.stderr}"
        except Exception as e:
            return False, f"轉換過程中發生錯誤: {str(e)}"
    
    def extract_audio(self, input_file: str, output_format: str = 'mp3', output_file: str = None) -> Tuple[bool, str]:
        """
        從視頻中提取音頻
        
        Args:
            input_file: 輸入文件路徑
            output_format: 輸出音頻格式，默認為 mp3
            output_file: 輸出文件路徑，如果為 None 則自動生成
            
        Returns:
            (成功標誌, 輸出文件路徑或錯誤信息)
        """
        if not os.path.exists(input_file):
            return False, f"輸入文件不存在: {input_file}"
        
        # 如果未指定輸出文件，則自動生成
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}.{output_format}"
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-vn',              # 不包含視頻
                '-acodec', 'libmp3lame' if output_format == 'mp3' else 'copy',
                '-y',               # 覆蓋現有文件
                output_file
            ]
            
            # 執行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, output_file
            else:
                return False, f"提取音頻失敗: {result.stderr}"
        except Exception as e:
            return False, f"提取音頻過程中發生錯誤: {str(e)}"
    
    def get_video_info(self, video_file: str) -> Dict:
        """
        獲取視頻文件信息
        
        Args:
            video_file: 視頻文件路徑
            
        Returns:
            視頻信息字典
        """
        if not os.path.exists(video_file):
            return {}
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_file,
                '-hide_banner'
            ]
            
            # 執行命令（預期會失敗，因為只是獲取信息）
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 解析輸出
            info = {}
            
            # 提取時長
            duration_match = re.search(r'Duration: (\d{2}:\d{2}:\d{2}\.\d{2})', result.stderr)
            if duration_match:
                info['duration'] = duration_match.group(1)
            
            # 提取視頻編碼
            video_codec_match = re.search(r'Video: (\w+)', result.stderr)
            if video_codec_match:
                info['video_codec'] = video_codec_match.group(1)
            
            # 提取分辨率
            resolution_match = re.search(r'(\d+x\d+)', result.stderr)
            if resolution_match:
                info['resolution'] = resolution_match.group(1)
            
            # 提取音頻編碼
            audio_codec_match = re.search(r'Audio: (\w+)', result.stderr)
            if audio_codec_match:
                info['audio_codec'] = audio_codec_match.group(1)
            
            return info
        except Exception as e:
            return {}
    
    def format_quality_label(self, format_info: Dict) -> str:
        """
        格式化質量標籤
        
        Args:
            format_info: 格式信息字典
            
        Returns:
            格式化的質量標籤
        """
        resolution = format_info.get('resolution', '?x?')
        format_note = format_info.get('format_note', '')
        ext = format_info.get('ext', '')
        
        # 計算大小（如果有）
        size_str = ''
        if format_info.get('filesize'):
            size_mb = format_info['filesize'] / (1024 * 1024)
            size_str = f" - {size_mb:.1f}MB"
        
        # 格式化標籤
        if format_note:
            return f"{resolution} ({format_note}) [{ext}]{size_str}"
        else:
            return f"{resolution} [{ext}]{size_str}"
    
    def get_best_quality_format(self, formats: List[Dict], prefer_mp4: bool = True) -> str:
        """
        獲取最佳質量格式
        
        Args:
            formats: 格式列表
            prefer_mp4: 是否優先選擇 MP4 格式
            
        Returns:
            最佳格式的 format_id
        """
        if not formats:
            return 'best'
        
        # 如果優先選擇 MP4 格式
        if prefer_mp4:
            # 先嘗試找到最高分辨率的 MP4 格式
            mp4_formats = [f for f in formats if f.get('ext') == 'mp4']
            if mp4_formats:
                return mp4_formats[0]['format_id']
        
        # 如果沒有找到合適的 MP4 格式或不優先選擇 MP4，則返回最高分辨率的格式
        return formats[0]['format_id'] if formats else 'best'
