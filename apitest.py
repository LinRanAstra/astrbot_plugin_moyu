from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from astrbot.api import logger
from .playwright_manager import get_browser


async def capture_poster_without_obstacle(
    url, output_path="poster_clean.png", timeout=30000
):
    """异步版本：使用 Playwright 打开页面、移除遮挡并对 #poster 元素截图。"""
    browser = await get_browser("chromium")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            await page.goto(url, wait_until="networkidle", timeout=timeout)
            logger.info(f"已加载页面: {url}")

            # 步骤1：尝试移除已知遮挡元素
            try:
                locator = page.locator("xpath=/html/body/div[1]/div[2]/div[2]")
                await locator.evaluate("el => el.remove()")
                logger.info("尝试移除遮挡元素（如存在）")
            except Exception:
                logger.debug("遮挡元素未找到或移除失败，继续")

            # 步骤2：等待目标元素并截图
            try:
                await page.wait_for_selector(
                    "#poster", state="visible", timeout=timeout
                )
                poster = page.locator("#poster")
                await poster.scroll_into_view_if_needed()
                await poster.screenshot(path=output_path)
                logger.info(f"已保存截图: {output_path}")
                return output_path
            except PlaywrightTimeoutError as e:
                logger.error(f"等待目标元素超时: {e}")
                try:
                    await page.screenshot(path="debug_fullpage.png", full_page=True)
                    logger.info("已保存调试图: debug_fullpage.png")
                except Exception:
                    logger.debug("调试截图保存失败")
                return False
    except Exception as e:
        logger.error(f"Playwright 运行失败: {e}")
        return False
    # 使用 try/finally 确保即使出错也能关闭浏览器
    finally:
        for resource in [page, context]:
            if resource:
                try:
                    if hasattr(resource, "is_closed") and resource.is_closed():
                        continue
                    await resource.close()
                except Exception as e:
                    # 📝 仅记录 warning，不 re-raise
                    logger.warning(f"清理资源 {type(resource).__name__} 时警告: {e}")

        # 2. 再关闭 context（会自动关闭其下所有 pages）
        # if context and not context.is_closed():
        #     try:
        #         await context.close()
        #     except Exception as e:
        #         logger.warning(f"关闭 context 失败: {e}")

        # 3. 【关键】仅当 browser 是本函数内创建的局部单例时才关闭
        #    如果 browser 是插件全局单例，注释掉下面这段！
        # if browser and browser.is_connected() and _is_local_browser:
        #     try:
        #         await browser.close()
        #     except Exception as e:
        #         logger.warning(f"关闭 browser 失败: {e}")


if __name__ == "__main__":
    target_url = "https://moyu.ranawa.com"  # 替换为实际网址
    success = capture_poster_without_obstacle(target_url)
    if success:
        print("截图成功！")
        print("截图保存在:", success)
    else:
        print("截图失败，请检查错误信息")
