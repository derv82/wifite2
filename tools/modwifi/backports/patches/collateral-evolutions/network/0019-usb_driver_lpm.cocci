@@
identifier backport_driver;
@@
struct usb_driver backport_driver = {
+#if (LINUX_VERSION_CODE >= KERNEL_VERSION(3,5,0))
	.disable_hub_initiated_lpm = 1,
+#endif
...
};
