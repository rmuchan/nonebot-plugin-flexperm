from typing import Tuple, Union

from nonebot import CommandGroup
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp import MessageEvent, GroupMessageEvent

from . import core
from .plugin import register

P = register('flexperm')

cg = CommandGroup('flexperm')


def h(x):
    return x.handle()


async def ensure_command(_b, e, s):
    msg = e.get_message()
    raw_cmd = s["_prefix"]["raw_command"]
    if not msg or not raw_cmd or not all(seg.is_text() for seg in msg):
        return False

    first_seg = str(msg[0]).lstrip()
    if not first_seg.startswith(raw_cmd):
        return False
    return (len(msg) == 1 and len(first_seg) == len(raw_cmd)  # 无参数
            or first_seg[len(raw_cmd)].isspace())  # 命令名后有空格


@h(cg.command('reload', rule=ensure_command, permission=P('reload')))
async def _(bot: Bot, event: MessageEvent):
    force = str(event.message).strip() == 'force'
    reloaded = core.reload(force)
    if reloaded:
        await bot.send(event, '重新加载权限配置')
    else:
        await bot.send(event, '有未保存的修改，如放弃修改请添加force参数')


@h(cg.command('save', rule=ensure_command, permission=P('reload')))
async def _(bot: Bot, event: MessageEvent):
    success = core.save_all()
    if success:
        await bot.send(event, '已保存权限配置')
    else:
        await bot.send(event, '部分配置保存失败，请检查控制台输出')


@h(cg.command('add', rule=ensure_command, permission=P('edit.perm'), state={'add': True}))
@h(cg.command('remove', rule=ensure_command, permission=P('edit.perm'), state={'add': False}))
async def _(bot: Bot, event: MessageEvent, state: dict):
    args = str(event.message).split()

    # 一个参数，编辑当前会话的权限
    if len(args) == 1:
        item = args[0]
        namespace, group = get_group_for_event(event)
    # 两个参数，编辑指定权限组权限
    elif len(args) == 2:
        item = args[1]
        namespace, group = parse_group(args[0])
    # 参数数量错误
    else:
        usage = '用法：{} [[名称空间:]权限组名] 权限描述'
        return await bot.send(event, usage.format(state["_prefix"]["raw_command"]))

    # 阻止修饰
    if item.startswith('-'):
        item = '-/' + item[1:]
    else:
        item = '/' + item

    try:
        if state['add']:
            P.add_item(namespace, group, item)
        else:
            P.remove_item(namespace, group, item)
    except TypeError:
        await bot.send(event, '权限组不可修改')
    except KeyError:
        await bot.send(event, '权限组不存在')
    except ValueError:
        await bot.send(event, '权限组中{}指定描述'.format('已有' if state['add'] else '没有'))
    else:
        await bot.send(event, '已修改权限组')


@h(cg.command('addgrp', rule=ensure_command, permission=P('edit.group'), state={'add': True}))
@h(cg.command('rmgrp', rule=ensure_command, permission=P('edit.group'), state={'add': False, 'force': False}))
@h(cg.command('rmgrpf', rule=ensure_command, permission=P('edit.group.force'), state={'add': False, 'force': True}))
async def _(bot: Bot, event: MessageEvent, state: dict):
    arg = str(event.message).strip()

    # 无参数，编辑当前会话权限组
    if not arg:
        namespace, group = get_group_for_event(event)
    # 一个参数，编辑指定权限组
    elif not any(x.isspace() for x in arg):
        namespace, group = parse_group(arg)
    # 参数数量错误
    else:
        usage = '用法：{} [[名称空间:]权限组名]'
        return await bot.send(event, usage.format(state["_prefix"]["raw_command"]))

    try:
        if state['add']:
            P.add_group(namespace, group)
        else:
            P.remove_group(namespace, group, state['force'])
    except TypeError:
        await bot.send(event, '名称空间不可修改')
    except KeyError:
        await bot.send(event, '权限组{}存在'.format('已' if state['add'] else '不'))
    except ValueError:
        await bot.send(event, '权限组非空')
    else:
        await bot.send(event, '已{}权限组'.format('创建' if state['add'] else '删除'))


def get_group_for_event(event: MessageEvent) -> Tuple[str, int]:
    if isinstance(event, GroupMessageEvent):
        return 'group', event.group_id
    else:
        return 'user', event.user_id


def parse_group(arg: str) -> Tuple[str, Union[str, int]]:
    group_split = arg.split(':', maxsplit=1)
    if len(group_split) == 1:
        return 'global', group_split[0]
    else:
        namespace, group = group_split
        if namespace in ['group', 'user']:
            try:
                group = int(group)
            except ValueError:
                pass
        return namespace, group
