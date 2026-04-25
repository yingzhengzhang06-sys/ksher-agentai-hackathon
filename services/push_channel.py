"""
推送通道服务 — 企业微信/飞书消息推送
支持：文本消息、Markdown、图文卡片
"""
import os
import json
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class PushMessage:
    """推送消息数据结构"""
    title: str
    content: str
    msg_type: str = "text"  # text / markdown / news
    url: Optional[str] = None
    pic_url: Optional[str] = None
    mention_list: Optional[List[str]] = None


class WeComPusher:
    """
    企业微信推送器
    支持：群机器人Webhook、应用消息
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("WECOM_WEBHOOK_URL", "")

    def _send(self, payload: dict) -> dict:
        """发送请求"""
        if not self.webhook_url:
            return {"success": False, "error": "未配置企业微信Webhook URL"}

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            result = resp.json()
            if result.get("errcode") == 0:
                return {"success": True, "msgid": result.get("msgid")}
            return {"success": False, "error": result.get("errmsg", "未知错误")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_text(self, content: str, mention_list: Optional[List[str]] = None) -> dict:
        """发送文本消息"""
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mention_list or [],
            },
        }
        return self._send(payload)

    def send_markdown(self, content: str) -> dict:
        """发送Markdown消息"""
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        return self._send(payload)

    def send_news(self, title: str, description: str, url: str,
                  pic_url: Optional[str] = None) -> dict:
        """发送图文消息"""
        payload = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": description,
                        "url": url,
                        "picurl": pic_url or "",
                    }
                ]
            },
        }
        return self._send(payload)

    def send_card(self, title: str, description: str, url: str,
                  btntxt: str = "查看详情") -> dict:
        """发送模板卡片（更美观的展示）"""
        payload = {
            "msgtype": "template_card",
            "template_card": {
                "card_type": "text_notice",
                "source": {
                    "desc": "Ksher销售助手",
                    "desc_color": 0,
                },
                "main_title": {
                    "title": title,
                    "desc": description,
                },
                "jump_list": [
                    {
                        "type": 1,
                        "url": url,
                        "title": btntxt,
                    }
                ],
            },
        }
        return self._send(payload)


class FeishuPusher:
    """
    飞书推送器
    支持：Webhook机器人
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")

    def _send(self, payload: dict) -> dict:
        """发送请求"""
        if not self.webhook_url:
            return {"success": False, "error": "未配置飞书Webhook URL"}

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            result = resp.json()
            if result.get("code") == 0:
                return {"success": True}
            return {"success": False, "error": result.get("msg", "未知错误")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_text(self, content: str) -> dict:
        """发送文本消息"""
        payload = {
            "msg_type": "text",
            "content": {"text": content},
        }
        return self._send(payload)

    def send_rich_text(self, title: str, content: List[dict]) -> dict:
        """发送富文本消息"""
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content,
                    }
                }
            },
        }
        return self._send(payload)

    def send_interactive(self, card: dict) -> dict:
        """发送交互式卡片"""
        payload = {
            "msg_type": "interactive",
            "card": card,
        }
        return self._send(payload)


class PushChannelManager:
    """
    推送通道管理器
    统一接口，支持多通道推送
    """

    CHANNEL_WECOM = "wecom"
    CHANNEL_FEISHU = "feishu"

    def __init__(self):
        self._channels: Dict[str, Any] = {}
        self._init_channels()

    def _init_channels(self):
        """初始化所有可用的推送通道"""
        # 企业微信
        wecom_url = os.getenv("WECOM_WEBHOOK_URL", "")
        if wecom_url:
            self._channels[self.CHANNEL_WECOM] = WeComPusher(wecom_url)

        # 飞书
        feishu_url = os.getenv("FEISHU_WEBHOOK_URL", "")
        if feishu_url:
            self._channels[self.CHANNEL_FEISHU] = FeishuPusher(feishu_url)

    def get_available_channels(self) -> List[str]:
        """获取可用的推送通道列表"""
        return list(self._channels.keys())

    def push(self, message: PushMessage, channels: Optional[List[str]] = None) -> Dict[str, dict]:
        """
        推送消息到指定通道

        Args:
            message: 推送消息
            channels: 指定通道列表，None表示推送到所有可用通道

        Returns:
            {通道名: 推送结果}
        """
        targets = channels or list(self._channels.keys())
        results = {}

        for channel in targets:
            pusher = self._channels.get(channel)
            if not pusher:
                results[channel] = {"success": False, "error": "通道未配置"}
                continue

            if message.msg_type == "text":
                if channel == self.CHANNEL_WECOM:
                    results[channel] = pusher.send_text(
                        message.content, message.mention_list
                    )
                else:
                    results[channel] = pusher.send_text(message.content)

            elif message.msg_type == "markdown":
                if channel == self.CHANNEL_WECOM:
                    results[channel] = pusher.send_markdown(message.content)
                else:
                    # 飞书用富文本模拟markdown
                    results[channel] = pusher.send_text(message.content)

            elif message.msg_type == "news":
                if channel == self.CHANNEL_WECOM:
                    results[channel] = pusher.send_news(
                        message.title, message.content,
                        message.url or "", message.pic_url
                    )
                else:
                    results[channel] = pusher.send_text(
                        f"{message.title}\n{message.content}\n{message.url or ''}"
                    )

        return results

    def push_text(self, content: str, channels: Optional[List[str]] = None) -> Dict[str, dict]:
        """快捷方式：推送文本消息"""
        msg = PushMessage(title="", content=content, msg_type="text")
        return self.push(msg, channels)

    def push_markdown(self, title: str, content: str,
                      channels: Optional[List[str]] = None) -> Dict[str, dict]:
        """快捷方式：推送Markdown消息"""
        msg = PushMessage(title=title, content=content, msg_type="markdown")
        return self.push(msg, channels)

    def push_alert(self, title: str, content: str, level: str = "info",
                   channels: Optional[List[str]] = None) -> Dict[str, dict]:
        """
        推送告警消息（带级别标识）

        level: info / warning / danger
        """
        level_emoji = {"info": "ℹ️", "warning": "⚠️", "danger": "🚨"}
        emoji = level_emoji.get(level, "ℹ️")
        formatted = f"{emoji} **{title}**\n\n{content}"
        msg = PushMessage(title=title, content=formatted, msg_type="markdown")
        return self.push(msg, channels)


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────
def get_push_manager() -> PushChannelManager:
    """获取推送管理器实例"""
    if not hasattr(get_push_manager, "_instance"):
        get_push_manager._instance = PushChannelManager()
    return get_push_manager._instance


def quick_push(content: str) -> dict:
    """快速推送文本消息"""
    manager = get_push_manager()
    return manager.push_text(content)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("PushChannel 测试")
    print("=" * 60)

    manager = PushChannelManager()
    channels = manager.get_available_channels()
    print(f"可用推送通道: {channels}")

    if not channels:
        print("\n未配置任何推送通道。请设置环境变量：")
        print("  WECOM_WEBHOOK_URL=xxx")
        print("  FEISHU_WEBHOOK_URL=xxx")
    else:
        # 测试推送
        result = manager.push_alert(
            title="汇率预警",
            content="USD/CNY 今日波动超过0.5%，建议关注锁汇机会。",
            level="warning",
        )
        print(f"\n推送结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
