from pathlib import Path

import nonebot
from pydantic import BaseModel


class Config(BaseModel):
    permman_base: Path = Path('permissions')
    permman_debug_check: bool = False


c = Config(**nonebot.get_driver().config.dict())
