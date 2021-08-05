from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import Optional, Union, Tuple, List, Set, Dict

import nonebot
from nonebot.log import logger
from pydantic import BaseModel, parse_obj_as
from ruamel.yaml import YAML, YAMLError

from .config import c

yaml = YAML()
nonebot_driver = nonebot.get_driver()

loaded: Dict[str, "Namespace"] = {}
plugin_namespaces: List["Namespace"] = []


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
        if path_override:
            ns = Namespace(namespace, required, path_override, False)
        else:
            ns = Namespace(namespace, required, c.permman_base / f'{namespace}.yml', True)
        loaded[namespace] = ns
    return ns


@nonebot_driver.on_startup
def reload():
    """
    使所有权限组在下一次使用时重新从配置加载。
    """
    loaded.clear()
    plugin_namespaces.clear()

    # 默认权限组
    global_ = get_namespace('global', False)
    defaults = Namespace('global', True, Path(__file__).parent / 'defaults.yml', False)
    for k, v in defaults.config.items():
        global_.config.setdefault(k, v)

    # 加载插件预设
    from .plugin import plugins
    for name, handler in plugins.items():
        if handler.preset:
            namespace = get_namespace(name, True, handler.preset)
            plugin_namespaces.append(namespace)


class Namespace:
    """
    权限组名称空间。每个名称空间对应一个配置文件。
    """

    def __init__(self, namespace: str, required: bool, path: Optional[Path], modifiable: bool):
        self.name = namespace
        self.path = path
        self.groups: Dict[Union[str, int], PermissionGroup] = {}
        self.dirty = False
        self.modifiable = modifiable

        if not path:
            self.config = {}
            self.modifiable = False
        elif not required and not path.is_file():
            self.config = {}
        else:
            try:
                doc = yaml.load(path)
            except (OSError, YAMLError):
                logger.exception('Failed to load namespace {} ({})', namespace, path)
                doc = {}

            if not isinstance(doc, dict):
                logger.error('Expect a dict: {} ({})', namespace, path)
                doc = {}

            self.config: Dict[Union[str, int], dict] = doc

    def save(self):
        """
        把本名称空间保存到硬盘上。若没有修改过则不做任何事。
        """
        if self.modifiable and self.dirty:
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
                return group, True

            cycle = [f'{self.name}:{name}']
            it = referer
            while it and not (it.name == name and it.namespace is self):
                cycle.append(f'{it.namespace.name}:{it.name}')
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
                    logger.error('Permission group {}:{} not found (required from {}:{})',
                                 self.name, name, referer.namespace.name, referer.name)
                else:
                    logger.error('Permission group {}:{} not found', self.name, name)
            return NullPermissionGroup(), False

        try:
            desc = parse_obj_as(GroupDesc, group_desc)
        except ValueError:
            logger.exception('Failed to parse {}:{} ({})', self.name, name, self.path)
            return NullPermissionGroup(), False

        # 注入插件预设
        if self.name == 'global':
            for pn in plugin_namespaces:
                if name in pn.config:
                    desc.inherits.append(f'{pn.name}:{name}')

        self.groups[name] = group = PermissionGroup(self, name)
        group.populate(desc, referer)
        return group, True


class PermissionGroup:
    """
    权限组。
    """

    # 仅在加载过程中有效，加载完成后恢复None。该权限组的引用者，若没有引用者则指向自己。
    referer: Optional["PermissionGroup"] = None

    def __init__(self, namespace: Optional[Namespace], name: Union[str, int]):
        if namespace is not None:
            self.namespace = namespace
            self.name = name
            self.denies: Set[str] = set()
            self.allows: Set[str] = set()
            self.inherits: List[PermissionGroup] = []
            self.cache: OrderedDict[str, CheckResult] = OrderedDict()

    def __repr__(self):
        return f'<PermissionGroup {self.namespace.name}:{self.name}>'

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

    def populate(self, desc: "GroupDesc", referer: Optional["PermissionGroup"]):
        """
        从描述中读取权限组内容，同时会加载依赖的组。

        :param desc: 权限组描述。
        :param referer: 引用者。
        """
        self.referer = referer or self

        for parent in desc.inherits:
            split = parent.split(':', maxsplit=1)
            if not split:
                continue
            if len(split) == 1:
                res, found = get(self.namespace.name, split[0], self, True)
            else:
                res, found = get(split[0], split[1], self, True)
            if found:
                self.inherits.append(res)

        for item in desc.permissions:
            if item.startswith('-'):
                target = self.denies
                item = item[1:]
            else:
                target = self.allows
            target.add(item)

        del self.referer


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
    while segments:
        segments[-1] = '*'
        if '.'.join(segments) in set_:
            return True
        del segments[-2:]
    return False


class NullPermissionGroup(PermissionGroup):
    def __init__(self):
        super().__init__(None, 'empty')

    def __repr__(self):
        return f'<NullPermissionGroup>'

    def check(self, perm):
        pass

    def populate(self, desc, referer):
        raise TypeError
