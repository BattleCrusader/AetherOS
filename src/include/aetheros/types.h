/* Aether OS — Common Type Definitions */
#ifndef AETHEROS_TYPES_H
#define AETHEROS_TYPES_H

typedef unsigned char      u8;
typedef unsigned short     u16;
typedef unsigned int       u32;
typedef unsigned long long u64;

typedef signed char        i8;
typedef signed short       i16;
typedef signed int         i32;
typedef signed long long   i64;

typedef u8                 byte;
typedef u32                size_t;
typedef u32                ino_t;

#define NULL ((void*)0)

/* Memory map constants */
#define STAGE1_BASE     0x7C00
#define STAGE2_BASE     0x7E00
#define PAGE_TABLES     0x6000
#define MODULE_REGISTRY 0x4000
#define SYSCALL_PAGE    0x5000
#define KERNEL_BASE     0x1000000
#define BIN_BASE        0x2000000
#define MOD_SLOT_BASE   0x2100000
#define MOD_SLOT_SIZE   0x10000   /* 64KB per module slot */
#define MOD_SLOT_COUNT  8
#define MEM_START       0x11E6000
#define MEM_END         0x10000000
#define PAGE_SIZE       4096
#define BITMAP_ADDR     0xD000

/* Syscall indices */
#define SYS_PUTC    0
#define SYS_PUTS    1
#define SYS_OPEN    2
#define SYS_READ    3
#define SYS_READDIR 4
#define SYS_GETCWD  5
#define SYS_CHDIR   6
#define SYS_EXIT    7
#define SYS_BOOLEVAL 8

/* Module registry slots */
#define REG_CMD      0
#define REG_HOOK     1
#define FIND_CMD     2
#define FIND_HOOK    3
#define UNREG_CMD    4

/* Hook IDs */
#define HOOK_BOOL_EVAL 1

/* ELF constants */
#define ELF_MAGIC      0x464C457F  /* "\x7fELF" little-endian */
#define ELF_CLASS_64   2
#define ELF_DATA_2LSB  1
#define EM_X86_64      62
#define PT_LOAD        1

/* COM1 port addresses */
#define COM1           0x3F8
#define COM1_DATA      0x3F8
#define COM1_IER       0x3F9
#define COM1_LCR       0x3FB
#define COM1_LSR       0x3FD
#define LSR_THR_EMPTY  0x20
#define LSR_DATA_READY 0x01

/* Boot FS inode numbers */
#define INODE_ROOT     1
#define INODE_BIN      2
#define INODE_ETC      3
#define INODE_LIB      4
#define INODE_TMP      5
#define INODE_DEV      6
#define INODE_LIB_AVAIL 7
#define INODE_LIB_ENABLED 8

#endif /* AETHEROS_TYPES_H */
