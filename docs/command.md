# 命令文档

## /flexperm.reload

重新加载权限配置。

⚠️ 通过命令或接口进行的修改若未保存则将丢失。

需要权限：`flexperm.reload`

## /flexperm.save

立即保存权限配置，用于通过命令或接口修改过配置之后。即使不使用这个命令，配置也会定期自动保存。

需要权限：`flexperm.reload`

## /flexperm.add

添加权限描述。

若未指定需要修改的权限组，则为当前会话所在群（私聊为用户）的权限组。若指定了权限组名但未指定名称空间，则为`global`名称空间。下同。

用法：`/flexperm.add [[名称空间:]权限组名] 权限描述`

需要权限：`flexperm.edit.perm`

## /flexperm.remove

移除权限描述。

用法：`/flexperm.remove [[名称空间:]权限组名] 权限描述`

需要权限：`flexperm.edit.perm`

## /flexperm.addgrp

添加权限组。

用法：`/flexperm.addgrp [[名称空间:]权限组名]`

需要权限：`flexperm.edit.group`

## /flexperm.rmgrp

移除权限组，权限组必须为空。

用法：`/flexperm.rmgrp [[名称空间:]权限组名]`

需要权限：`flexperm.edit.group`

## /flexperm.rmgrpf

移除权限组，权限组可以非空。

用法：`/flexperm.rmgrpf [[名称空间:]权限组名]`

需要权限：`flexperm.edit.group.force`
