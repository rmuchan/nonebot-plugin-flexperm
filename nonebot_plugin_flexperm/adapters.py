from abc import ABC, abstractmethod
from functools import cache
from typing import ClassVar, Type, Union, Optional

from nonebot import logger
from nonebot.adapters import Event

registry: dict[str, Type['AdapterHandler']] = {}


class AdapterHandler(ABC):
    adapter: ClassVar[str]

    @abstractmethod
    def is_private_chat(self, event: Event) -> bool: ...

    @abstractmethod
    def get_group_id(self, event: Event) -> Union[int, str, None]: ...

    @abstractmethod
    def get_group_role(self, event: Event) -> Optional[str]:
        """ check "owner", "admin" """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.adapter:
            if cls.adapter in registry:
                raise ValueError(f'Duplicate adapter handler for {cls.adapter}')
            registry[cls.adapter] = cls


@cache
def handler_for(adapter: str) -> AdapterHandler:
    cls = registry.get(adapter)
    if not cls:
        logger.warning('Unknown adapter {}', adapter)
        cls = Dummy
    return cls()


class Dummy(AdapterHandler):
    adapter = ''

    def is_private_chat(self, event: Event) -> bool:
        return False

    def get_group_id(self, event: Event) -> Union[int, str, None]:
        return

    def get_group_role(self, event: Event) -> Optional[str]:
        return


class OnebotV11(AdapterHandler):
    adapter = 'OneBot V11'

    def __init__(self):
        import nonebot.adapters.onebot.v11 as onebot
        self.onebot = onebot

    def is_private_chat(self, event: Event) -> bool:
        return isinstance(event, self.onebot.PrivateMessageEvent)

    def get_group_id(self, event: Event) -> Union[int, str, None]:
        if isinstance(event, self.onebot.GroupMessageEvent):
            return event.group_id

    def get_group_role(self, event: Event) -> Optional[str]:
        if isinstance(event, self.onebot.GroupMessageEvent):
            return event.sender.role


class Kaiheila(AdapterHandler):
    adapter = 'Kaiheila'

    def __init__(self):
        import nonebot.adapters.kaiheila as kaiheila
        self.kaiheila = kaiheila

    def is_private_chat(self, event: Event) -> bool:
        return isinstance(event, self.kaiheila.event.PrivateMessageEvent)

    def get_group_id(self, event: Event) -> Union[int, str, None]:
        if isinstance(event, self.kaiheila.event.ChannelMessageEvent):
            return event.group_id

    def get_group_role(self, event: Event) -> Optional[str]:
        return
