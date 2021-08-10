# nonebot-plugin-flexperm

精细化的 NoneBot 权限管理插件。

提供对用户精确到人或群、对插件精确到指令或更细粒度的权限管理功能。

## 安装

- 使用 nb-cli

```shell
nb plugin install nonebot-plugin-flexperm
```

- 使用 poetry

```shell
poetry add nonebot-plugin-flexperm
```

- 使用 pip

```shell
pip install nonebot-plugin-flexperm
```

## 依赖

目前只支持 cqhttp 协议，之后可能会支持其他协议。

## 使用

本插件主要通过 NoneBot 的 require 机制向**其他插件**提供功能。本插件也提供了一组命令，用于直接管理权限配置。

```python
from nonebot import require
P = require("nonebot_plugin_flexperm").register("my_plugin")
```

`P`是一个可调用对象，以权限名为参数调用即可得到相应的检查器。`P`的其他接口详见[接口文档](docs/interface.md)。

```python
from nonebot import on_command
cmd = on_command("my_command", permission=P("my_command"))

@cmd.handle()
async def _(bot, event):
    ...
```

这样，运行时只有具有`my_plugin.my_command`权限的用户或群才能使用该命令。

### 权限配置文件

权限配置文件使用 YAML 格式，详见[权限配置文档](docs/permdesc.md)。示例：

```yaml
anyone:
  permissions:
    - my_plugin.help

group_admin:
  permissions:
    - my_plugin.my_command
    - another_plugin.*
    - -another_plugin.another_command
```

这个配置文件授予了所有用户`my_plugin.help`权限，同时授予了群管理员`my_plugin.my_command`权限和`another_plugin`下的所有子权限，但撤销`another_plugin.another_command`权限。

### 命令

权限配置文件可以在运行时修改，然后使用`/flexperm.reload`命令重新加载。

也可以通过命令编辑权限配置，详见[命令文档](docs/command.md)。

## 配置

本插件使用两个配置项，均为可选。如需修改，写入 NoneBot 项目环境文件`.env.*`即可。

- `flexperm_base`: 权限配置文件所在目录，默认为`permissions`。
- `flexperm_debug_check`: 是否输出检查权限过程中的调试信息，默认为`false`。未启用 NoneBot 的调试模式时无效。

## 鸣谢

- [nonebot / nonebot2](https://github.com/nonebot/nonebot2)
- [Mrs4s / go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
