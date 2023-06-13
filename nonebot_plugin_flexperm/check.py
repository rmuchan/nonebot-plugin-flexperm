from typing import Iterable, Tuple, Optional

from nonebot import logger, get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent

from .config import c
from .core import get, CheckResult, PermissionGroup


def check(event: Event, perm: str) -> bool:
    if c.flexperm_debug_check:
        logger.debug('Checking {}', perm)
    for group in iterate_groups(event):
        r = group.check(perm)
        if c.flexperm_debug_check:
            logger.debug('Got {} from {}', r, group)
        if r is not None:
            return r == CheckResult.ALLOW

    return False


def get_permission_group_by_event(event: Event) -> Optional[Tuple[str, int]]:
    if isinstance(event, GroupMessageEvent):
        return 'group', event.group_id
    if isinstance(event, PrivateMessageEvent):
        return 'user', event.user_id


def iterate_groups(event: Event) -> Iterable[PermissionGroup]:
    # 特定用户
    user = getattr(event, 'user_id', None) or int(event.get_user_id())
    yield get('user', user)

    # Bot超级用户
    if event.get_user_id() in get_driver().config.superusers:
        yield get('global', 'superuser')

    # 所有用户
    yield get('global', 'anyone')

    # 群组
    if isinstance(event, GroupMessageEvent):
        # 用户在群组内的身份
        if event.sender.role == 'admin':
            yield get('global', 'group_admin')
        elif event.sender.role == 'owner':
            yield get('global', 'group_owner')

        # 特定群组
        yield get('group', event.group_id)

        # 所有群组
        yield get('global', 'group')

    # 私聊
    if isinstance(event, PrivateMessageEvent):
        yield get('global', 'private')
