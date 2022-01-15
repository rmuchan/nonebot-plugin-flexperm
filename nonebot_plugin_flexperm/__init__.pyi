from pathlib import Path
from typing import Union

from nonebot.adapters import Event
from nonebot.permission import Permission


def register(plugin_name: str) -> "PluginHandler":
    """
    注册插件，并获取交互对象。

    :param plugin_name: 插件名称，不能为"global"。
    :return: 交互对象。
    """

class PluginHandler:
    def preset(self, preset: Path) -> "PluginHandler":
        """
        设置预设权限组，会被加载到插件名对应的名称空间。

        :param preset: 包含权限组的文件路径。
        :return: self
        """

    def check_root(self) -> "PluginHandler":
        """
        设置自动检查根权限。

        :return: self
        """

    def __call__(self, *perm: str, check_root: bool = ...) -> Permission:
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

    def has(self, *perm: str, event: Event = None) -> bool:
        """
        检查事件是否具有指定权限。会修饰权限名，详见 __call__ 。不会自动检查根权限，无论是否设置 check_root 。

        :param perm: 权限名，若传入多个权限则须同时满足。
        :param event: 事件，默认为当前正在处理的事件。
        :return: 检查结果。
        """

    def add_permission(self, designator: Union[Event, str, None], perm: str, *,
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

    def remove_permission(self, designator: Union[Event, str, None], perm: str, *,
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

    def reset_permission(self, designator: Union[Event, str, None], perm: str, *, allow_missing: bool = True) -> bool:
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

    def add_item(self, designator: Union[Event, str, None], item: str, *,
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

    def remove_item(self, designator: Union[Event, str, None], item: str, *, allow_missing: bool = True) -> bool:
        """
        从权限组中移除权限描述。会修饰权限名。

        :param designator: 权限组指示符。
        :param item: 权限描述。
        :param allow_missing: 如果权限组不存在，是否静默忽略。
        :return: 是否确实移除了，如果权限组中没有指定描述则返回 False 。
        :raise KeyError: 权限组不存在，并且指定为不静默忽略。
        :raise TypeError: 权限组不可修改。
        """

    def add_group(self, designator: Union[Event, str, None], *, comment: str = None) -> None:
        """
        创建权限组。

        :param designator: 权限组指示符。
        :param comment: 注释。
        :raise KeyError: 权限组已存在。
        :raise TypeError: 名称空间不可修改。
        """

    def remove_group(self, designator: Union[Event, str, None], *, force: bool = False) -> None:
        """
        移除权限组。

        :param designator: 权限组指示符。
        :param force: 是否允许移除非空的权限组。
        :raise KeyError: 权限组不存在。
        :raise ValueError: 因权限组非空而没有移除。
        :raise TypeError: 名称空间不可修改。
        """
