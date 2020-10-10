/*
 * Copyright (c) 1991, 1993
 *  The Regents of the University of California.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 4. Neither the name of the University nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 *
 *  @(#)queue.h 8.5 (Berkeley) 8/20/94
 * $FreeBSD: src/sys/sys/queue.h,v 1.58 2004/04/07 04:19:49 imp Exp $
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/magpie_fw_dev/asf/include/asf_queue.h#1 $
 */

#ifndef _ASF_QUEUE_H_
#define _ASF_QUEUE_H_

/**
 * General purpose routines
 */
#define asf_offsetof(type, member) ((adf_os_size_t) &((type *)0)->member)

#define asf_containerof(ptr, type, member) ({           \
        const typeof( ((type *)0)->member ) *__lptr = (ptr);    \
        (type *)( (char *)__mptr - asf_offsetof(type,member) );})

/*
 * This file defines four types of data structures: singly-linked lists,
 * singly-linked tail queues, lists and tail queues.
 *
 * A singly-linked list is headed by a single forward pointer. The elements
 * are singly linked for minimum space and pointer manipulation overhead at
 * the expense of O(n) removal for arbitrary elements. New elements can be
 * added to the list after an existing element or at the head of the list.
 * Elements being removed from the head of the list should use the explicit
 * macro for this purpose for optimum efficiency. A singly-linked list may
 * only be traversed in the forward direction.  Singly-linked lists are ideal
 * for applications with large datasets and few or no removals or for
 * implementing a LIFO queue.
 *
 * A singly-linked tail queue is headed by a pair of pointers, one to the
 * head of the list and the other to the tail of the list. The elements are
 * singly linked for minimum space and pointer manipulation overhead at the
 * expense of O(n) removal for arbitrary elements. New elements can be added
 * to the list after an existing element, at the head of the list, or at the
 * end of the list. Elements being removed from the head of the tail queue
 * should use the explicit macro for this purpose for optimum efficiency.
 * A singly-linked tail queue may only be traversed in the forward direction.
 * Singly-linked tail queues are ideal for applications with large datasets
 * and few or no removals or for implementing a FIFO queue.
 *
 * A list is headed by a single forward pointer (or an array of forward
 * pointers for a hash table header). The elements are doubly linked
 * so that an arbitrary element can be removed without a need to
 * traverse the list. New elements can be added to the list before
 * or after an existing element or at the head of the list. A list
 * may only be traversed in the forward direction.
 *
 * A tail queue is headed by a pair of pointers, one to the head of the
 * list and the other to the tail of the list. The elements are doubly
 * linked so that an arbitrary element can be removed without a need to
 * traverse the list. New elements can be added to the list before or
 * after an existing element, at the head of the list, or at the end of
 * the list. A tail queue may be traversed in either direction.
 *
 * For details on the use of these macros, see the queue(3) manual page.
 *
 *
 *              asf_slist   asf_list    asf_stailq  asf_tailq
 * _head            +   +   +   +
 * _head_initializer        +   +   +   +
 * _entry           +   +   +   +
 * _init            +   +   +   +
 * _empty           +   +   +   +
 * _first           +   +   +   +
 * _next            +   +   +   +
 * _prev            -   -   -   +
 * _last            -   -   +   +
 * _foreach         +   +   +   +
 * _foreach_safe        +   +   +   +
 * _foreach_reverse     -   -   -   +
 * _foreach_reverse_safe    -   -   -   +
 * _insert_head         +   +   +   +
 * _insert_before       -   +   -   +
 * _insert_after        +   +   +   +
 * _insert_tail         -   -   +   +
 * _concat          -   -   +   +
 * _remove_head         +   -   +   -
 * _remove          +   +   +   +
 *
 */
#define QUEUE_MACRO_DEBUG 0
#if QUEUE_MACRO_DEBUG
/* Store the last 2 places the queue element or head was altered */
struct asf_qm_trace {
    char * lastfile;
    int lastline;
    char * prevfile;
    int prevline;
};

#define TRACEBUF    struct asf_qm_trace trace
#define trashit(x)  do {(x) = (void *)-1;} while (0)

#define qmd_trace_head(head) do {                   \
    (head)->trace.prevline = (head)->trace.lastline;        \
    (head)->trace.prevfile = (head)->trace.lastfile;        \
    (head)->trace.lastline = __LINE__;              \
    (head)->trace.lastfile = __FILE__;              \
} while (0)

#define qmd_trace_elem(elem) do {                   \
    (elem)->trace.prevline = (elem)->trace.lastline;        \
    (elem)->trace.prevfile = (elem)->trace.lastfile;        \
    (elem)->trace.lastline = __LINE__;              \
    (elem)->trace.lastfile = __FILE__;              \
} while (0)

#else
#define qmd_trace_elem(elem)
#define qmd_trace_head(head)
#define TRACEBUF
#define trashit(x)
#endif  /* QUEUE_MACRO_DEBUG */

/*
 * Singly-linked List declarations.
 */
#define asf_slist_head(name, type)                      \
struct name {                               \
    struct type *slh_first; /* first element */         \
}

#define asf_slist_head_initializer(head)                    \
    { NULL }

#define asf_slist_entry(type)                       \
struct {                                \
    struct type *sle_next;  /* next element */          \
}

/*
 * Singly-linked List functions.
 */
#define asf_slist_empty(head)   ((head)->slh_first == NULL)

#define asf_slist_first(head)   ((head)->slh_first)

#define asf_slist_foreach(var, head, field)                 \
    for ((var) = asf_slist_first((head));               \
        (var);                          \
        (var) = asf_slist_next((var), field))

#define asf_slist_foreach_safe(var, head, field, tvar)          \
    for ((var) = asf_slist_first((head));               \
        (var) && ((tvar) = asf_slist_next((var), field), 1);        \
        (var) = (tvar))

#define asf_slist_foreach_prevptr(var, varp, head, field)           \
    for ((varp) = &asf_slist_first((head));             \
        ((var) = *(varp)) != NULL;                  \
        (varp) = &asf_slist_next((var), field))

#define asf_slist_init(head) do {                       \
    asf_slist_first((head)) = NULL;                 \
} while (0)

#define asf_slist_insert_after(slistelm, elm, field) do {           \
    asf_slist_next((elm), field) = asf_slist_next((slistelm), field);   \
    asf_slist_next((slistelm), field) = (elm);              \
} while (0)

#define asf_slist_insert_head(head, elm, field) do {            \
    asf_slist_next((elm), field) = asf_slist_first((head));         \
    asf_slist_first((head)) = (elm);                    \
} while (0)

#define asf_slist_next(elm, field)  ((elm)->field.sle_next)

#define asf_slist_remove(head, elm, type, field) do {           \
    if (asf_slist_first((head)) == (elm)) {             \
        asf_slist_remove_head((head), field);           \
    }                               \
    else {                              \
        struct type *curelm = asf_slist_first((head));      \
        while (asf_slist_next(curelm, field) != (elm))      \
            curelm = asf_slist_next(curelm, field);     \
        asf_slist_next(curelm, field) =             \
            asf_slist_next(asf_slist_next(curelm, field), field);   \
    }                               \
} while (0)

#define asf_slist_remove_head(head, field) do {             \
    asf_slist_first((head)) = asf_slist_next(asf_slist_first((head)), field);   \
} while (0)

/*
 * Singly-linked Tail queue declarations.
 */
#define asf_stailq_head(name, type)                     \
struct name {                               \
    struct type *stqh_first;/* first element */         \
    struct type **stqh_last;/* addr of last next element */     \
}

#define asf_stailq_head_initializer(head)                   \
    { NULL, &(head).stqh_first }

#define asf_stailq_entry(type)                      \
struct {                                \
    struct type *stqe_next; /* next element */          \
}

/*
 * Singly-linked Tail queue functions.
 */
#define asf_stailq_concat(head1, head2) do {                \
    if (!asf_stailq_empty((head2))) {                   \
        *(head1)->stqh_last = (head2)->stqh_first;      \
        (head1)->stqh_last = (head2)->stqh_last;        \
        asf_stailq_init((head2));                   \
    }                               \
} while (0)

#define asf_stailq_empty(head)  ((head)->stqh_first == NULL)

#define asf_stailq_first(head)  ((head)->stqh_first)

#define asf_stailq_foreach(var, head, field)                \
    for((var) = asf_stailq_first((head));               \
       (var);                           \
       (var) = asf_stailq_next((var), field))


#define asf_stailq_foreach_safe(var, head, field, tvar)         \
    for ((var) = asf_stailq_first((head));              \
        (var) && ((tvar) = asf_stailq_next((var), field), 1);       \
        (var) = (tvar))

#define asf_stailq_init(head) do {                      \
    asf_stailq_first((head)) = NULL;                    \
    (head)->stqh_last = &asf_stailq_first((head));          \
} while (0)

#define asf_stailq_insert_after(head, tqelm, elm, field) do {       \
    if ((asf_stailq_next((elm), field) = asf_stailq_next((tqelm), field)) == NULL)\
        (head)->stqh_last = &asf_stailq_next((elm), field);     \
    asf_stailq_next((tqelm), field) = (elm);                \
} while (0)

#define asf_stailq_insert_head(head, elm, field) do {           \
    if ((asf_stailq_next((elm), field) = asf_stailq_first((head))) == NULL) \
        (head)->stqh_last = &asf_stailq_next((elm), field);     \
    asf_stailq_first((head)) = (elm);                   \
} while (0)

#define asf_stailq_insert_tail(head, elm, field) do {           \
    asf_stailq_next((elm), field) = NULL;               \
    *(head)->stqh_last = (elm);                 \
    (head)->stqh_last = &asf_stailq_next((elm), field);         \
} while (0)

#define asf_stailq_last(head, type, field)                  \
    (asf_stailq_empty((head)) ?                     \
        NULL :                          \
            ((struct type *)                    \
        ((char *)((head)->stqh_last) - __offsetof(struct type, field))))

#define asf_stailq_next(elm, field) ((elm)->field.stqe_next)

#define asf_stailq_remove(head, elm, type, field) do {          \
    if (asf_stailq_first((head)) == (elm)) {                \
        asf_stailq_remove_head((head), field);          \
    }                               \
    else {                              \
        struct type *curelm = asf_stailq_first((head));     \
        while (asf_stailq_next(curelm, field) != (elm))     \
            curelm = asf_stailq_next(curelm, field);        \
        if ((asf_stailq_next(curelm, field) =           \
             asf_stailq_next(asf_stailq_next(curelm, field), field)) == NULL)\
            (head)->stqh_last = &asf_stailq_next((curelm), field);\
    }                               \
} while (0)


#define asf_stailq_remove_after(head, elm, field) do {          \
    if (asf_stailq_next(elm, field)) {      \
        if ((asf_stailq_next(elm, field) =          \
            asf_stailq_next(asf_stailq_next(elm, field), field)) == NULL)\
            (head)->stqh_last = &asf_stailq_next((elm), field); \
    }                               \
} while (0)


#define asf_stailq_remove_head(head, field) do {                \
    if ((asf_stailq_first((head)) =                 \
         asf_stailq_next(asf_stailq_first((head)), field)) == NULL)     \
        (head)->stqh_last = &asf_stailq_first((head));      \
} while (0)

#define asf_stailq_remove_head_until(head, elm, field) do {         \
    if ((asf_stailq_first((head)) = asf_stailq_next((elm), field)) == NULL) \
        (head)->stqh_last = &asf_stailq_first((head));      \
} while (0)

/*
 * List declarations.
 */
#define asf_list_head(name, type)                   \
struct name {                               \
    struct type *lh_first;  /* first element */         \
}

#define asf_list_head_initializer(head)                 \
    { NULL }

#define asf_list_entry(type)                        \
struct {                                \
    struct type *le_next;   /* next element */          \
    struct type **le_prev;  /* address of previous next element */  \
}

/*
 * List functions.
 */

#define asf_list_empty(head)    ((head)->lh_first == NULL)

#define asf_list_first(head)    ((head)->lh_first)

#define asf_list_foreach(var, head, field)                  \
    for ((var) = asf_list_first((head));                \
        (var);                          \
        (var) = asf_list_next((var), field))

#define asf_list_foreach_safe(var, head, field, tvar)           \
    for ((var) = asf_list_first((head));                \
        (var) && ((tvar) = asf_list_next((var), field), 1);     \
        (var) = (tvar))

#define asf_list_init(head) do {                        \
    asf_list_first((head)) = NULL;                  \
} while (0)

#define asf_list_insert_after(listelm, elm, field) do {         \
    if ((asf_list_next((elm), field) = asf_list_next((listelm), field)) != NULL)\
        asf_list_next((listelm), field)->field.le_prev =        \
            &asf_list_next((elm), field);               \
    asf_list_next((listelm), field) = (elm);                \
    (elm)->field.le_prev = &asf_list_next((listelm), field);        \
} while (0)

#define asf_list_insert_before(listelm, elm, field) do {            \
    (elm)->field.le_prev = (listelm)->field.le_prev;        \
    asf_list_next((elm), field) = (listelm);                \
    *(listelm)->field.le_prev = (elm);              \
    (listelm)->field.le_prev = &asf_list_next((elm), field);        \
} while (0)

#define asf_list_insert_head(head, elm, field) do {             \
    if ((asf_list_next((elm), field) = asf_list_first((head))) != NULL) \
        asf_list_first((head))->field.le_prev = &asf_list_next((elm), field);\
    asf_list_first((head)) = (elm);                 \
    (elm)->field.le_prev = &asf_list_first((head));         \
} while (0)

#define asf_list_next(elm, field)   ((elm)->field.le_next)

#define asf_list_remove(elm, field) do {                    \
    if (asf_list_next((elm), field) != NULL)                \
        asf_list_next((elm), field)->field.le_prev =        \
            (elm)->field.le_prev;               \
    *(elm)->field.le_prev = asf_list_next((elm), field);        \
} while (0)

/*
 * Tail queue declarations.
 */
#define asf_tailq_head(name, type)                      \
struct name {                               \
    struct type *tqh_first; /* first element */         \
    struct type **tqh_last; /* addr of last next element */     \
    TRACEBUF;                           \
}

#define asf_tailq_head_initializer(head)                    \
    { NULL, &(head).tqh_first }

#define asf_tailq_entry(type)                       \
struct {                                \
    struct type *tqe_next;  /* next element */          \
    struct type **tqe_prev; /* address of previous next element */  \
    TRACEBUF;                           \
}

/*
 * Tail queue functions.
 */
#define asf_tailq_concat(head1, head2, field) do {              \
    if (!asf_tailq_empty(head2)) {                  \
        *(head1)->tqh_last = (head2)->tqh_first;        \
        (head2)->tqh_first->field.tqe_prev = (head1)->tqh_last; \
        (head1)->tqh_last = (head2)->tqh_last;          \
        asf_tailq_init((head2));                    \
        qmd_trace_head(head);                   \
        qmd_trace_head(head2);                  \
    }                               \
} while (0)

#define asf_tailq_empty(head)   ((head)->tqh_first == NULL)

#define asf_tailq_first(head)   ((head)->tqh_first)

#define asf_tailq_foreach(var, head, field)                 \
    for ((var) = asf_tailq_first((head));               \
        (var);                          \
        (var) = asf_tailq_next((var), field))

#define asf_tailq_foreach_safe(var, head, field, tvar)          \
    for ((var) = asf_tailq_first((head));               \
        (var) && ((tvar) = asf_tailq_next((var), field), 1);        \
        (var) = (tvar))

#define asf_tailq_foreach_reverse(var, head, headname, field)       \
    for ((var) = asf_tailq_last((head), headname);          \
        (var);                          \
        (var) = asf_tailq_prev((var), headname, field))

#define asf_tailq_foreach_reverse_safe(var, head, headname, field, tvar)    \
    for ((var) = asf_tailq_last((head), headname);          \
        (var) && ((tvar) = asf_tailq_prev((var), headname, field), 1);  \
        (var) = (tvar))

#define asf_tailq_init(head) do {                       \
    asf_tailq_first((head)) = NULL;                 \
    (head)->tqh_last = &asf_tailq_first((head));            \
    qmd_trace_head(head);                       \
} while (0)

#define asf_tailq_insert_after(head, listelm, elm, field) do {      \
    if ((asf_tailq_next((elm), field) = asf_tailq_next((listelm), field)) != NULL)\
        asf_tailq_next((elm), field)->field.tqe_prev =      \
            &asf_tailq_next((elm), field);              \
    else {                              \
        (head)->tqh_last = &asf_tailq_next((elm), field);       \
        qmd_trace_head(head);                   \
    }                               \
    asf_tailq_next((listelm), field) = (elm);               \
    (elm)->field.tqe_prev = &asf_tailq_next((listelm), field);      \
    qmd_trace_elem(&(elm)->field);                  \
    qmd_trace_elem(&listelm->field);                \
} while (0)

#define asf_tailq_insert_before(listelm, elm, field) do {           \
    (elm)->field.tqe_prev = (listelm)->field.tqe_prev;      \
    asf_tailq_next((elm), field) = (listelm);               \
    *(listelm)->field.tqe_prev = (elm);             \
    (listelm)->field.tqe_prev = &asf_tailq_next((elm), field);      \
    qmd_trace_elem(&(elm)->field);                  \
    qmd_trace_elem(&listelm->field);                \
} while (0)

#define asf_tailq_insert_head(head, elm, field) do {            \
    if ((asf_tailq_next((elm), field) = asf_tailq_first((head))) != NULL)   \
        asf_tailq_first((head))->field.tqe_prev =           \
            &asf_tailq_next((elm), field);              \
    else                                \
        (head)->tqh_last = &asf_tailq_next((elm), field);       \
    asf_tailq_first((head)) = (elm);                    \
    (elm)->field.tqe_prev = &asf_tailq_first((head));           \
    qmd_trace_head(head);                       \
    qmd_trace_elem(&(elm)->field);                  \
} while (0)

#define asf_tailq_insert_tail(head, elm, field) do {            \
    asf_tailq_next((elm), field) = NULL;                \
    (elm)->field.tqe_prev = (head)->tqh_last;           \
    *(head)->tqh_last = (elm);                  \
    (head)->tqh_last = &asf_tailq_next((elm), field);           \
    qmd_trace_head(head);                       \
    qmd_trace_elem(&(elm)->field);                  \
} while (0)

#define asf_tailq_last(head, headname)                  \
    (*(((struct headname *)((head)->tqh_last))->tqh_last))

#define asf_tailq_next(elm, field) ((elm)->field.tqe_next)

#define asf_tailq_prev(elm, headname, field)                \
    (*(((struct headname *)((elm)->field.tqe_prev))->tqh_last))

#define asf_tailq_remove(head, elm, field) do {             \
    if ((asf_tailq_next((elm), field)) != NULL)             \
        asf_tailq_next((elm), field)->field.tqe_prev =      \
            (elm)->field.tqe_prev;              \
    else {                              \
        (head)->tqh_last = (elm)->field.tqe_prev;       \
        qmd_trace_head(head);                   \
    }                               \
    *(elm)->field.tqe_prev = asf_tailq_next((elm), field);      \
    trashit((elm)->field.tqe_next);                 \
    trashit((elm)->field.tqe_prev);                 \
    qmd_trace_elem(&(elm)->field);                  \
} while (0)


#ifdef _KERNEL

/*
 * XXX asf_insque() and remque() are an old way of handling certain queues.
 * They bogusly assumes that all queue heads look alike.
 */

struct asf_qhead {
    struct asf_qhead *qh_link;
    struct asf_qhead *qh_rlink;
};

#if defined(__GNUC__) || defined(__INTEL_COMPILER)

static __inline void
asf_insque(void *a, void *b)
{
    struct asf_qhead *element = (struct asf_qhead *)a,
         *head = (struct asf_qhead *)b;

    element->qh_link = head->qh_link;
    element->qh_rlink = head;
    head->qh_link = element;
    element->qh_link->qh_rlink = element;
}

static __inline void
asf_remque(void *a)
{
    struct asf_qhead *element = (struct asf_qhead *)a;

    element->qh_link->qh_rlink = element->qh_rlink;
    element->qh_rlink->qh_link = element->qh_link;
    element->qh_rlink = 0;
}

#else /* !(__GNUC__ || __INTEL_COMPILER) */

void    asf_insque(void *a, void *b);
void    asf_remque(void *a);

#endif /* __GNUC__ || __INTEL_COMPILER */

#endif /* _KERNEL */

#endif /* !_ASF_QUEUE_H_ */
