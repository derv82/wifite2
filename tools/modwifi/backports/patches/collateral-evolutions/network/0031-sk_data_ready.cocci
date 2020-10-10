/*
Commit 676d2369 by David removed the skb->len arguments passed onto
the struct sock sk_data_ready() callback. This was done as its racy,
a few drivers were passing 0 to it, and it was not really used.
By removing it the raciness is addresed but to backport this we are
going to have to deal with the races as-is on older kernels. This was
merged as of v3.15:

mcgrof@ergon ~/linux-next (git::master)$ git describe --contains 676d2369
v3.15-rc1~8^2~10

Since this is not a define or static inline we can't easily replace this with
the backports module or header files, instead we use SmPL grammar to generalize
the backport for all use cases. Note that in order to backport this we won't
know what older kernel drivers were using before this change, it could have
been 0 or skb->len for the length parameter, since we have to infer something
we choose skb->len *iff* skb_queue_tail() was used right before it, otherwise
we infer to throw 0.

commit 676d23690fb62b5d51ba5d659935e9f7d9da9f8e
Author: David S. Miller <davem@davemloft.net>
Date:   Fri Apr 11 16:15:36 2014 -0400

    net: Fix use after free by removing length arg from sk_data_ready callbacks.
    
    Several spots in the kernel perform a sequence like:
    
        skb_queue_tail(&sk->s_receive_queue, skb);
        sk->sk_data_ready(sk, skb->len);
    
    But at the moment we place the SKB onto the socket receive queue it
    can be consumed and freed up.  So this skb->len access is potentially
    to freed up memory.
    
    Furthermore, the skb->len can be modified by the consumer so it is
    possible that the value isn't accurate.
    
    And finally, no actual implementation of this callback actually uses
    the length argument.  And since nobody actually cared about it's
    value, lots of call sites pass arbitrary values in such as '0' and
    even '1'.
    
    So just remove the length argument from the callback, that way there
    is no confusion whatsoever and all of these use-after-free cases get
    fixed as a side effect.
    
    Based upon a patch by Eric Dumazet and his suggestion to audit this
    issue tree-wide.
    
    Signed-off-by: David S. Miller <davem@davemloft.net>
*/

@ sk_data_ready_assigned @
expression E;
identifier drv_data_ready;
@@

	E->sk_data_ready = drv_data_ready;

@ sk_data_ready_declared depends on sk_data_ready_assigned @
identifier sk;
identifier sk_data_ready_assigned.drv_data_ready;
fresh identifier backport_drv_data_ready = "backport_" ## drv_data_ready;
@@

drv_data_ready(struct sock *sk)
{
	...
}

+static void backport_drv_data_ready(struct sock *sk, int unused)
+{
+	drv_data_ready(sk);
+}

@ sk_data_ready_assigned_mod_e depends on sk_data_ready_assigned @
expression E;
identifier sk_data_ready_assigned.drv_data_ready;
fresh identifier backport_drv_data_ready = "backport_" ## drv_data_ready;
@@

+#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,15,0)
	E->sk_data_ready = drv_data_ready;
+#else
+	E->sk_data_ready = backport_drv_data_ready;
+#endif

@ sk_data_ready_found @
expression E;
struct sock *sk;
@@

	E->sk_data_ready(sk);

@ sk_data_ready_skips_skb_queue_tail_E depends on sk_data_ready_found @
expression E;
@@

+#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,15,0)
	E->sk_data_ready(E);
+#else
+	E->sk_data_ready(E, 0);
+#endif

@ sk_data_ready_uses_skb_queue_tail depends on sk_data_ready_found && !sk_data_ready_skips_skb_queue_tail_E @
struct sock *sk;
struct sk_buff *skb;
identifier sk_data_ready;
@@

	skb_queue_tail(&sk->sk_receive_queue, skb);
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,15,0)
	sk->sk_data_ready(sk);
+#else
+	sk->sk_data_ready(sk, skb->len);
+#endif

