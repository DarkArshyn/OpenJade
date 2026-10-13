#ifndef TEST_STDDEF_H
#define TEST_STDDEF_H
typedef unsigned __int64 size_t;
typedef __int64 ptrdiff_t;
#define NULL ((void*)0)
#define offsetof(s,m) ((size_t)&(((s*)0)->m))
#endif
