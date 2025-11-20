import asyncio
import sys
import signal
from typing import Optional

import cmd_arg
import config
from database import db
from base.base_crawler import AbstractCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.zhihu import ZhihuCrawler
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class CrawlerFactory:
    CRAWLERS = {
        "wb": WeiboCrawler,
        "zhihu": ZhihuCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported xhs or dy or ks or bili ..."
            )
        return crawler_class()


crawler: Optional[AbstractCrawler] = None


async def main():
    # Init crawler
    global crawler

    # parse cmd
    args = await cmd_arg.parse_cmd()

    # init db
    if args.init_db:
        await db.init_db(args.init_db)
        print(f"Database {args.init_db} initialized successfully.")
        return  # Exit the main function cleanly

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()

    # Generate wordcloud after crawling is complete
    # Only for JSON save mode
    if config.SAVE_DATA_OPTION == "json" and config.ENABLE_GET_WORDCLOUD:
        try:
            file_writer = AsyncFileWriter(
                platform=config.PLATFORM,
                crawler_type=crawler_type_var.get()
            )
            await file_writer.generate_wordcloud_from_comments()
        except Exception as e:
            print(f"Error generating wordcloud: {e}")


async def async_cleanup():
    """异步清理函数，用于处理CDP浏览器等异步资源"""
    global crawler
    if crawler:
        # 检查并清理CDP浏览器
        if hasattr(crawler, 'cdp_manager') and crawler.cdp_manager:
            try:
                await crawler.cdp_manager.cleanup(force=True)  # 强制清理浏览器进程
            except Exception as e:
                # 只在非预期错误时打印
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] 清理CDP浏览器时出错: {e}")

        # 检查并清理标准浏览器上下文（仅在非CDP模式下）
        elif hasattr(crawler, 'browser_context') and crawler.browser_context:
            try:
                # 检查上下文是否仍然打开
                if hasattr(crawler.browser_context, 'pages'):
                    await crawler.browser_context.close()
            except Exception as e:
                # 只在非预期错误时打印
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] 关闭浏览器上下文时出错: {e}")

    # 关闭数据库连接
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.close()


def cleanup():
    """同步清理函数"""
    try:
        # 创建新的事件循环来执行异步清理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_cleanup())
        loop.close()
    except Exception as e:
        print(f"[Main] 清理时出错: {e}")


def signal_handler(signum, _frame):
    """信号处理器，处理Ctrl+C等中断信号"""
    print(f"\n[Main] 收到中断信号 {signum}，正在清理资源...")
    cleanup()
    sys.exit(0)


if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\n[Main] 收到键盘中断，正在清理资源...")
    finally:
        cleanup()
