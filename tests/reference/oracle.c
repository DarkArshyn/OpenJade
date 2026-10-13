/* Local test bridge to official miniLZO; not a runtime dependency. */
#include "minilzo.h"
static lzo_align_t workspace[(LZO1X_1_MEM_COMPRESS + sizeof(lzo_align_t) - 1) / sizeof(lzo_align_t)];
__declspec(dllexport) int oracle_decode(const unsigned char *src, int length,
                                        unsigned char *dst, int capacity) {
    lzo_uint n = capacity;
    int rc;
    if (lzo_init() != LZO_E_OK) return -100;
    rc = lzo1x_decompress_safe(src, length, dst, &n, NULL);
    return rc == LZO_E_OK ? (int)n : rc;
}
__declspec(dllexport) int oracle_compress(const unsigned char *src, int length,
                                          unsigned char *dst, int capacity) {
    lzo_uint n = capacity;
    void *work;
    int rc;
    if (capacity < length + length/16 + 64 + 3) return -101;
    if (lzo_init() != LZO_E_OK) return -100;
    work = workspace;
    if (!work) return -102;
    rc = lzo1x_1_compress(src, length, dst, &n, work);

    return rc == LZO_E_OK ? (int)n : rc;
}

