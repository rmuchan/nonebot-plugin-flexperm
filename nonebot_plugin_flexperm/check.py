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
    group, _ = get('user', user)
    yield group

    # Bot超级用户
    if event.get_user_id() in get_driver().config.superusers:
        group, _ = get('global', 'superuser')
        yield group

    # 所有用户
    group, _ = get('global', 'anyone')
    yield group

    # 群组
    if isinstance(event, GroupMessageEvent):
        # 用户在群组内的身份
        if event.sender.role == 'admin':
            group, _ = get('global', 'group_admin')
            yield group
        elif event.sender.role == 'owner':
            group, _ = get('global', 'group_owner')
            yield group

        # 特定群组
        group, _ = get('group', event.group_id)
        yield group

        # 所有群组
        group, _ = get('global', 'group')
        yield group

    # 私聊
    if isinstance(event, PrivateMessageEvent):
        group, _ = get('global', 'private')
        yield group
