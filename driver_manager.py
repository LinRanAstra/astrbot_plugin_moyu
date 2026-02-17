import os
import platform
from typing import Optional


class DriverManager:
    """
    跨平台驱动管理器，用于根据操作系统自动选择合适的chromedriver
    """

    @staticmethod
    def get_chromedriver_path():
        """根据操作系统获取chromedriver路径，按优先级顺序：固定路径 -> webdriver-manager -> 系统环境变量"""
        # 首先尝试固定路径
        fixed_path = DriverManager._get_fixed_chromedriver_path()
        if fixed_path and os.path.exists(fixed_path):
            return fixed_path
        
        # 然后尝试webdriver-manager
        managed_path = DriverManager._get_webdriver_manager_path()
        if managed_path:
            return managed_path
            
        # 最后返回None，让selenium使用系统PATH中的驱动
        return None

    @staticmethod
    def _get_fixed_chromedriver_path():
        """根据操作系统获取固定路径下的 chromedriver 路径"""
        system = platform.system().lower()

        if system == "windows":
            # Windows 系统使用 chromedriver.exe，固定路径在 chrome-win64 目录
            chromedriver_filename = "chromedriver.exe"
            chromedriver_folder = "chromedriver-win64"
        elif system == "linux":
            # Linux 系统使用 chromedriver (通常没有扩展名)，固定路径在 chrome-linux64 目录
            chromedriver_filename = "chromedriver"
            chromedriver_folder = "chromedriver-linux64"
        elif system == "darwin":  # macOS
            # macOS 也使用 chromedriver (通常没有扩展名)
            chromedriver_filename = "chromedriver"
            chromedriver_folder = "chromedriver-mac64"
        else:
            return None

        # 固定路径搜索顺序：
        # 1. 项目根目录下的 drivers/{platform} 目录
        # 2. 插件目录下的 drivers/{platform} 目录
        fixed_paths = [
            os.path.join(os.getcwd(), "drivers", chromedriver_folder, chromedriver_filename),
            os.path.join(os.path.dirname(__file__), "drivers", chromedriver_folder, chromedriver_filename),
        ]

        for path in fixed_paths:
            # 规范化路径以处理可能的 .. 组件
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                return normalized_path

        return None

    @staticmethod
    def _get_webdriver_manager_path():
        """使用webdriver-manager获取chromedriver路径"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.utils import ChromeType
            # 根据操作系统类型决定Chrome类型
            system = platform.system().lower()
            if system in ["windows", "linux", "darwin"]:
                # 尝试获取最新版本的chromedriver
                path = ChromeDriverManager().install()
                return path
        except ImportError:
            # 如果webdriver-manager未安装，则返回None
            print("webdriver-manager未安装，跳过使用此方式获取驱动")
            return None
        except Exception as e:
            # 如果获取驱动过程中出现错误，记录错误并返回None
            print(f"通过webdriver-manager获取驱动时出错: {e}")
            return None
        return None

    @staticmethod
    def get_chrome_browser_path():
        """根据操作系统获取固定路径下的Chrome浏览器路径"""
        system = platform.system().lower()

        if system == "windows":
            # Windows 系统使用 chrome.exe，固定路径在 chrome-win64 目录
            chrome_filename = "chrome.exe"
            chrome_folder = "chrome-win64"
        elif system == "linux":
            # Linux 系统使用 chrome，固定路径在 chrome-linux64 目录
            chrome_filename = "chrome"
            chrome_folder = "chrome-linux64"
        elif system == "darwin":  # macOS
            # macOS 系统使用 Chrome 应用程序，固定路径在 chrome-mac 目录
            chrome_filename = "Google Chrome.app/Contents/MacOS/Google Chrome"
            chrome_folder = "chrome-mac"
        else:
            return None

        # 固定路径搜索顺序：
        # 1. 项目根目录下的 drivers/{platform} 目录
        # 2. 插件目录下的 drivers/{platform} 目录
        fixed_paths = [
            os.path.join(os.getcwd(), "drivers", chrome_folder, chrome_filename),
            os.path.join(os.path.dirname(__file__), "drivers", chrome_folder, chrome_filename),
        ]

        for path in fixed_paths:
            # 规范化路径
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                return normalized_path

        return None

    @staticmethod
    def get_driver_path_info():
        """获取驱动路径的详细信息，用于调试"""
        system = platform.system().lower()
        chromedriver_path = DriverManager.get_chromedriver_path()
        chrome_path = DriverManager.get_chrome_browser_path()

        info = {
            "system": system,
            "chromedriver_path": chromedriver_path,
            "chromedriver_exists": chromedriver_path is not None and os.path.exists(chromedriver_path) if chromedriver_path else False,
            "chrome_path": chrome_path,
            "chrome_exists": chrome_path is not None and os.path.exists(chrome_path) if chrome_path else False
        }

        return info


if __name__ == "__main__":
    print(DriverManager.get_driver_path_info())
    print("Chromedriver path:", DriverManager.get_chromedriver_path())
    print("Chrome browser path:", DriverManager.get_chrome_browser_path())