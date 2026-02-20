import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

from astrbot.core.utils.astrbot_path import get_astrbot_data_path

plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_moyu"
# 内部配置
_PLUGIN_DATA_PATH = plugin_data_path
_BROWSERS_PATH = _PLUGIN_DATA_PATH / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_BROWSERS_PATH)

# 内部缓存
_installed_browsers = None


def _ensure_installed(browser: Literal["chromium", "firefox", "webkit"] = "chromium"):
    """内部函数：确保指定浏览器已安装"""
    global _installed_browsers

    if _installed_browsers is None:
        _installed_browsers = (
            [
                folder.name.split("-")[0]
                for folder in _BROWSERS_PATH.iterdir()
                if folder.is_dir()
                and folder.name.split("-")[0] in ["chromium", "firefox", "webkit"]
            ]
            if _BROWSERS_PATH.exists()
            else []
        )

    if browser not in _installed_browsers:
        print(f"📦 正在安装 {browser}...")
        _BROWSERS_PATH.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", browser], check=True
        )
        _installed_browsers.append(browser)
        print(f"✅ {browser} 安装完成")


async def get_browser(
    browser: Literal["chromium", "firefox", "webkit"] = "chromium",
    launch_kwargs: Optional[dict] = None,
):
    """
    【公开函数】获取浏览器实例（如未安装则自动安装）

    :param browser: 浏览器类型
    :param launch_kwargs: 启动参数，如 headless、slow_mo 等
    :return: Playwright 浏览器实例
    """
    # from playwright.async_api import async_playwright

    _ensure_installed(browser)

    # launch_kwargs = launch_kwargs or {}
    # playwright = await async_playwright().start()

    # if browser == "chromium":
    #     return playwright.chromium.launch(**launch_kwargs), playwright
    # elif browser == "firefox":
    #     return playwright.firefox.launch(**launch_kwargs), playwright
    # elif browser == "webkit":
    #     return playwright.webkit.launch(**launch_kwargs), playwright
    # else:
    #     raise ValueError(f"不支持的浏览器类型: {browser}")


def uninstall(browser: Optional[Literal["chromium", "firefox", "webkit"]] = None):
    """
    【公开函数】卸载浏览器（删除对应文件夹）

    :param browser: 指定浏览器，如为 None 则卸载所有
    """
    global _installed_browsers

    if not _BROWSERS_PATH.exists():
        print("ℹ️ 浏览器目录不存在，无需卸载")
        return

    if browser:
        browsers_to_remove = [browser]
    else:
        browsers_to_remove = ["chromium", "firefox", "webkit"]

    for folder in _BROWSERS_PATH.iterdir():
        if folder.is_dir():
            folder_browser = folder.name.split("-")[0]
            if folder_browser in browsers_to_remove:
                shutil.rmtree(folder)
                print(f"🗑️ 已卸载: {folder.name}")
                if _installed_browsers and folder_browser in _installed_browsers:
                    _installed_browsers.remove(folder_browser)

    if not browser and not any(_BROWSERS_PATH.iterdir()):
        _BROWSERS_PATH.rmdir()
        print("🧹 浏览器目录已清空")
