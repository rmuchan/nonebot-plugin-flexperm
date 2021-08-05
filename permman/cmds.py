from nonebot import CommandGroup
from nonebot.adapters import Bot, Event

from . import core
from .plugin import register

P = register('permman')

cg = CommandGroup('permman')

reload = cg.command('reload', permission=P('reload'))


@reload.handle()
async def _(bot: Bot, event: Event):
    core.reload()
    await bot.send(event, '重新加载权限配置')
