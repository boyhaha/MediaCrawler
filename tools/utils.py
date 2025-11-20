# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import argparse
import logging

from .crawler_util import *
from .slider_util import *
from .time_util import *


# app/core/logger.py
import sys
from loguru import logger as loguru_logger

def init_loging_config():
    level = logging.INFO

    # ------------------ loguru 文件输出 ------------------
    loguru_logger.remove()  # 移除默认 handler

    # 文件日志，保留14天
    loguru_logger.add(
        "logs/media_crawler.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="1 day",
        retention="14 days",
        encoding="utf-8"
    )

    # ------------------ logging 拦截到 loguru ------------------
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # 获取 loguru 对象，并保持原调用堆栈深度
            logger_opt = loguru_logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(record.levelname, record.getMessage())

    logging.basicConfig(
        handlers=[InterceptHandler(), logging.StreamHandler(sys.stdout)],  # 控制台依然输出
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )

    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)

    # httpx 只显示 WARNING 及以上
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return _logger


logger = init_loging_config()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
