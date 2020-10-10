/*
The new attribute sysfs group was added onto struct class via
commit d05a6f96c

mcgrof@ergon ~/linux (git::master)$ git describe --contains d05a6f96c
v3.11-rc2~18^2~3

This backpoort makes use of the helpers to backport this more efficiently.
Refer to the INFO file for documentation there on that.

commit d05a6f96c76062b5f25858ac02cf677602076f7e
Author: Greg Kroah-Hartman <gregkh@linuxfoundation.org>
Date:   Sun Jul 14 16:05:58 2013 -0700

    driver core: add default groups to struct class

    We should be using groups, not attribute lists, for classes to allow
    subdirectories, and soon, binary files.  Groups are just more flexible
    overall, so add them.

    The dev_attrs list will go away after all in-kernel users are converted
    to use dev_groups.

    Reviewed-by: Guenter Roeck <linux@roeck-us.net>
    Tested-by: Guenter Roeck <linux@roeck-us.net>
    Signed-off-by: Greg Kroah-Hartman <gregkh@linuxfoundation.org>
*/

@ attribute_group @
identifier group;
declarer name ATTRIBUTE_GROUPS;
@@

ATTRIBUTE_GROUPS(group);

@ class_group depends on attribute_group @
identifier group_class;
expression groups;
fresh identifier group_dev_attr = attribute_group.group ## "_dev_attrs";
@@

struct class group_class = {
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,11,0)
	.dev_groups = groups,
+#else
+	.dev_attrs = group_dev_attr,
+#endif
};

@ attribute_group_mod depends on attribute_group && class_group @
declarer name ATTRIBUTE_GROUPS_BACKPORT;
identifier group;
@@

+#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,11,0)
ATTRIBUTE_GROUPS(group);
+#else
+#define BP_ATTR_GRP_STRUCT device_attribute
+ATTRIBUTE_GROUPS_BACKPORT(group);
+#endif

@ class_registering depends on class_group && attribute_group_mod @
identifier class_register, ret;
identifier class_group.group_class;
fresh identifier group_class_init = "init_" ## attribute_group_mod.group ## "_attrs";
@@

(
+	group_class_init();
	return class_register(&group_class);
|
+	group_class_init();
	ret = class_register(&group_class);
)
