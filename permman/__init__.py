from nonebot import export

from . import cmds
from .plugin import register

export().register = register

del export, cmds, register
