/* fzlzx.c - tiny helper for fm4livery: decode Forza/Xbox "method 21" (XMemCompress LZX) zip entries.
 * Strips the XMemCompress chunk headers and feeds the LZX payload to libmspack's lzxd (LGPL-2.1, https://github.com/kyz/libmspack).
 * Build:  gcc -shared -O2 -o fzlzx.dll fzlzx.c <libmspack>/mspack/lzxd.c -I<libmspack>/mspack   (see .github/workflows/build.yml)
 * int fz_lzx_decompress(const char *in, long in_len, char *out, long out_len, int window_bits)  -> 0 on success */
#include <stdlib.h>
#include <string.h>
#include "mspack.h"
#include "lzx.h"
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
typedef struct { unsigned char *buf; size_t len, pos; } mem;
static struct mspack_file *m_open(struct mspack_system *s, const char *f, int mode) { (void)s; (void)f; (void)mode; return NULL; }
static void m_close(struct mspack_file *f) { (void)f; }
static int m_read(struct mspack_file *f, void *b, int n) { mem *m = (mem *)f; size_t r = m->len - m->pos; if ((size_t)n < r) r = n; memcpy(b, m->buf + m->pos, r); m->pos += r; return (int)r; }
static int m_write(struct mspack_file *f, void *b, int n) { mem *m = (mem *)f; size_t r = m->len - m->pos; if ((size_t)n > r) return -1; memcpy(m->buf + m->pos, b, n); m->pos += n; return n; }
static int m_seek(struct mspack_file *f, off_t o, int w) { mem *m = (mem *)f; off_t p = w == 0 ? o : w == 1 ? (off_t)m->pos + o : (off_t)m->len + o; if (p < 0 || (size_t)p > m->len) return 1; m->pos = (size_t)p; return 0; }
static off_t m_tell(struct mspack_file *f) { return (off_t)((mem *)f)->pos; }
static void m_msg(struct mspack_file *f, const char *fmt, ...) { (void)f; (void)fmt; }
static void *m_alloc(struct mspack_system *s, size_t n) { (void)s; return malloc(n); }
static void m_free(void *p) { free(p); }
static void m_copy(void *a, void *b, size_t n) { memcpy(b, a, n); }
static struct mspack_system sys = { m_open, m_close, m_read, m_write, m_seek, m_tell, m_msg, m_alloc, m_free, m_copy, NULL };

EXPORT int fz_lzx_decompress(const char *in, long in_len, char *out, long out_len, int window_bits) {
    const unsigned char *p = (const unsigned char *)in; long o = 0; size_t n = 0;
    unsigned char *pay = (unsigned char *)malloc((size_t)in_len + 64);
    if (!pay) return 1;
    while (o + 1 < in_len) {                        /* chunk: FF uu uu cc cc  or  cc cc  (big endian compressed size) */
        long sz, hdr;
        if (p[o] == 0xFF) { if (o + 4 >= in_len) break; sz = (p[o + 3] << 8) | p[o + 4]; hdr = 5; }
        else { sz = (p[o] << 8) | p[o + 1]; hdr = 2; }
        if (sz == 0 || o + hdr + sz > in_len) break;
        memcpy(pay + n, p + o + hdr, sz); n += sz; o += hdr + sz;
    }
    mem src = { pay, n, 0 }, dst = { (unsigned char *)out, (size_t)out_len, 0 };
    struct lzxd_stream *s = lzxd_init(&sys, (struct mspack_file *)&src, (struct mspack_file *)&dst, window_bits, 0, 0x8000, (off_t)out_len, 0);
    int rc = 3;
    if (s) { rc = lzxd_decompress(s, (off_t)out_len); lzxd_free(s); }
    free(pay);
    return rc;
}
