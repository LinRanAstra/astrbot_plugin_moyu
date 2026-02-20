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
        else:
            # 如果配置中禁用了定时任务，且当前有运行的定时任务，则停止它
            if self.moyu_job_id:
                await self._stop_scheduled_task()

    async def _start_scheduled_task(
        self, cron_expression: str = "0 8 * * *", target_sessions: list = []
    ):
        """启动定时任务"""
        # 如果已有定时任务，先删除旧任务
        if self.moyu_job_id:
            try:
                await self.cron_manager.delete_job(self.moyu_job_id)
            except Exception as e:
                logger.error(f"删除旧定时任务失败: {e}")
            self.moyu_job_id = None

        async def send_moyu_image(**kwargs):
            try:
                moyu_img_path = await capture_poster_without_obstacle(
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

                                # 解析会话字符串，支持完整格式和仅ID格式
                                session = self._parse_session_string(session_str)
                                if session is None:
                                    logger.error(f"无法解析会话字符串: {session_str}")
                                    continue

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

                                # 解析会话字符串，支持完整格式和仅ID格式
                                session = self._parse_session_string(session_str)
                                if session is None:
                                    logger.error(f"无法解析会话字符串: {session_str}")
                                    continue

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

    def _parse_session_string(self, session_str):
        """解析会话字符串，支持完整格式和仅ID格式"""
        from astrbot.core.platform.message_session import MessageSession
        from astrbot.core.platform.message_type import MessageType

        try:
            # 尝试按完整格式解析
            platform_id, message_type, session_id = session_str.split(":", 2)
            return MessageSession(platform_id, MessageType(message_type), session_id)
        except ValueError:
            # 如果解析失败，假定这是仅ID格式，尝试从当前上下文获取默认值
            # 这里假设默认是QQ群消息，实际应用中可能需要更灵活的配置
            logger.warning(f"会话字符串格式不完整，尝试使用默认值: {session_str}")

            # 如果字符串只包含数字（即会话ID），则使用默认平台和消息类型
            if session_str.isdigit():
                # 默认使用QQ平台和群消息类型
                # 实际使用中可能需要从配置或其他地方获取默认值
                return MessageSession("qq", MessageType.GROUP_MESSAGE, session_str)
            else:
                logger.error(f"无法解析会话字符串: {session_str}")
                return None

    async def _stop_scheduled_task(self):
        """停止定时任务"""
        if self.moyu_job_id:
            try:
                await self.cron_manager.delete_job(self.moyu_job_id)
                logger.info(f"已停止定时摸鱼任务，ID: {self.moyu_job_id}")
                self.moyu_job_id = None
            except Exception as e:
                logger.error(f"插件卸载时删除定时任务失败: {e}")

    # 注册指令的装饰器。指令名为 moyu。发送 `/moyu` 即可触发此指令，发送摸鱼图片
    @filter.command("moyu")
    async def moyu(self, event: AstrMessageEvent):
        """这是一个摸鱼指令，发送一张摸鱼图片"""
        message_chain = event.get_messages()  # 用户所发的消息的消息链
        logger.info(message_chain)

        try:
            moyu_img_path = await capture_poster_without_obstacle(
                "https://moyu.ranawa.com/"
            )
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

    async def on_config_updated(self, new_config):
        """当插件配置更新时调用此方法"""
        old_enabled = self.plugin_config.get("enabled", False) if self.plugin_config else False
        new_enabled = new_config.get("enabled", False)
        
        # 更新配置
        self.plugin_config = new_config
        
        # 如果启用状态发生变化
        if old_enabled != new_enabled:
            if new_enabled:
                # 从禁用变为启用，启动任务
                cron_expr = self.plugin_config.get("cron_expression", "0 8 * * *")
                target_sessions = self.plugin_config.get("target_sessions", [])
                await self._start_scheduled_task(cron_expr, target_sessions)
            else:
                # 从启用变为禁用，停止任务
                await self._stop_scheduled_task()
        elif new_enabled:
            # 启用状态下，检查cron表达式是否改变
            old_cron = (self.plugin_config or {}).get("cron_expression", "0 8 * * *")
            new_cron = new_config.get("cron_expression", "0 8 * * *")
            
            if old_cron != new_cron:
                # cron表达式改变，更新任务
                target_sessions = new_config.get("target_sessions", [])
                
                # 先停止旧任务
                await self._stop_scheduled_task()
                
                # 启动新任务
                await self._start_scheduled_task(new_cron, target_sessions)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        # 插件卸载时删除定时任务
        if self.moyu_job_id:
            try:
                await self.cron_manager.delete_job(self.moyu_job_id)
                self.moyu_job_id = None
            except Exception as e:
                logger.error(f"插件卸载时删除定时任务失败: {e}")
