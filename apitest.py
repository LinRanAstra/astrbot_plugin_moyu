from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from astrbot.api import logger


def capture_poster_without_obstacle(url, output_path="poster_clean.png", timeout=30000):
    """使用 Playwright 打开页面、移除遮挡并对 #poster 元素截图。

    返回截图路径或 False（失败）。
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            page.goto(url, wait_until="networkidle", timeout=timeout)
            logger.info(f"已加载页面: {url}")

            # 步骤1：尝试移除已知遮挡元素（安全地忽略不存在情况）
            try:
                page.locator("xpath=/html/body/div[1]/div[2]/div[2]").evaluate(
                    "el => el.remove()"
                )
                logger.info("尝试移除遮挡元素（如存在）")
            except Exception:
                logger.debug("遮挡元素未找到或移除失败，继续")

            # 步骤2：等待目标元素可见并截图
            try:
                page.wait_for_selector("#poster", state="visible", timeout=timeout)
                poster = page.locator("#poster")
                poster.scroll_into_view_if_needed()
                poster.screenshot(path=output_path)
                logger.info(f"已保存截图: {output_path}")
                return output_path
            except PlaywrightTimeoutError as e:
                logger.error(f"等待目标元素超时: {e}")
                # 保存调试截图
                try:
                    page.screenshot(path="debug_fullpage.png", full_page=True)
                    logger.info("已保存调试调试图: debug_fullpage.png")
                except Exception:
                    logger.debug("调试截图保存失败")
                return False
            finally:
                context.close()
                browser.close()

    except Exception as e:
        logger.error(f"Playwright 运行失败: {e}")
        return False


if __name__ == "__main__":
    target_url = "https://moyu.ranawa.com"  # 替换为实际网址
    success = capture_poster_without_obstacle(target_url)
    if success:
        print("截图成功！")
        print("截图保存在:", success)
    else:
        print("截图失败，请检查错误信息")
