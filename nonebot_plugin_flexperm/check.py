from typing import Iterable, Tuple, Optional, Union

from nonebot import logger
from nonebot.adapters import Bot, Event

from .adapters import handler_for
from .config import c
from .core import get, CheckResult, PermissionGroup
from .util import try_int


def check(bot: Bot, event: Event, perm: str) -> bool:
    if c.flexperm_debug_check:
        logger.debug('Checking {}', perm)
    for group in iterate_groups(bot, event):
        r = group.check(perm)
        if c.flexperm_debug_check:
            logger.debug('Got {} from {}', r, group)
        if r is not None:
            return r == CheckResult.ALLOW

    return False


def get_permission_group_by_event(bot: Bot, event: Event) -> Optional[Tuple[str, Union[str, int]]]:
    h = handler_for(bot.adapter.get_name())
    adapter = bot.adapter.get_name().split(maxsplit=1)[0].lower()
    is_default_adapter = (adapter == c.flexperm_default_adapter.lower())

    if (group_id := h.get_group_id(event)) is not None:
        gn = group_id if is_default_adapter else f'{adapter}:{group_id}'
        return 'group', gn
    if h.is_private_chat(event):
        uid = event.get_user_id()
        un = try_int(uid) if is_default_adapter else f'{adapter}:{uid}'
        return 'user', un


def iterate_groups(bot: Bot, event: Event) -> Iterable[PermissionGroup]:
    h = handler_for(bot.adapter.get_name())
    adapter = bot.adapter.get_name().split(maxsplit=1)[0].lower()
    is_default_adapter = (adapter == c.flexperm_default_adapter.lower())

    # 特定用户
    user_id = event.get_user_id()
    group = get('user', try_int(user_id)) if is_default_adapter else None
    if not (is_default_adapter and group.is_valid):
        group = get('user', f'{adapter}:{user_id}')
    yield group

    # Bot超级用户
    if is_superuser(bot, event):
        yield get('global', 'superuser')

    # 所有用户
    yield get('global', 'anyone')

    # 群组
    if (group_id := h.get_group_id(event)) is not None:
        # 用户在群组内的身份
        role = h.get_group_role(event)
        if role == 'admin':
            yield get('global', 'group_admin')
        elif role == 'owner':
            yield get('global', 'group_owner')

        # 特定群组
        group = get('group', try_int(group_id)) if is_default_adapter else None
        if not (is_default_adapter and group.is_valid):
            group = get('group', f'{adapter}:{group_id}')
        yield group

        # 所有群组
        yield get('global', 'group')

    # 私聊
    if h.is_private_chat(event):
        yield get('global', 'private')


def is_superuser(bot: Bot, event: Event):
    try:
        user_id = event.get_user_id()
    except Exception:
        return False
    return (
        f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{user_id}" in bot.config.superusers
        or user_id in bot.config.superusers
    )
