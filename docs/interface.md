# 接口文档

## register

注册一个需要使用本插件功能的插件，并获取交互对象。

参数：

- `plugin_name: str`，插件名，不能为"global"。为避免冲突，建议使用插件包名（去掉`nonebot_plugin_`前缀）。

返回类型：`PluginHandler`

示例：

```python
from nonebot import require
P = require("nonebot_plugin_flexperm").register("my_plugin")
```

## PluginHandler

通过`register`获得的交互对象。

该对象保存了注册时传递的插件名，若无特殊说明，调用该对象接口时传递的权限名（包括权限描述的权限名部分）均会被修饰，规则如下：

- 空串，改为插件名，即根权限。
- 以`/`开头的，去掉`/`，不做其他修改。
- 以`.`开头的，在开头添加前一个权限名的修饰结果。若指定的第一个权限名就以`.`开头，则添加插件名。
- 否则，在开头添加 插件名+`.` 。

例如：

- `P("")`检查`my_plugin`权限
- `P("a.b")`检查`my_plugin.a.b`权限
- `P("/a.b")`检查`a.b`权限
- `P("/a", ".b", ".c")`检查`a`、`a.b`和`a.b.c`三个权限
- `P("a", ".b", "/c")`检查`my_plugin.a`、`my_plugin.a.b`和`c`三个权限

### \_\_call__

创建权限检查器。

参数：

- `*perm: str`，需要检查的权限，若传入多个则须全部满足。

返回类型：`Permission`

示例：

```python
from nonebot import on_command
cmd = on_command("my_command", permission=P("my_command"))
```

### has

检查事件是否有指定权限，类似于未封装为检查器版本的`__call__`。

参数：

- `bot: Bot`，机器人。
- `event: Event`，事件。
- `*perm: str`，需要检查的权限，若传入多个则须全部满足。

返回类型：`bool`

示例：

```python
@cmd.handle()
async def _(bot, event):
    if P.has(bot, event, "my_command.inner"):
        ...
```

### preset

设置插件预设权限配置。多次设置仅最后一次有效。

参数：

- `preset: Path`，预设文件路径。

返回`self`，可以在`register`之后直接链式调用。

示例：

```python
from pathlib import Path

P.preset(Path(__file__).parent / "preset.yml")
```

说明：

预设配置会被加载到与插件同名的名称空间中，允许被其他配置文件引用。与默认的六个权限组同名的会自动加入到相应默认组的继承列表里。例如，上述示例代码的同一目录下`preset.yml`文件内容为：

```yaml
superuser:
  permissions:
    - my_plugin.*
  
editor:
  permissions:
    - my_plugin.read
    - my_plugin.write
```

此时，默认组`global:superuser`将自动继承`my_plugin:superuser`，因此超级用户自动具有`my_plugin`下所有子权限（除非被撤销）。权限组`my_plugin:editor`不会直接起作用，但其他权限组可以通过继承它来获得`my_plugin.read`和`my_plugin.write`两项权限。

### check_root

设置`__call__`自动检查根权限。

参数：无

返回`self`，可以在`register`之后直接链式调用。

示例：

```python
P.check_root()
```

说明：

未设置`check_root`的情况下，`__call__`返回的检查器只会检查显式传递给它的权限，例如`P("a.b.c")`会检查`my_plugin.a.b.c`权限。设置`check_root`后，`P("a.b.c")`将检查`my_plugin`和`my_plugin.a.b.c`两个权限，用户必须同时拥有这两个权限才能使用功能。主要可以应用于在不同会话中启用/禁用整个插件。

只作用于`__call__`，`has`不受影响。

### add_item

向权限组添加权限描述。

参数：

- `namespace: str`，权限组名称空间。
- `group: Union[str, int]`，权限组名。
- `item: str`，权限描述。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在。
- `ValueError`: 权限组中已有指定描述。
- `TypeError`: 权限组不可修改。

### remove_item

从权限组中移除权限描述。

参数：

- `namespace: str`，权限组名称空间。
- `group: Union[str, int]`，权限组名。
- `item: str`，权限描述。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在。
- `ValueError`: 权限组中没有指定描述。
- `TypeError`: 权限组不可修改。

### add_group

创建权限组。

参数：

- `namespace: str`，权限组名称空间。
- `group: Union[str, int]`，权限组名。

可能抛出的异常及原因：

- `KeyError`: 权限组已存在。
- `TypeError`: 名称空间不可修改。

### remove_group

创建权限组。

参数：

- `namespace: str`，权限组名称空间。
- `group: Union[str, int]`，权限组名。
- `force: bool`，是否允许移除非空的权限组。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在。
- `ValueError`: 因权限组非空而没有移除。
- `TypeError`: 名称空间不可修改。