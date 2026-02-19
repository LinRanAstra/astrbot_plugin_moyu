from typing import Any, Dict

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.cron.manager import CronJobManager
from astrbot.core.message.message_event_result import MessageChain

from .apitest import capture_poster_without_obstacle


@register("moyu", "YourName", "摸鱼插件，支持定时发送摸鱼图片", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)

        # 获取Cron管理器
        self.cron_manager: CronJobManager = context.cron_manager

        # 存储定时任务ID
        self.moyu_job_id = None

        # 保存配置
        self.plugin_config = config

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 如果配置中启用了定时任务，则自动启动
        if self.plugin_config and self.plugin_config.get("enabled", False):
            # 获取配置的cron表达式，默认为每天早上8:00
            cron_expr = self.plugin_config.get("cron_expression", "0 8 * * *")
            # 启动定时任务
            await self._start_scheduled_task(
                cron_expr, self.plugin_config.get("target_sessions", [])
            )

    async def _start_scheduled_task(
        self, cron_expression: str = "0 8 * * *", target_sessions: list = []
    ):
        """启动定时任务"""
        # 检查是否已有定时任务
        if self.moyu_job_id:
            job = await self.cron_manager.db.get_cron_job(self.moyu_job_id)
            if job and job.enabled:
                logger.info("定时摸鱼任务已经存在")
                return

        async def send_moyu_image(**kwargs):
            try:
                moyu_img_path = capture_poster_without_obstacle(
                    "https://moyu.ranawa.com"
                )
                if moyu_img_path:
                    img_component = Comp.Image(moyu_img_path)

                    # 创建MessageChain对象
                    message_chain = MessageChain(chain=[img_component])

                    # 如果有指定目标会话，发送到这些会话
                    if target_sessions:
                        for session_str in target_sessions:
                            try:
                                from astrbot.core.platform.message_session import (
                                    MessageSession,
                                )

                                session = MessageSession.from_str(session_str)
                                await self.context.send_message(
                                    session, message_chain
                                )  # 传递MessageChain对象
                            except Exception as e:
                                logger.error(f"发送到会话 {session_str} 失败: {e}")
                    else:
                        # 如果没有指定目标会话，从kwargs中获取会话
                        session = kwargs.get("session")
                        if session:
                            await self.context.send_message(
                                session, message_chain
                            )  # 传递MessageChain对象
                else:
                    # 发送错误信息
                    error_msg = MessageChain(
                        chain=[Comp.Plain("定时摸鱼失败：无法生成摸鱼图片")]
                    )
                    if target_sessions:
                        for session_str in target_sessions:
                            try:
                                from astrbot.core.platform.message_session import (
                                    MessageSession,
                                )

                                session = MessageSession.from_str(session_str)
                                await self.context.send_message(
                                    session, error_msg
                                )  # 传递MessageChain对象
                            except Exception as e:
                                logger.error(f"发送到会话 {session_str} 失败: {e}")
                    elif "session" in kwargs:
                        await self.context.send_message(
                            kwargs["session"], error_msg
                        )  # 传递MessageChain对象
            except Exception as e:
                logger.error(f"定时摸鱼任务执行失败: {e}")

        # 添加基本定时任务
        job = await self.cron_manager.add_basic_job(
            name="定时摸鱼",
            cron_expression=cron_expression,
            handler=send_moyu_image,
            description="每天定时发送摸鱼图片",
            payload={},
            enabled=True,
            persistent=True,  # 设为持久化，重启后仍然有效
        )

        self.moyu_job_id = job.job_id
        logger.info(
            f"已启动定时摸鱼任务，ID: {self.moyu_job_id}，表达式: {cron_expression}"
        )

    # 注册指令的装饰器。指令名为 moyu。发送 `/moyu` 即可触发此指令，发送摸鱼图片
    @filter.command("moyu")
    async def moyu(self, event: AstrMessageEvent):
        """这是一个摸鱼指令，发送一张摸鱼图片"""
        message_chain = event.get_messages()  # 用户所发的消息的消息链
        logger.info(message_chain)

        try:
            moyu_img_path = capture_poster_without_obstacle("https://moyu.ranawa.com/")
            if moyu_img_path:
                chain = [
                    Comp.Image(moyu_img_path),
                ]  # type: list[Comp.BaseMessageComponent]
            else:
                chain = [
                    Comp.Plain("生成摸鱼图片失败"),
                ]  # type: list[Comp.BaseMessageComponent]
        except Exception as e:
            logger.error(f"生成摸鱼图片时发生错误: {e}")
            chain = [
                Comp.Plain("生成摸鱼图片时发生错误"),
            ]  # type: list[Comp.BaseMessageComponent]

        yield event.chain_result(chain)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        # 插件卸载时删除定时任务
        if self.moyu_job_id:
            try:
                await self.cron_manager.delete_job(self.moyu_job_id)
            except Exception as e:
                logger.error(f"插件卸载时删除定时任务失败: {e}")
