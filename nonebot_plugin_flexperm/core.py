import contextlib
from collections import OrderedDict
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union, Tuple, List, Set, Dict, Iterable

import nonebot
from nonebot.log import logger
from pydantic import BaseModel, parse_obj_as
from ruamel.yaml import YAML, YAMLError, CommentedMap, CommentedSeq

from .config import c

yaml = YAML()
nonebot_driver = nonebot.get_driver()

loaded: Dict[str, "Namespace"] = {}
loaded_by_path: Dict[Path, "Namespace"] = {}
plugin_namespaces: List["Namespace"] = []
default_groups: Set[str] = set()


def get(namespace: str, group: Union[str, int], referer: "PermissionGroup" = None, required: bool = False):
    """
    获取权限组。

    :param namespace: 名称空间。
    :param group: 组名。
    :param referer: 引用者。
    :param required: 权限组不存在时是否报错。若存在但有其他问题，则无论该参数设置，都会报错。
    :return:
        [0] 权限组，若失败则返回一个空组。 <br>
        [1] 是否成功。
    """
    return get_namespace(namespace, required).get_group(group, referer, required)


def get_namespace(namespace: str, required: bool, path_override: Path = None) -> "Namespace":
    ns = loaded.get(namespace)
    if ns is None:
        path = path_override or c.flexperm_base / f'{namespace}.yml'
        path = path.resolve()
        ns = loaded_by_path.get(path)
        if ns is None:
            ns = Namespace(namespace, path, required=required, modifiable=path_override is None)
            loaded_by_path[path] = ns
        loaded[namespace] = ns
    return ns


@nonebot_driver.on_startup
def reload(force: bool = False) -> bool:
    """
    使所有权限组在下一次使用时重新从配置加载。

    :param force: 强制重新加载，忽略未保存的修改。
    :return: 因有未保存的修改而没有重新加载时返回 False ，否则返回 True 。
    """
    if not force and any(x.dirty for x in loaded.values()):
        return False

    loaded.clear()
    loaded_by_path.clear()
    plugin_namespaces.clear()
    default_groups.clear()

    # 默认权限组
    global_ = get_namespace('global', False)
    defaults = Namespace('global', Path(__file__).parent / 'defaults.yml', required=True, modifiable=False)
    for k, v in defaults.config.items():
        global_.config.setdefault(k, v)
    default_groups.update(defaults.config)

    # 加载插件预设
    from .plugin import plugins
    for name, handler in plugins.items():
        if handler.preset_:
            namespace = get_namespace(name, True, handler.preset_)
            namespace.auto_decorate = handler.decorate_
            plugin_namespaces.append(namespace)

    # 生成全局组默认配置
    if not global_.path.is_file():
        global_.dirty = True
        global_.save()
    for name in ['group', 'user']:
        namespace = get_namespace(name, False)
        if not namespace.path.is_file():
            namespace.add_group(42, 'Example')
            namespace.save()

    return True


@nonebot_driver.on_shutdown
def save_all() -> bool:
    """
    保存所有权限配置。

    :return: 是否全部保存成功。
    """
    logger.debug('Saving permissions')
    failed = False
    for k, v in loaded.items():
        try:
            v.save()
        except Exception as e:
            _ = e
            failed = True
            logger.exception('Failed to save namespace {}', k)
    return not failed


try:
    sched = nonebot.require('nonebot_plugin_apscheduler').scheduler
    sched.add_job(save_all, 'interval', minutes=5, coalesce=True,
                  id='flexperm.save', replace_existing=True)
except (RuntimeError, AttributeError, TypeError):
    @nonebot_driver.on_startup
    def _():
        import asyncio

        async def save_timer():
            while True:
                await asyncio.sleep(5 * 60)
                save_all()

        asyncio.create_task(save_timer())


class Namespace:
    """
    权限组名称空间。每个名称空间对应一个配置文件。
    """

    auto_decorate: bool = False

    def __init__(self, namespace: str, path: Optional[Path], required: bool, modifiable: bool):
        self.name = namespace
        self.path = path
        self.groups: Dict[Union[str, int], PermissionGroup] = {}
        self.dirty = False
        self.modifiable = modifiable

        if not path:
            self.config = {}
            self.modifiable = False
        elif not required and not path.is_file():
            self.config = CommentedMap()
        else:
            try:
                doc = yaml.load(path)
            except (OSError, YAMLError):
                logger.exception('Failed to load namespace {} ({})', namespace, path)
                doc = {}

            if not isinstance(doc, CommentedMap):
                logger.error('Expect a dict: {} ({})', namespace, path)
                doc = {}

            self.config: CommentedMap[Union[str, int], dict] = doc

    def save(self):
        """
        把本名称空间保存到硬盘上。若没有修改过则不做任何事。
        """
        if self.modifiable and self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            yaml.dump(self.config, self.path)
            self.dirty = False

    def get_group(self, name: Union[str, int], referer: Optional["PermissionGroup"], required: bool
                  ) -> Tuple["PermissionGroup", bool]:
        """
        获取本名称空间下的权限组。

        :param name: 组名。
        :param referer: 引用者。
        :param required: 权限组不存在时是否报错。
        :return:
            [0] 权限组，若失败则返回一个空组。 <br>
            [1] 是否成功。
        """
        group = self.groups.get(name)
        if group is not None:
            if not group.referer:
                return group, group.namespace is not None

            cycle = [f'{self.name}:{name}']
            it = referer
            while it and not (it.name == name and it.namespace is self):
                cycle.append(it.qualified_name())
                it = it.referer
            cycle.append(f'{self.name}:{name}')
            logger.error('Inheritance cycle detected: {}', ' -> '.join(reversed(cycle)))
            return NullPermissionGroup(), False

        group, found = self._get_group_uncached(name, referer, required)
        self.groups[name] = group
        return group, found

    def _get_group_uncached(self, name: Union[str, int], referer: Optional["PermissionGroup"], required: bool
                            ) -> Tuple["PermissionGroup", bool]:
        group_desc = self.config.get(name)
        if group_desc is None:
            if required:
                if referer:
                    logger.error('Permission group {}:{} not found (required from {})',
                                 self.name, name, referer.qualified_name())
                else:
                    logger.error('Permission group {}:{} not found', self.name, name)
            return NullPermissionGroup(), False

        try:
            desc = parse_obj_as(GroupDesc, group_desc)
        except ValueError:
            logger.exception('Failed to parse {}:{} ({})', self.name, name, self.path)
            return NullPermissionGroup(), False

        # 注入插件预设
        if self.name == 'global' and name in default_groups:
            for pn in plugin_namespaces:
                if name in pn.config:
                    desc.inherits.append(f'{pn.name}:{name}')

        self.groups[name] = group = PermissionGroup(self, name)
        group.populate(desc, referer, self.name if self.auto_decorate else None)
        return group, True

    @contextmanager
    def modifying(self, name: Union[str, int] = None):
        if not self.modifiable:
            raise TypeError('Unmodifiable')
        yield self.config[name] if name is not None else None
        self.dirty = True

    def add_group(self, name: Union[str, int], comment: str = None):
        """
        创建权限组。

        :param name: 权限组名。
        :param comment: 注释。
        :raise KeyError: 权限组已存在。
        :raise TypeError: 名称空间不可修改。
        """
        with self.modifying():
            if name in self.config:
                raise KeyError('Duplicate group')
            self.config[name] = CommentedMap(permissions=CommentedSeq())
            if comment is not None:
                self.config.yaml_add_eol_comment(comment, name)
            self.groups.pop(name, None)

    def remove_group(self, name: Union[str, int], force: bool):
        """
        移除权限组。

        :param name: 权限组名。
        :param force: 是否允许移除非空的权限组。
        :raise KeyError: 权限组不存在。
        :raise ValueError: 因权限组非空而没有移除。
        :raise TypeError: 名称空间不可修改。
        """
        with self.modifying():
            if not force and any(self.config[name].values()):
                raise ValueError('Not empty')
            del self.config[name]
            self.groups.pop(name, None)


class PermissionGroup:
    """
    权限组。
    """

    # 仅在加载过程中有效，加载完成后恢复None。该权限组的引用者，若没有引用者则指向自己。
    referer: Optional["PermissionGroup"] = None

    def __init__(self, namespace: Namespace, name: Union[str, int]):
        self.namespace = namespace
        self.name = name
        self.denies: Set[str] = set()
        self.allows: Set[str] = set()
        self.inherits: List[PermissionGroup] = []
        self.cache: OrderedDict[str, CheckResult] = OrderedDict()

    def __repr__(self):
        return f'<PermissionGroup {self.qualified_name()}>'

    def qualified_name(self):
        return f'{self.namespace.name}:{self.name}'

    def check(self, perm: str) -> Optional["CheckResult"]:
        """
        检查本权限组对指定权限的说明。

        :param perm: 权限。
        :return: 查找结果，若不包含则返回 None 。
        """
        if perm in self.cache:
            self.cache.move_to_end(perm)
            return self.cache[perm]
        result = self._check_uncached(perm)
        if len(self.cache) > 127:
            self.cache.popitem(last=False)
        self.cache[perm] = result
        return result

    def _check_uncached(self, perm: str) -> Optional["CheckResult"]:
        if check_wildcard(perm, self.denies):
            return CheckResult.DENY
        if check_wildcard(perm, self.allows):
            return CheckResult.ALLOW

        allowed = False
        for inherit in self.inherits:
            r = inherit.check(perm)
            if r == CheckResult.DENY:
                return r
            elif r == CheckResult.ALLOW:
                allowed = True
        if allowed:
            return CheckResult.ALLOW

    def populate(self, desc: "GroupDesc", referer: Optional["PermissionGroup"], decorate_base: Optional[str]):
        """
        从描述中读取权限组内容，同时会加载依赖的组。

        :param desc: 权限组描述。
        :param referer: 引用者。
        :param decorate_base: 如果需要修饰，插件名。
        """
        self.referer = referer or self

        for parent in desc.inherits:
            namespace, group = parse_qualified_group_name(parent, self.namespace.name)
            res, found = get(namespace, group, self, True)
            if found:
                self.inherits.append(res)

        for item in desc.permissions:
            if item.startswith('-'):
                target = self.denies
                item = item[1:]
            else:
                target = self.allows
            if decorate_base is not None:
                [item] = decorate_permission(decorate_base, [item])
            target.add(item)

        del self.referer

    def add(self, item: str, comment: str = None):
        """
        添加权限描述。

        :param item: 权限描述。
        :param comment: 注释。
        :raise ValueError: 权限组中已有指定描述。
        :raise TypeError: 权限组不可修改。
        """
        with self.namespace.modifying(self.name) as desc:
            if item.startswith('-'):
                target = self.denies
                perm = item[1:]
            else:
                target = self.allows
                perm = item
            if perm in target:
                raise ValueError('Duplicate item')
            target.add(perm)
            self.cache.clear()
            permissions: CommentedSeq = desc.setdefault('permissions', CommentedSeq())
            permissions.append(item)
            if comment is not None:
                permissions.yaml_add_eol_comment(comment, len(permissions) - 1)  # yaml_add_eol_comment 不支持负数下标

    def remove(self, item: str):
        """
        移除权限描述。

        :param item: 权限描述。
        :raise ValueError: 权限组中没有指定描述。
        :raise TypeError: 权限组不可修改。
        """
        with self.namespace.modifying(self.name) as desc:
            if item.startswith('-'):
                target = self.denies
                perm = item[1:]
            else:
                target = self.allows
                perm = item
            if perm not in target:
                raise ValueError('No such item')
            target.remove(perm)
            self.cache.clear()
            permissions = desc['permissions']
            permissions.remove(item)

    def add_inheritance(self, target: "PermissionGroup", comment: str = None):
        """
        添加继承关系。

        :param target: 需继承权限组。
        :param comment: 注释。
        :raise ValueError: 权限组中已有指定继承关系。
        :raise TypeError: 权限组不可修改。
        """
        with self.namespace.modifying(self.name) as desc:
            if target in self.inherits:
                raise ValueError('Duplicate inheritance')
            self.inherits.append(target)
            self.cache.clear()
            inherits: CommentedSeq = desc.setdefault('inherits', CommentedSeq())
            inherits.append(target.qualified_name())
            if comment is not None:
                inherits.yaml_add_eol_comment(comment, len(inherits) - 1)  # yaml_add_eol_comment 不支持负数下标

    def remove_inheritance(self, target: "PermissionGroup"):
        """
        移除继承关系。

        :param target: 需移除继承权限组。
        :raise ValueError: 权限组中没有指定继承关系。
        :raise TypeError: 权限组不可修改。
        """
        with self.namespace.modifying(self.name) as desc:
            if target not in self.inherits:
                raise ValueError('No such inheritance')
            self.inherits.remove(target)
            self.cache.clear()

            inherits: CommentedSeq = desc.setdefault('inherits', CommentedSeq())
            possible_decls = [target.qualified_name()]
            if target.namespace is self.namespace:
                possible_decls.append(target.name)
            for decl in possible_decls:
                with contextlib.suppress(ValueError):
                    inherits.remove(decl)
                    break


class GroupDesc(BaseModel):
    """
    权限组描述。对应配置文件。
    """

    permissions: List[str] = []
    """
    授予或拒绝的权限列表。
    """

    inherits: List[str] = []
    """
    继承的权限组，每个元素为一个权限组名，可以表示为限定名（名称空间:组名），也可以不包含冒号，表示当前名称空间。
    """

    class Config:
        extra = 'forbid'


class CheckResult(Enum):
    ALLOW = 1
    DENY = 2


def check_wildcard(item: str, set_: Set[str]) -> bool:
    if item in set_:
        return True
    segments = item.split('.')
    segments.append('*')
    while segments:
        segments[-1] = '*'
        if '.'.join(segments) in set_:
            return True
        segments.pop()
    return False


def parse_qualified_group_name(qn: str, default_namespace: str = 'global') -> Tuple[str, Union[str, int]]:
    split = qn.split(':', maxsplit=1)
    if len(split) == 1:
        namespace, group = default_namespace, split[0]
    else:
        namespace, group = split
    if namespace in ['group', 'user']:
        with contextlib.suppress(ValueError):
            group = int(group)
    return namespace, group


def decorate_permission(base: str, perm: Iterable[str]) -> List[str]:
    result = []
    for p in perm:
        if not p:
            result.append(base)
        elif p.startswith('/'):
            result.append(p[1:])
        elif p.startswith('.'):
            prev = result[-1] if result else base
            result.append(prev + p)
        else:
            result.append(base + '.' + p)
    return result


if TYPE_CHECKING:
    class NullPermissionGroup(PermissionGroup):
        def __new__(cls, *args, **kwargs):
            raise TypeError

else:
    class NullPermissionGroup:
        referer = None
        namespace = None

        def __init__(self):
            pass

        def __repr__(self):
            return f'<NullPermissionGroup>'

        def check(self, perm):
            pass
