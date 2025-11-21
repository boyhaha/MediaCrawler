"""
企业微信通知模块
"""
from enum import Enum
import requests
import logging
import config


class WeChatNotifier:
    """企业微信通知器"""

    def __init__(self):
        self.webhook_url = config.WEBHOOK
        self.logger = logging.getLogger(__name__)
        self.debug_mode = config.WEBHOOK_DEBUG_MODE

        if self.debug_mode:
            self.logger.warning("⚠️ 企业微信通知器运行在调试模式，不会发送实际消息")

    def send_message(self, content: str, mention_all: bool = False) -> bool:
        """
        发送消息到企业微信

        Args:
            content: 消息内容
            mention_all: 是否@所有人

        Returns:
            bool: 发送是否成功
        """
        if self.debug_mode:
            # 调试模式：只记录日志，不发送实际消息
            mention_text = "(@所有人)" if mention_all else ""
            self.logger.info(f"🧪 调试模式: 模拟发送企业微信消息{mention_text}: {content[:100]}...")
            return True

        # 构建消息体
        message_data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }

        # 如果需要@所有人，添加mentioned_list
        # if mention_all:
        #     message_data["markdown"]["mentioned_list"] = ["@all"]
        # 发送请求
        response = requests.post(self.webhook_url, json=message_data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            self.logger.info(f"发送完成: {result.get('errcode')}, {result.get('errmsg')}")
            if result.get("errcode") == 0:
                return True
            else:
                self.logger.error(f"消息发送失败: {result}")
        return False


class CONTENTS(Enum):
    ERROR = "### 错误通知\n爬取异常，请及时处理！\n [点击验证](https://m.weibo.cn/u/3592951597)\n"


# 全局通知器实例
notifier = WeChatNotifier()


def notify_final_error(retry_state):
    # 5 次失败后才会执行这里
    notifier.send_message(CONTENTS.ERROR.value, mention_all=False)


if __name__ == "__main__":
    # 测试通知功能 notification
    test_notifier = WeChatNotifier()
    content = "# 一、标题\n## 二级标题\n### 三级标题\n# 二、字体\n*斜体*\n\n**加粗**\n# 三、列表 \n- 无序列表 1 \n- 无序列表 2\n  - 无序列表 2.1\n  - 无序列表 2.2\n1. 有序列表 1\n2. 有序列表 2\n# 四、引用\n> 一级引用\n>>二级引用\n>>>三级引用\n# 五、链接\n[这是一个链接](https:work.weixin.qq.com\/api\/doc)\n![](https://res.mail.qq.com/node/ww/wwopenmng/images/independent/doc/test_pic_msg1.png)\n# 六、分割线\n\n---\n# 七、代码\n`这是行内代码`\n```\n这是独立代码块\n```\n\n# 八、表格\n| 姓名 | 文化衫尺寸 | 收货地址 |\n| :----- | :----: | -------: |\n| 张三 | S | 广州 |\n| 李四 | L | 深圳 |\n"
    success = test_notifier.send_message(CONTENTS.ERROR.value, mention_all=True)
    print(f"测试消息发送: {'成功' if success else '失败'}")
