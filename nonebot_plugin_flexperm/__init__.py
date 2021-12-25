from nonebot.plugin.manager import PluginLoader

# noinspection PyUnresolvedReferences
if type(__loader__) is not PluginLoader:
    raise TypeError('Do not import flexperm directly. Use "nonebot.require".')

from . import plugin as _
from . import cmds as _
