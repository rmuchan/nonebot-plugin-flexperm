from pathlib import Path

import nonebot
from pydantic import BaseModel


class Config(BaseModel):
    flexperm_base: Path = Path('permissions')
    flexperm_debug_check: bool = False
    flexperm_export: bool = True


c = Config(**nonebot.get_driver().config.dict())
