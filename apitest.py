import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from astrbot.api import logger

from .driver_manager import DriverManager


def capture_poster_without_obstacle(url, output_path="poster_clean.png"):
    # 浏览器配置（无头 + 固定窗口）
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 获取适合当前系统的 chromedriver 路径
    chromedriver_path = DriverManager.get_chromedriver_path()
    chrome_options.binary_location = DriverManager.get_chrome_browser_path()  # 获取 Chrome 浏览器路径（如果需要指定）
    try:
        if chromedriver_path:
            # 使用找到的特定路径的 chromedriver
            driver = webdriver.Chrome(
                service=Service(executable_path=chromedriver_path),
                options=chrome_options,
            )
        else:
            # 如果没有找到特定路径的 chromedriver，则尝试使用系统 PATH 中的
            logger.warning("未找到预置的 chromedriver，尝试使用系统 PATH 中的版本")
            driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        logger.warning(f"使用自定义 chromedriver 失败，尝试使用系统 PATH 中的驱动: {e}")
        try:
            driver = webdriver.Chrome(options=chrome_options)  # 回退方案
        except Exception as e2:
            logger.error(f"所有 Chrome 驱动加载方法均失败: {e2}")
            raise

    try:
        driver.get(url)
        logger.info(f"已加载页面: {url}")
        time.sleep(1.5)  # 基础加载等待（可配合显式等待优化）

        # ============ 步骤1：安全移除遮挡元素 ============
        remove_script = """
            const xpath = '/html/body/div[1]/div[2]/div[2]';
            const result = document.evaluate(
                xpath, document, null,
                XPathResult.FIRST_ORDERED_NODE_TYPE, null
            );
            const el = result.singleNodeValue;
            if (el) {
                el.remove();  // 完全移除，不留占位
                return 'removed';
            }
            return 'not_found';
        """
        status = driver.execute_script(remove_script)
        logger.info(f"遮挡元素处理结果: {status}")

        # ============ 步骤2：等待并截图目标元素 ============
        # 等待元素存在且可见（避免被其他元素遮挡）
        poster = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="poster"]'))
        )
        logger.info("目标元素已就绪")

        # 滚动至视图中心（确保完整渲染）
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            poster,
        )
        time.sleep(0.8)  # 等待滚动与渲染稳定

        # 截图保存
        poster.screenshot(output_path)
        logger.info(f"元素尺寸: {poster.size}, 位置: {poster.location}")

        return output_path

    except Exception as e:
        logger.error(f"❌ 处理失败: {str(e)}")
        # 保存调试截图
        try:
            driver.save_screenshot("debug_fullpage.png")
            logger.info("已保存调试截图: debug_fullpage.png")
        except:
            pass
        return False

    finally:
        driver.quit()
        logger.info("浏览器已关闭")


# ============ 使用示例 ============
if __name__ == "__main__":
    target_url = "https://zhou75i.github.io/moyu/"  # 替换为实际网址
    success = capture_poster_without_obstacle(target_url)
    if success:
        print("截图成功！")
        print("截图保存在:", success)
    else:
        print("截图失败，请检查错误信息")
