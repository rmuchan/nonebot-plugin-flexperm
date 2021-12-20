from pathlib import Path
from typing import Optional, Dict, List, Iterable, Union

from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.permission import Permission

from .check import check
from .core import get, get_namespace

plugins: Dict[str, "PluginHandler"] = {}


def register(plugin_name: str) -> "PluginHandler":
    """
    注册插件，并获取交互对象。

    :param plugin_name: 插件名称，不能为"global"。
    :return: 交互对象。
    """
    if plugin_name == 'global':
        raise ValueError('Plugin shall not be named "global".')
    if plugin_name in plugins:
        logger.warning(f'Plugin {plugin_name} is registered twice!')
        return plugins[plugin_name]
    handler = PluginHandler(plugin_name)
    plugins[plugin_name] = handler
    return handler


class PluginHandler:
    def __init__(self, name: str):
        self.name = name
        self.preset_: Optional[Path] = None
        self.check_root_ = False

    def preset(self, preset: Path):
        """
        设置预设权限组，会被加载到插件名对应的名称空间。

        :param preset: 包含权限组的文件路径。
        :return: self
        """
        self.preset_ = preset
        return self

    def check_root(self):
        """
        设置自动检查根权限。

        :return: self
        """
        self.check_root_ = True
        return self

    def __call__(self, *perm: str) -> Permission:
        """
        创建权限检查器。若设置了 check_root ，则除了传入的权限外，还会检查本插件的根权限。

        权限名会自动按下列规则修饰：

        - 空串，会修改为插件名，即根权限。
        - 以"/"开头的，去掉"/"，不做其他修改。
        - 以"."开头的，在开头添加前一个权限名的修饰结果。若指定的第一个权限名就以"."开头，则添加插件名。
        - 否则，在开头添加 插件名+"." 。

        :param perm: 权限名，若传入多个权限则须同时满足。
        :return: 权限检查器，可以直接传递给 nonebot 事件响应器。
        """
        full = self._parse_perm(perm)
        if self.check_root_:
            full.insert(0, self.name)

        if len(full) == 1:
            single = full[0]

            async def _check(bot, event):
                return check(bot, event, single)
        else:
            async def _check(bot, event):
                return all(check(bot, event, px) for px in full)

        return Permission(_check)

    def has(self, bot: Bot, event: Event, *perm: str) -> bool:
        """
        检查事件是否具有指定权限。会修饰权限名，详见 __call__ 。不会自动检查根权限，无论是否设置 check_root 。

        :param bot: 机器人。
        :param event: 事件。
        :param perm: 权限名，若传入多个权限则须同时满足。
        :return: 检查结果。
        """
        full = self._parse_perm(perm)
        return all(check(bot, event, px) for px in full)

    def add_item(self, namespace: str, group: Union[str, int], item: str, comment: str = None,
                 create_group: bool = True) -> bool:
        """
        向权限组添加权限描述。会修饰权限名。

        :param namespace: 权限组名称空间。
        :param group: 权限组名。
        :param item: 权限描述。
        :param comment: 注释。
        :param create_group: 如果权限组不存在，是否自动创建。
        :return: 是否确实添加了，如果权限组中已有指定描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不自动创建。
        :raise TypeError: 权限组不可修改。
        """
        group_, found = get(namespace, group)
        if not found:
            if not create_group:
                raise KeyError('No such group')
            self.add_group(namespace, group)
            group_, _ = get(namespace, group)
        if item.startswith('-'):
            item = '-' + self._parse_perm([item[1:]])[0]
        else:
            item = self._parse_perm([item])[0]
        try:
            group_.add(item, comment)
            return True
        except ValueError:
            return False

    def remove_item(self, namespace: str, group: Union[str, int], item: str, allow_missing: bool = True) -> bool:
        """
        从权限组中移除权限描述。会修饰权限名。

        :param namespace: 权限组名称空间。
        :param group: 权限组名。
        :param item: 权限描述。
        :param allow_missing: 如果权限组不存在，是否静默忽略。
        :return: 是否确实移除了，如果权限组中没有指定描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不静默忽略。
        :raise TypeError: 权限组不可修改。
        """
        group_, found = get(namespace, group)
        if not found:
            if not allow_missing:
                raise KeyError('No such group')
            return False
        if item.startswith('-'):
            item = '-' + self._parse_perm([item[1:]])[0]
        else:
            item = self._parse_perm([item])[0]
        try:
            group_.remove(item)
            return True
        except ValueError:
            return False

    @classmethod
    def add_group(cls, namespace: str, group: Union[str, int], comment: str = None):
        """
        创建权限组。

        :param namespace: 权限组名称空间。
        :param group: 权限组名。
        :param comment: 注释。
        :raise KeyError: 权限组已存在。
        :raise TypeError: 名称空间不可修改。
        """
        get_namespace(namespace, False).add_group(group, comment)

    @classmethod
    def remove_group(cls, namespace: str, group: Union[str, int], force: bool):
        """
        移除权限组。

        :param namespace: 权限组名称空间。
        :param group: 权限组名。
        :param force: 是否允许移除非空的权限组。
        :raise KeyError: 权限组不存在。
        :raise ValueError: 因权限组非空而没有移除。
        :raise TypeError: 名称空间不可修改。
        """
        get_namespace(namespace, False).remove_group(group, force)

    def _parse_perm(self, perm: Iterable[str]) -> List[str]:
        result = []
        for p in perm:
            if not p:
                result.append(self.name)
            elif p.startswith('/'):
                result.append(p[1:])
            elif p.startswith('.'):
                prev = result[-1] if result else self.name
                result.append(prev + p)
            else:
                result.append(self.name + '.' + p)
        return result
