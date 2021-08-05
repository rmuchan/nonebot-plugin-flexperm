from pathlib import Path

import nonebot
from pydantic import BaseModel


class Config(BaseModel):
    permman_base: Path = Path('permissions')


c = Config(**nonebot.get_driver().config.dict())
