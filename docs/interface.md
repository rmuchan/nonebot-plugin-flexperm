# 接口文档

## register

注册一个需要使用本插件功能的插件，并获取交互对象。

参数：

- `plugin_name: str`，插件名。为避免冲突，建议使用插件包名（去掉`nonebot_plugin_`前缀）。

💬 插件名不能为 "global" ，强烈不建议使用 "user" 或 "group" 。

返回类型：`PluginHandler`

示例：

```python
from nonebot import require
P = require("nonebot_plugin_flexperm").register("my_plugin")
```

扩展阅读：[权限名称修饰](#权限名称修饰)。

### 类型标注

本插件在`__init__.pyi`文件中提供了`PluginHandler`类的接口说明，可用于支持 IDE 的代码提示、自动补全等功能。可以通过下面的方式使用：

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nonebot_plugin_flexperm import PluginHandler
P: "PluginHandler" = require("nonebot_plugin_flexperm").register("my_plugin")
```

注意：检查`TYPE_CHECKING`是必须的。为了避免不同来源多次加载本插件导致配置文件管理混乱，本插件被设计为**不允许直接`import`**。

## PluginHandler

通过`register`获得的交互对象。

### \_\_call__

创建权限检查器。

参数：

- `*perm: str`，需要检查的权限，若传入多个则须全部满足。
- 以下参数只能以关键字参数形式传入。
- `check_root: bool = ...`，如果传入布尔值，则替代之前`self.check_root()`的设定。

返回类型：`Permission`

示例：

```python
from nonebot import on_command
cmd = on_command("my_command", permission=P("my_command"))
```

### has

检查事件是否有指定权限，类似于未封装为检查器版本的`__call__`。

参数：

- `*perm: str`，需要检查的权限，若传入多个则须全部满足。
- `event: Event = None`，事件，默认为当前正在处理的事件。

返回类型：`bool`

示例：

```python
@cmd.handle()
async def _(bot, event):
    if P.has("my_command.inner"):
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

预设配置会被加载到与插件同名的名称空间中，允许被其他配置文件引用。与[六个默认权限组](permdesc.md#默认权限组)同名的会被相应组自动继承，无论后者保持默认还是使用自定义设置。

例如，上述示例代码的同一目录下`preset.yml`文件内容为：

```yaml
superuser:
  permissions:
    - my_plugin.*
  
editor:
  permissions:
    - my_plugin.read
    - my_plugin.write
```

此时，权限组`global:superuser`将自动继承`my_plugin:superuser`，因此超级用户自动具有`my_plugin`下所有子权限（除非被撤销）。权限组`my_plugin:editor`不会直接起作用，但其他权限组可以通过继承它来获得`my_plugin.read`和`my_plugin.write`两项权限。

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

### add_permission

向权限组添加一项权限。

实质是移除相应"撤销"权限描述，并添加"授予"权限描述，因此存在被更高优先级的权限组覆盖的可能。

参数：

- `designator: Union[Event, str, None]`，[权限组指示符](#权限组指示符)，可以缺省为`None`。
- `perm: str`，权限名。
- 以下参数只能以关键字参数形式传入。
- `comment: str = None`，注释，会以 YAML 注释的形式添加在配置文件对应项目的行尾。
- `create_group: bool = True`，如果权限组不存在，是否自动创建。

返回：

`bool`，是否确实更改了，如果权限组中已有指定"授予"权限描述则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在，并且指定为不自动创建。
- `TypeError`: 权限组不可修改。

### remove_permission

从权限组去除一项权限。

实质是移除相应"授予"权限描述，并添加"撤销"权限描述，因此存在被更高优先级的权限组覆盖的可能。

参数：

- `designator: Union[Event, str, None]`，[权限组指示符](#权限组指示符)，可以缺省为`None`。
- `perm: str`，权限名。
- 以下参数只能以关键字参数形式传入。
- `comment: str = None`，注释，会以 YAML 注释的形式添加在配置文件对应项目的行尾。
- `create_group: bool = True`，如果权限组不存在，是否自动创建。

返回：

`bool`，是否确实更改了，如果权限组中已有指定"撤销"权限描述则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在，并且指定为不自动创建。
- `TypeError`: 权限组不可修改。

### reset_permission

把权限组中关于一项权限的描述恢复默认。

实质是移除相应的"授予"和"撤销"权限描述，因此存在被更高优先级的权限组覆盖的可能。

参数：

- `designator: Union[Event, str, None]`，[权限组指示符](#权限组指示符)，可以缺省为`None`。
- `perm: str`，权限名。
- 以下参数只能以关键字参数形式传入。
- `allow_missing: bool = True`，如果权限组不存在，是否静默忽略。

返回：

`bool`，是否确实更改了，如果权限组中没有指定"授予"和"撤销"权限描述则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在，并且指定为不静默忽略。
- `TypeError`: 权限组不可修改。

### add_item

向权限组添加权限描述。

参数：

- `designator: Union[Event, str, None]`，[权限组指示符](#权限组指示符)，可以缺省为`None`。
- `item: str`，权限描述。
- 以下参数只能以关键字参数形式传入。
- `comment: str = None`，注释，会以 YAML 注释的形式添加在配置文件对应项目的行尾。
- `create_group: bool = True`，如果权限组不存在，是否自动创建。

返回：

`bool`，是否确实添加了，如果权限组中已有指定描述则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在，并且指定为不自动创建。
- `TypeError`: 权限组不可修改。

### remove_item

从权限组中移除权限描述。

参数：

- `designator: Union[Event, str, None]`，[权限组指示符](#权限组指示符)，可以缺省为`None`。
- `item: str`，权限描述。
- 以下参数只能以关键字参数形式传入。
- `allow_missing: bool = True`，如果权限组不存在，是否静默忽略。

返回：

`bool`，是否确实移除了，如果权限组中没有指定描述则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在，并且指定为不静默忽略。
- `TypeError`: 权限组不可修改。

### add_inheritance

向权限组添加继承关系。

参数：

- `designator: Union[Event, str, None]`，待修改权限组的[指示符](#权限组指示符)，可以缺省为`None`。
- `target: Union[Event, str, None]`，需继承权限组的[指示符](#权限组指示符)。**如省略名称空间则默认为当前插件。**
- 以下参数只能以关键字参数形式传入。
- `comment: str = None`，注释，会以 YAML 注释的形式添加在配置文件对应项目的行尾。
- `create_group: bool = True`，如果待修改权限组不存在，是否自动创建。

返回：

`bool`，是否确实添加了，如果权限组中已有指定继承关系则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 待修改权限组不存在，并且指定为不自动创建；或需继承的权限组不存在。
- `TypeError`: 权限组不可修改。

### remove_inheritance

从权限组中移除继承关系。

参数：

- `designator: Union[Event, str, None]`，待修改权限组的[指示符](#权限组指示符)，可以缺省为`None`。
- `target: Union[Event, str, None]`，需移除继承权限组的[指示符](#权限组指示符)。**如省略名称空间则默认为当前插件。**
- 以下参数只能以关键字参数形式传入。
- `allow_missing: bool = True`，如果待修改权限组不存在，是否静默忽略。

返回：

`bool`，是否确实移除了，如果权限组中没有指定继承关系则返回`False`。

可能抛出的异常及原因：

- `KeyError`: 待修改权限组不存在，并且指定为不静默忽略；或需移除继承的权限组不存在。
- `TypeError`: 权限组不可修改。

### add_group

创建权限组。

参数：

- `designator: Union[Event, str, None] = None`，[权限组指示符](#权限组指示符)。
- 以下参数只能以关键字参数形式传入。
- `comment: str = None`，注释，会以 YAML 注释的形式添加在配置文件对应项目的行尾。

可能抛出的异常及原因：

- `KeyError`: 权限组已存在。
- `TypeError`: 名称空间不可修改。

### remove_group

创建权限组。

参数：

- `designator: Union[Event, str, None] = None`，[权限组指示符](#权限组指示符)。
- 以下参数只能以关键字参数形式传入。
- `force: bool = False`，是否允许移除非空的权限组。

可能抛出的异常及原因：

- `KeyError`: 权限组不存在。
- `ValueError`: 因权限组非空而没有移除。
- `TypeError`: 名称空间不可修改。

# 词条解释

## 权限组指示符

权限组指示符可以是一个字符串、一个 NoneBot `Event` 对象或者`None`，在本插件的接口中的出现形式通常是名为`designator`的参数。指示符会按下列规则解释为名称空间和权限组名：

- 如果指示符是字符串：
  - 如果指示符包含冒号，则以第一个冒号之前的内容为名称空间，之后的内容为权限组名。
    - 如果名称空间是`group`或`user`，并且权限组名是一个整数，则自动调整为整型，否则保持为字符串。
  - 如果指示符不包含冒号，则**一般**代表`global`名称空间，整个指示符为权限组名。
    - 少数接口参数会将其解释为当前插件名称空间（[1](#add_inheritance) [2](#remove_inheritance)这两个接口的`target`参数）。
- 如果指示符是`Event`对象：
  - 对于群聊消息事件，代表`group`名称空间，群号为权限组名。
  - 对于私聊消息事件，代表`user`名称空间，用户ID（QQ号）为权限组名。
  - 其他事件类型暂不支持。
- 如果指示符是`None`：
  - 视为当前正在处理的事件。

## 权限名称修饰

通过 `register` 注册获得的 `PluginHandler` 对象保存了注册时传递的插件名，若无特殊说明，调用该对象接口时传递的权限名称（包括权限描述的权限名称部分）均会被修饰。

💬 修饰功能主要是考虑到不同插件作者可能选用相同的权限名称，用于避免不同插件的权限互相干扰。当前通过交互对象提供的接口全部有修饰处理，所以通常的应用无需特别考虑，只要编辑和检查权限时使用一致的写法即可指代同一权限。需要用户明确感知到修饰功能的场景主要有：(1) 直接编辑权限配置文件，(2) 使用本插件自己的[命令](command.md)。

修饰规则为：

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
