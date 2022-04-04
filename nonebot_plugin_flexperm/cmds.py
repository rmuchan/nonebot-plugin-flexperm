from nonebot import CommandGroup
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import CommandArg, State, RawCommand, EventMessage

from . import core
from .plugin import register

P = register('flexperm')

cg = CommandGroup('flexperm', block=True)


def h(x):
    return x.handle()


async def ensure_command(msg: Message = EventMessage(), raw_cmd: str = RawCommand()):
    if not msg or not raw_cmd or not all(seg.is_text() for seg in msg):
        return False

    first_seg = str(msg[0]).lstrip()
    if not first_seg.startswith(raw_cmd):
        return False
    return (len(msg) == 1 and len(first_seg) == len(raw_cmd)  # 无参数
            or first_seg[len(raw_cmd)].isspace())  # 命令名后有空格


@h(cg.command('reload', rule=ensure_command, permission=P('reload')))
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    force = str(arg).strip() == 'force'
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
async def _(bot: Bot, event: MessageEvent, state: dict = State(),
            raw_command: str = RawCommand(), arg: Message = CommandArg()):
    args = str(arg).split()

    # 一个参数，编辑当前会话的权限
    if len(args) == 1:
        item = args[0]
        designator = event
    # 两个参数，编辑指定权限组权限
    elif len(args) == 2:
        designator, item = args
    # 参数数量错误
    else:
        usage = f'用法：{raw_command} [[名称空间:]权限组名] 权限描述'
        return await bot.send(event, usage)

    # 阻止修饰
    if item.startswith('-'):
        item = '-/' + item[1:]
    else:
        item = '/' + item

    try:
        if state['add']:
            result = P.add_item(designator, item)
        else:
            result = P.remove_item(designator, item)
    except TypeError:
        await bot.send(event, '权限组不可修改')
    else:
        if result:
            await bot.send(event, '已修改权限组')
        else:
            await bot.send(event, '权限组中{}指定描述'.format('已有' if state['add'] else '没有'))


@h(cg.command('addinh', rule=ensure_command, permission=P('edit.inherit'), state={'add': True}))
@h(cg.command('rminh', rule=ensure_command, permission=P('edit.inherit'), state={'add': False}))
async def _(bot: Bot, event: MessageEvent, state: dict = State(),
            raw_command: str = RawCommand(), arg: Message = CommandArg()):
    args = str(arg).split()

    # 一个参数，编辑当前会话的权限
    if len(args) == 1:
        target = args[0]
        designator = event
    # 两个参数，编辑指定权限组权限
    elif len(args) == 2:
        designator, target = args
    # 参数数量错误
    else:
        usage = f'用法：{raw_command} [[名称空间:]权限组名] [名称空间:]继承权限组名'
        return await bot.send(event, usage)

    try:
        if state['add']:
            result = P.add_inheritance(designator, target)
        else:
            result = P.remove_inheritance(designator, target)
    except KeyError:
        await bot.send(event, '权限组不存在')
    except TypeError:
        await bot.send(event, '权限组不可修改')
    else:
        if result:
            await bot.send(event, '已修改权限组')
        else:
            await bot.send(event, '权限组中{}指定继承关系'.format('已有' if state['add'] else '没有'))


@h(cg.command('addgrp', rule=ensure_command, permission=P('edit.group'), state={'add': True}))
@h(cg.command('rmgrp', rule=ensure_command, permission=P('edit.group'), state={'add': False, 'force': False}))
@h(cg.command('rmgrpf', rule=ensure_command, permission=P('edit.group.force'), state={'add': False, 'force': True}))
async def _(bot: Bot, event: MessageEvent, state: dict = State(),
            raw_command: str = RawCommand(), arg: Message = CommandArg()):
    arg = str(arg).strip()

    # 无参数，编辑当前会话权限组
    if not arg:
        designator = event
    # 一个参数，编辑指定权限组
    elif not any(x.isspace() for x in arg):
        designator = arg
    # 参数数量错误
    else:
        usage = f'用法：{raw_command} [[名称空间:]权限组名]'
        return await bot.send(event, usage)

    try:
        if state['add']:
            P.add_group(designator)
        else:
            P.remove_group(designator, force=state['force'])
    except TypeError:
        await bot.send(event, '名称空间不可修改')
    except KeyError:
        await bot.send(event, '权限组{}存在'.format('已' if state['add'] else '不'))
    except ValueError:
        await bot.send(event, '权限组非空')
    else:
        await bot.send(event, '已{}权限组'.format('创建' if state['add'] else '删除'))
