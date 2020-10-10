@nl1@
identifier notify;
@@
struct netlink_notify *notify;
@@
identifier nl1.notify;
@@
-notify->portid
+netlink_notify_portid(notify)

// This works because no other struct in the kernel
// has an snd_portid member.
@@
expression info;
@@
-info->snd_portid
+genl_info_snd_portid(info)

// skb is an expression since it could be something
// other than just an identifier, e.g. cb->skb
@@
expression skb;
@@
-NETLINK_CB(skb).portid
+NETLINK_CB_PORTID(skb)
