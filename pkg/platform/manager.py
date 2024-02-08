from __future__ import annotations

import json
import os
import logging
import asyncio
import traceback

from mirai import At, GroupMessage, MessageEvent, StrangerMessage, \
    FriendMessage, Image, MessageChain, Plain
import mirai
from ..platform import adapter as msadapter

from ..core import app, entities as core_entities
from ..plugin import events

# 控制QQ消息输入输出的类
class PlatformManager:
    
    adapter: msadapter.MessageSourceAdapter = None

    @property
    def bot_account_id(self):
        return self.adapter.bot_account_id

    # modern
    ap: app.Application = None

    def __init__(self, ap: app.Application = None):

        self.ap = ap
    
    async def initialize(self):

        from .sources import yirimirai, nakuru, aiocqhttp, qqbotpy

        adapter_cls = None

        for adapter in msadapter.preregistered_adapters:
            if adapter.name == self.ap.platform_cfg.data['platform-adapter']:
                adapter_cls = adapter
                break
        if adapter_cls is None:
            raise Exception('未知的平台适配器: ' + self.ap.platform_cfg.data['platform-adapter'])

        cfg_key = self.ap.platform_cfg.data['platform-adapter'] + '-config'
        self.adapter = adapter_cls(
            self.ap.platform_cfg.data[cfg_key],
            self.ap
        )

        async def on_friend_message(event: FriendMessage):

            event_ctx = await self.ap.plugin_mgr.emit_event(
                event=events.PersonMessageReceived(
                    launcher_type='person',
                    launcher_id=event.sender.id,
                    sender_id=event.sender.id,
                    message_chain=event.message_chain,
                    query=None
                )
            )

            if not event_ctx.is_prevented_default():

                await self.ap.query_pool.add_query(
                    launcher_type=core_entities.LauncherTypes.PERSON,
                    launcher_id=event.sender.id,
                    sender_id=event.sender.id,
                    message_event=event,
                    message_chain=event.message_chain
                )

        self.adapter.register_listener(
            FriendMessage,
            on_friend_message
        )

        async def on_stranger_message(event: StrangerMessage):
            
            event_ctx = await self.ap.plugin_mgr.emit_event(
                event=events.PersonMessageReceived(
                    launcher_type='person',
                    launcher_id=event.sender.id,
                    sender_id=event.sender.id,
                    message_chain=event.message_chain,
                    query=None
                )
            )

            if not event_ctx.is_prevented_default():

                await self.ap.query_pool.add_query(
                    launcher_type=core_entities.LauncherTypes.PERSON,
                    launcher_id=event.sender.id,
                    sender_id=event.sender.id,
                    message_event=event,
                    message_chain=event.message_chain,
                )

        # nakuru不区分好友和陌生人，故仅为yirimirai注册陌生人事件
        if self.ap.platform_cfg.data['platform-adapter'] == 'yiri-mirai':
            self.adapter.register_listener(
                StrangerMessage,
                on_stranger_message
            )

        async def on_group_message(event: GroupMessage):

            event_ctx = await self.ap.plugin_mgr.emit_event(
                event=events.GroupMessageReceived(
                    launcher_type='person',
                    launcher_id=event.sender.id,
                    sender_id=event.sender.id,
                    message_chain=event.message_chain,
                    query=None
                )
            )

            if not event_ctx.is_prevented_default():

                await self.ap.query_pool.add_query(
                    launcher_type=core_entities.LauncherTypes.GROUP,
                    launcher_id=event.group.id,
                    sender_id=event.sender.id,
                    message_event=event,
                    message_chain=event.message_chain
                )

        self.adapter.register_listener(
            GroupMessage,
            on_group_message
        )

    async def send(self, event, msg, check_quote=True, check_at_sender=True):
        
        if check_at_sender and self.ap.platform_cfg.data['at-sender'] and isinstance(event, GroupMessage):

            msg.insert(
                0,
                At(
                    event.sender.id
                )
            )

        await self.adapter.reply_message(
            event,
            msg,
            quote_origin=True if self.ap.platform_cfg.data['quote-origin'] and check_quote else False
        )

    # 通知系统管理员
    # TODO delete
    # async def notify_admin(self, message: str):
    #     await self.notify_admin_message_chain(MessageChain([Plain("[bot]{}".format(message))]))

    # async def notify_admin_message_chain(self, message: mirai.MessageChain):
    #     if self.ap.system_cfg.data['admin-sessions'] != []:

    #         admin_list = []
    #         for admin in self.ap.system_cfg.data['admin-sessions']:
    #             admin_list.append(admin)
            
    #         for adm in admin_list:
    #             self.adapter.send_message(
    #                 adm.split("_")[0],
    #                 adm.split("_")[1],
    #                 message
    #             )

    async def run(self):
        try:
            await self.adapter.run_async()
        except Exception as e:
            self.ap.logger.error('平台适配器运行出错: ' + str(e))
            self.ap.logger.debug(f"Traceback: {traceback.format_exc()}")
