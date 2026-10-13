// Original OpenJade implementation of the classic LZO1X byte-stream grammar.
// Format research: https://docs.kernel.org/staging/lzo.html (Tarreau/Rodgman).
// No Ubisoft source or third-party decoder source is included here.
using System;
using System.IO;

namespace OpenJade {
    public static class Lzo1x {
        // The public block API intentionally caps allocations at the POP block size.
        public static byte[] Decode(byte[] input, int expectedLength) {
            if (input == null) throw new ArgumentNullException("input");
            if (expectedLength < 0 || expectedLength > 131072)
                throw new ArgumentOutOfRangeException("expectedLength");
            return new Decoder(input, expectedLength).Run();
        }

        private sealed class Decoder {
            private readonly byte[] source, output;
            private int ip, op, state;
            internal Decoder(byte[] input, int size) { source = input; output = new byte[size]; }
            private int Byte() {
                if (ip >= source.Length) throw new InvalidDataException("Truncated LZO1X instruction.");
                return source[ip++];
            }
            private int Word() { int low = Byte(); return low | (Byte() << 8); }
            private int Length(int field, int mask, int extra) {
                int n = field;
                if (n == 0) {
                    n = mask;
                    int b;
                    do {
                        b = Byte();
                        n = checked(n + (b == 0 ? 255 : b));
                        if (n > output.Length) throw new InvalidDataException("LZO1X length exceeds output limit.");
                    } while (b == 0);
                }
                return checked(n + extra);
            }
            private void Literals(int count) {
                if (count > source.Length - ip || count > output.Length - op)
                    throw new InvalidDataException("LZO1X literal range exceeds input or output.");
                Buffer.BlockCopy(source, ip, output, op, count);
                ip += count; op += count;
            }
            private void Match(int distance, int count) {
                if (distance <= 0 || distance > op)
                    throw new InvalidDataException("LZO1X back-reference precedes output.");
                if (count > output.Length - op)
                    throw new InvalidDataException("LZO1X match exceeds output limit.");
                // Forward byte copying is required for overlapping dictionary matches.
                for (int i = 0; i < count; ++i) { output[op] = output[op - distance]; ++op; }
            }
            internal byte[] Run() {
                int token = Byte();
                if (token > 17) {
                    int n = token - 17;
                    Literals(n); state = n < 4 ? n : 4;
                    token = Byte();
                }
                while (true) {
                    int count, distance, following;
                    if (token < 16) {
                        if (state == 0) {
                            Literals(Length(token, 15, 3)); state = 4;
                            token = Byte(); continue;
                        }
                        distance = (Byte() << 2) + (token >> 2) + (state == 4 ? 2049 : 1);
                        count = state == 4 ? 3 : 2;
                        following = token & 3;
                    } else if (token < 32) {
                        count = Length(token & 7, 7, 2);
                        int word = Word();
                        int displacement = ((token & 8) << 11) + (word >> 2);
                        if (displacement == 0) {
                            if (count != 3 || (word & 3) != 0)
                                throw new InvalidDataException("Noncanonical LZO1X end marker.");
                            if (ip != source.Length) throw new InvalidDataException("Bytes remain after LZO1X end marker.");
                            if (op != output.Length) throw new InvalidDataException("Decoded length differs from declared length.");
                            return output;
                        }
                        distance = 16384 + displacement;
                        following = word & 3;
                    } else if (token < 64) {
                        count = Length(token & 31, 31, 2);
                        int word = Word();
                        distance = (word >> 2) + 1; following = word & 3;
                    } else {
                        count = (token >> 5) + 1;
                        distance = (Byte() << 3) + ((token >> 2) & 7) + 1;
                        following = token & 3;
                    }
                    Match(distance, count);
                    Literals(following); state = following;
                    token = Byte();
                }
            }
        }
    }
}
