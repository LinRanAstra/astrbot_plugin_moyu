import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_moyu"
# 内部配置
_PLUGIN_DATA_PATH = plugin_data_path
_BROWSERS_PATH = _PLUGIN_DATA_PATH / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_BROWSERS_PATH)

# 内部缓存
_installed_browsers = None
_deps_checked = False


def _check_system_deps(
    browser: Literal["chromium", "firefox", "webkit"] = "chromium",
) -> bool:
    """
    检查系统依赖是否完整
    :return: True 如果依赖完整，False 如果缺失
    """
    # 1. 先检查浏览器二进制是否存在
    browser_bin = _get_browser_binary_path(browser)
    if not browser_bin or not browser_bin.exists():
        return False  # 浏览器都没安装，谈不上依赖

    # 2. 使用 ldd 检查缺失的共享库
    try:
        result = subprocess.run(
            ["ldd", str(browser_bin)], capture_output=True, text=True, timeout=10
        )
        # 如果输出包含 "not found"，说明有依赖缺失
        if "not found" in result.stdout:
            missing_libs = [
                line.split("=>")[0].strip()
                for line in result.stdout.splitlines()
                if "not found" in line
            ]
            logger.warning(f"缺失系统依赖库：{missing_libs}")
            return False
        return True
    except Exception as e:
        logger.warning(f"检查系统依赖失败：{e}，假设依赖缺失")
        return False


def _get_browser_binary_path(
    browser: Literal["chromium", "firefox", "webkit"],
) -> Optional[Path]:
    """获取浏览器二进制文件路径"""
    if not _BROWSERS_PATH.exists():
        return None

    # 查找对应浏览器的目录
    for folder in _BROWSERS_PATH.iterdir():
        if folder.is_dir() and folder.name.startswith(browser):
            # 根据不同浏览器返回不同的二进制路径
            if browser == "chromium":
                binary = folder / "chrome-linux" / "chrome"
                if not binary.exists():
                    binary = (
                        folder
                        / "chrome-headless-shell-linux64"
                        / "chrome-headless-shell"
                    )
                return binary if binary.exists() else None
            elif browser == "firefox":
                binary = folder / "firefox" / "firefox"
                return binary if binary.exists() else None
            elif browser == "webkit":
                binary = folder / "minibrowser-gtk" / "MiniBrowser"
                return binary if binary.exists() else None

    return None


def _install_system_deps(
    browser: Literal["chromium", "firefox", "webkit"] = "chromium",
) -> bool:
    """
    安装系统依赖
    :return: True 如果安装成功，False 如果失败
    """
    logger.info(f"📦 正在安装 {browser} 的系统依赖...")

    try:
        # 方法 1：使用 playwright install-deps（推荐）
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install-deps", browser],
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
        )

        if result.returncode == 0:
            logger.info(f"✅ {browser} 系统依赖安装完成")
            return True
        else:
            logger.error(f"安装系统依赖失败：{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("安装系统依赖超时")
        return False
    except Exception as e:
        logger.error(f"安装系统依赖异常：{e}")
        return False


def _ensure_installed(browser: Literal["chromium", "firefox", "webkit"] = "chromium"):
    """
    内部函数：确保指定浏览器已安装 + 系统依赖完整
    """
    global _installed_browsers, _deps_checked

    # 1. 初始化已安装浏览器列表（缓存）
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

    # 2. 检查并安装系统依赖（每次启动检查一次）
    if not _deps_checked:
        if not _check_system_deps(browser):
            logger.warning("⚠️ 检测到系统依赖缺失，尝试自动安装...")
            if not _install_system_deps(browser):
                logger.error(
                    "❌ 系统依赖安装失败，请手动执行：playwright install-deps chromium"
                )
            else:
                logger.info("✅ 系统依赖安装成功")
        _deps_checked = True  # 标记已检查，避免重复

    # 3. 检查并安装浏览器
    if browser not in _installed_browsers:
        logger.info(f"📦 正在安装 {browser} 浏览器...")
        _BROWSERS_PATH.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", browser],
                check=True,
                timeout=600,  # 10 分钟超时
            )
            _installed_browsers.append(browser)
            logger.info(f"✅ {browser} 浏览器安装完成")
        except subprocess.TimeoutExpired:
            logger.error("安装浏览器超时")
            raise
        except Exception as e:
            logger.error(f"安装浏览器失败：{e}")
            raise


async def get_browser(
    browser: Literal["chromium", "firefox", "webkit"] = "chromium",
    launch_kwargs: Optional[dict] = None,
):
    """
    【公开函数】获取浏览器实例（如未安装则自动安装）

    :param browser: 指定浏览器类型
    :param launch_kwargs: 启动参数，如 headless, args 等
    :return: Browser 实例
    """
    from playwright.async_api import async_playwright

    # 1. 确保浏览器和依赖已安装
    _ensure_installed(browser)

    # 2. 启动浏览器
    async with async_playwright() as p:
        browser_type = getattr(p, browser)

        # 默认参数（Docker 环境必需）
        default_launch_kwargs = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ],
        }

        # 合并用户参数
        if launch_kwargs:
            default_launch_kwargs.update(launch_kwargs)

        # 3. 启动并返回
        browser_instance = await browser_type.launch(**default_launch_kwargs)
        return browser_instance


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
