from typing import Optional, Iterable

from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import PrivateMessageEvent, GroupMessageEvent

from .core import get, CheckResult


def check(bot: Bot, event: Event, perm: str) -> bool:
    for r in do_check(bot, event, perm):
        if r is not None:
            return r == CheckResult.ALLOW

    return False


def do_check(bot: Bot, event: Event, perm: str) -> Iterable[Optional[CheckResult]]:
    # 特定用户
    group, user_specific_found = get('user', str(event.get_user_id()))
    yield group.check(perm)

    # Bot超级用户
    if event.get_user_id() in bot.config.superusers:
        group, _ = get('global', 'superuser')
        yield group.check(perm)

    # 若没有特定用户的设置，则检查所有用户
    if not user_specific_found:
        group, _ = get('global', 'anyone')
        yield group.check(perm)

    # 群组
    if isinstance(event, GroupMessageEvent):
        # 用户在群组内的身份
        if event.sender.role == 'admin':
            group, _ = get('global', 'group_admin')
            yield group.check(perm)
        elif event.sender.role == 'owner':
            group, _ = get('global', 'group_owner')
            yield group.check(perm)

        # 群组本身
        group, found = get('group', str(event.group_id))
        if not found:
            group, _ = get('global', 'group')
        yield group.check(perm)

    # 私聊
    if isinstance(event, PrivateMessageEvent):
        group, _ = get('global', 'private')
        yield group.check(perm)
