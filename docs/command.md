# 命令文档

与 NoneBot2 的默认行为不同，本插件的所有命令（无参数的除外）要求命令名和参数之间有空格隔开。

## /flexperm.reload

重新加载权限配置。

如果有通过命令或接口进行的修改尚未保存则会拒绝重新加载，可以使用`force`参数忽略这一检查。

用法：`/flexperm.reload [force]`

需要权限：`flexperm.reload`

## /flexperm.save

立即保存权限配置，用于通过命令或接口修改过配置之后。即使不使用这个命令，配置也会定期自动保存。

需要权限：`flexperm.reload`

## /flexperm.add

添加权限描述。

如果没有提供权限组指示符，则默认使用当前会话所代表的权限组。详见[权限组指示符](interface.md#权限组指示符)。

**不会**自动[修饰](interface.md#权限名称修饰)权限名，需要填入目标权限的正式名称。

用法：`/flexperm.add [权限组指示符] 权限描述`

需要权限：`flexperm.edit.perm`

## /flexperm.remove

移除权限描述。

**不会**自动[修饰](interface.md#权限名称修饰)权限名，需要填入目标权限的正式名称。

用法：`/flexperm.remove [权限组指示符] 权限描述`

需要权限：`flexperm.edit.perm`

## /flexperm.addinh

添加继承关系。

用法：`/flexperm.addinh [权限组指示符] 继承权限组的指示符`

需要权限：`flexperm.edit.inherit`

## /flexperm.rminh

移除继承关系。

用法：`/flexperm.rminh [权限组指示符] 继承权限组的指示符`

需要权限：`flexperm.edit.inherit`

## /flexperm.addgrp

添加权限组。

用法：`/flexperm.addgrp [权限组指示符]`

需要权限：`flexperm.edit.group`

## /flexperm.rmgrp

移除权限组，权限组必须为空。

用法：`/flexperm.rmgrp [权限组指示符]`

需要权限：`flexperm.edit.group`

## /flexperm.rmgrpf

移除权限组，权限组可以非空。

用法：`/flexperm.rmgrpf [权限组指示符]`

需要权限：`flexperm.edit.group.force`
