import contextlib
from pathlib import Path
from typing import Optional, Dict, Union, Tuple

from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.matcher import current_event
from nonebot.permission import Permission
from nonebot.plugin.export import export

from .check import check, get_permission_group_by_event
from .core import get, get_namespace, PermissionGroup, decorate_permission, parse_qualified_group_name

plugins: Dict[str, "PluginHandler"] = {}

_sentinel = object()
Designator = Union[Event, str, None]


@export()
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
        self.decorate_ = False
        self.check_root_ = False

    def preset(self, preset: Path, decorate: bool = False):
        """
        设置预设权限组，会被加载到插件名对应的名称空间。

        :param preset: 包含权限组的文件路径。
        :param decorate: 是否自动修饰预设包含的权限名。
        :return: self
        """
        self.preset_ = preset
        self.decorate_ = decorate
        return self

    def check_root(self):
        """
        设置自动检查根权限。

        :return: self
        """
        self.check_root_ = True
        return self

    def __call__(self, *perm: str, check_root: bool = _sentinel) -> Permission:
        """
        创建权限检查器。若设置了 check_root ，则除了传入的权限外，还会检查本插件的根权限。

        权限名会自动按下列规则修饰：

        - 空串，会修改为插件名，即根权限。
        - 以"/"开头的，去掉"/"，不做其他修改。
        - 以"."开头的，在开头添加前一个权限名的修饰结果。若指定的第一个权限名就以"."开头，则添加插件名。
        - 否则，在开头添加 插件名+"." 。

        :param perm: 权限名，若传入多个权限则须同时满足。
        :param check_root: 如果传入布尔值，则替代之前 self.check_root() 的设定。
        :return: 权限检查器，可以直接传递给 nonebot 事件响应器。
        """
        full = decorate_permission(self.name, perm)
        if check_root is _sentinel:
            check_root = self.check_root_
        if check_root:
            full.insert(0, self.name)

        if len(full) == 1:
            single = full[0]

            async def _check(event):
                return check(event, single)
        else:
            async def _check(event):
                return all(check(event, px) for px in full)

        return Permission(_check)

    def has(self, *perm: str, event: Event = None) -> bool:
        """
        检查事件是否具有指定权限。会修饰权限名，详见 __call__ 。不会自动检查根权限，无论是否设置 check_root 。

        :param perm: 权限名，若传入多个权限则须同时满足。
        :param event: 事件，默认为当前正在处理的事件。
        :return: 检查结果。
        """
        if event is None:
            event = current_event.get()
        full = decorate_permission(self.name, perm)
        return all(check(event, px) for px in full)

    def add_permission(self, designator: Designator, perm: str = _sentinel, *,
                       comment: str = None, create_group: bool = True) -> bool:
        """
        向权限组添加一项权限。会修饰权限名。

        实质是移除 perm 的"撤销"权限描述，并添加"授予"权限描述。

        :param designator: 权限组指示符。
        :param perm: 权限名。
        :param comment: 注释。
        :param create_group: 如果权限组不存在，是否自动创建。
        :return: 是否确实更改了，如果权限组中已有指定"授予"权限描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不自动创建。
        :raise TypeError: 权限组不可修改。
        """
        if perm is _sentinel:
            designator, perm = None, designator

        group_ = self._get_or_create_group(designator, create_group, True)
        [perm] = decorate_permission(self.name, [perm])
        with contextlib.suppress(ValueError):
            group_.remove('-' + perm)
        try:
            group_.add(perm, comment)
            return True
        except ValueError:
            return False

    def remove_permission(self, designator: Designator, perm: str = _sentinel, *,
                          comment: str = None, create_group: bool = True) -> bool:
        """
        从权限组去除一项权限。会修饰权限名。

        实质是移除 perm 的"授予"权限描述，并添加"撤销"权限描述。

        :param designator: 权限组指示符。
        :param perm: 权限名。
        :param comment: 注释。
        :param create_group: 如果权限组不存在，是否自动创建。
        :return: 是否确实更改了，如果权限组中已有指定"撤销"权限描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不自动创建。
        :raise TypeError: 权限组不可修改。
        """
        if perm is _sentinel:
            designator, perm = None, designator

        group_ = self._get_or_create_group(designator, create_group, True)
        [perm] = decorate_permission(self.name, [perm])
        with contextlib.suppress(ValueError):
            group_.remove(perm)
        try:
            group_.add('-' + perm, comment)
            return True
        except ValueError:
            return False

    def reset_permission(self, designator: Designator, perm: str = _sentinel, *,
                         allow_missing: bool = True) -> bool:
        """
        把权限组中关于一项权限的描述恢复默认。会修饰权限名。

        实质是移除 perm 的"授予"和"撤销"权限描述，使得检查时会检索到更低层级权限组的设置。

        :param designator: 权限组指示符。
        :param perm: 权限名。
        :param allow_missing: 如果权限组不存在，是否静默忽略。
        :return: 是否确实更改了，如果权限组中没有指定"授予"和"撤销"权限描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不静默忽略。
        :raise TypeError: 权限组不可修改。
        """
        if perm is _sentinel:
            designator, perm = None, designator

        group_ = self._get_or_create_group(designator, allow_missing, False)
        if group_ is None:
            return False
        [perm] = decorate_permission(self.name, [perm])
        # noinspection PyUnusedLocal
        modified = False
        with contextlib.suppress(ValueError):
            group_.remove(perm)
            # noinspection PyUnusedLocal
            modified = True
        with contextlib.suppress(ValueError):
            group_.remove('-' + perm)
            modified = True
        return modified

    def add_item(self, designator: Designator, item: str = _sentinel, *,
                 comment: str = None, create_group: bool = True) -> bool:
        """
        向权限组添加权限描述。会修饰权限名。

        :param designator: 权限组指示符。
        :param item: 权限描述。
        :param comment: 注释。
        :param create_group: 如果权限组不存在，是否自动创建。
        :return: 是否确实添加了，如果权限组中已有指定描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不自动创建。
        :raise TypeError: 权限组不可修改。
        """
        if item is _sentinel:
            designator, item = None, designator

        group_ = self._get_or_create_group(designator, create_group, True)
        if item.startswith('-'):
            [item] = decorate_permission(self.name, [item[1:]])
            item = '-' + item
        else:
            [item] = decorate_permission(self.name, [item])
        try:
            group_.add(item, comment)
            return True
        except ValueError:
            return False

    def remove_item(self, designator: Designator, item: str = _sentinel, *,
                    allow_missing: bool = True) -> bool:
        """
        从权限组中移除权限描述。会修饰权限名。

        :param designator: 权限组指示符。
        :param item: 权限描述。
        :param allow_missing: 如果权限组不存在，是否静默忽略。
        :return: 是否确实移除了，如果权限组中没有指定描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不静默忽略。
        :raise TypeError: 权限组不可修改。
        """
        if item is _sentinel:
            designator, item = None, designator

        group_ = self._get_or_create_group(designator, allow_missing, False)
        if group_ is None:
            return False
        if item.startswith('-'):
            [item] = decorate_permission(self.name, [item[1:]])
            item = '-' + item
        else:
            [item] = decorate_permission(self.name, [item])
        try:
            group_.remove(item)
            return True
        except ValueError:
            return False

    def add_inheritance(self, designator: Designator, target: Designator = _sentinel, *,
                        comment: str = None, create_group: bool = True) -> bool:
        """
        向权限组添加继承关系。

        :param designator: 待修改权限组的指示符。
        :param target: 需继承权限组的指示符。<em>如省略名称空间则默认为当前插件。</em>
        :param comment: 注释。
        :param create_group: 如果待修改权限组不存在，是否自动创建。
        :return: 是否确实添加了，如果权限组中已有指定继承关系则返回 False 。
        :raise KeyError: 待修改权限组不存在，并且指定为不自动创建；或需继承的权限组不存在。
        :raise TypeError: 权限组不可修改。
        """
        if target is _sentinel:
            designator, target = None, designator

        ancestor = self._get_or_create_group(target, False, False, self.name)
        group_ = self._get_or_create_group(designator, create_group, True)
        try:
            group_.add_inheritance(ancestor, comment)
            return True
        except ValueError:
            return False

    def remove_inheritance(self, designator: Designator, target: Designator = _sentinel, *,
                           allow_missing: bool = True) -> bool:
        """
        从权限组中移除继承关系。

        :param designator: 待修改权限组的指示符。
        :param target: 需移除继承权限组的指示符。<em>如省略名称空间则默认为当前插件。</em>
        :param allow_missing: 如果待修改权限组不存在，是否静默忽略。
        :return: 是否确实移除了，如果权限组中没有指定继承关系则返回 False 。
        :raise KeyError: 待修改权限组不存在，并且指定为不静默忽略；或需移除继承的权限组不存在。
        :raise TypeError: 权限组不可修改。
        """
        if target is _sentinel:
            designator, target = None, designator

        group_ = self._get_or_create_group(designator, allow_missing, False)
        if group_ is None:
            return False
        ancestor = self._get_or_create_group(target, False, False, self.name)
        try:
            group_.remove_inheritance(ancestor)
            return True
        except ValueError:
            return False

    @classmethod
    def add_group(cls, designator: Designator = None, *, comment: str = None):
        """
        创建权限组。

        :param designator: 权限组指示符。
        :param comment: 注释。
        :raise KeyError: 权限组已存在。
        :raise TypeError: 名称空间不可修改。
        """
        namespace, group = cls._parse_designator(designator)
        get_namespace(namespace, False).add_group(group, comment)

    @classmethod
    def remove_group(cls, designator: Designator = None, *, force: bool = False):
        """
        移除权限组。

        :param designator: 权限组指示符。
        :param force: 是否允许移除非空的权限组。
        :raise KeyError: 权限组不存在。
        :raise ValueError: 因权限组非空而没有移除。
        :raise TypeError: 名称空间不可修改。
        """
        namespace, group = cls._parse_designator(designator)
        get_namespace(namespace, False).remove_group(group, force)

    @classmethod
    def _parse_designator(cls, designator: Designator, default_namespace: str = 'global'
                          ) -> Tuple[str, Union[str, int]]:
        if designator is None:
            designator = current_event.get()
        if isinstance(designator, Event):
            result = get_permission_group_by_event(designator)
            if result is not None:
                return result
            raise ValueError('Unrecognized event type: ' + designator.get_event_name())
        if isinstance(designator, str):
            return parse_qualified_group_name(designator, default_namespace)
        raise ValueError(f'Invalid designator: {type(designator)}')

    @classmethod
    def _get_or_create_group(cls, designator: Designator, silent: bool, create: bool, default_namespace: str = 'global'
                             ) -> Optional[PermissionGroup]:
        namespace, group = cls._parse_designator(designator, default_namespace)
        group_, found = get(namespace, group)
        if not found:
            if not silent:
                raise KeyError('No such group')
            if not create:
                return None
            get_namespace(namespace, False).add_group(group)
            group_, _ = get(namespace, group)
        return group_
