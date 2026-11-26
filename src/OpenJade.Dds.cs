// Original OpenJade reader for single-surface, single-level legacy DDS BC1/BC3.
// Format references: Microsoft DDS_HEADER, DDS_PIXELFORMAT and Block Compression.
using System;
using System.IO;
using System.IO.Compression;
using System.Text;

namespace OpenJade {
    public sealed class DdsImage {
        public int Width, Height;
        public string Format;
        public uint HeaderFlags, PixelFormatFlags, RawRgbBitCount, LinearSize, RawMipCount;
        public byte[] Rgba;
    }
    public static class Dds {
        private static uint U32(byte[] b, int p) { return BitConverter.ToUInt32(b,p); }
        private static void Color(int word, int[,] colors, int i) {
            int r=(word>>11)&31, g=(word>>5)&63, blue=word&31;
            colors[i,0]=(r<<3)|(r>>2); colors[i,1]=(g<<2)|(g>>4); colors[i,2]=(blue<<3)|(blue>>2);
            colors[i,3]=255;
        }
        public static DdsImage Decode(byte[] bytes) {
            if(bytes==null || bytes.Length<128) throw new InvalidDataException("Truncated DDS header.");
            if(U32(bytes,0)!=0x20534444 || U32(bytes,4)!=124 || U32(bytes,76)!=32)
                throw new InvalidDataException("Invalid DDS signature or header size.");
            uint w=U32(bytes,16), h=U32(bytes,12), cc=U32(bytes,84);
            if(w==0 || h==0 || w>8192 || h>8192 || (long)w*h>16777216)
                throw new InvalidDataException("DDS dimensions exceed the 16-megapixel limit.");
            if(U32(bytes,24)!=0 || U32(bytes,112)!=0 || U32(bytes,28)>1)
                throw new InvalidDataException("Only single-level 2D surfaces are supported.");
            if((U32(bytes,80)&4)==0 || (cc!=0x31545844 && cc!=0x35545844))
                throw new InvalidDataException("Only legacy DXT1 and DXT5 are supported.");
            bool bc3=cc==0x35545844;
            int width=(int)w, height=(int)h, blockSize=bc3?16:8;
            int columns=(width+3)/4, rows=(height+3)/4;
            int expected=checked(128+columns*rows*blockSize);
            if(bytes.Length!=expected) throw new InvalidDataException("DDS data length differs from the supported surface size.");
            DdsImage image=new DdsImage {Width=width, Height=height, Format=bc3?"DXT5/BC3":"DXT1/BC1",
                HeaderFlags=U32(bytes,8), PixelFormatFlags=U32(bytes,80), RawRgbBitCount=U32(bytes,88),
                LinearSize=U32(bytes,20), RawMipCount=U32(bytes,28), Rgba=new byte[checked(width*height*4)]};
            int[,] palette=new int[4,4]; int[] alpha=new int[8];
            for(int by=0;by<rows;by++) for(int bx=0;bx<columns;bx++) {
                int offset=128+(by*columns+bx)*blockSize, c=offset+(bc3?8:0);
                int c0=BitConverter.ToUInt16(bytes,c), c1=BitConverter.ToUInt16(bytes,c+2);
                Color(c0,palette,0); Color(c1,palette,1);
                bool four=bc3 || c0>c1;
                for(int channel=0;channel<3;channel++) {
                    palette[2,channel]=four?(2*palette[0,channel]+palette[1,channel])/3:(palette[0,channel]+palette[1,channel])/2;
                    palette[3,channel]=four?(palette[0,channel]+2*palette[1,channel])/3:0;
                }
                palette[2,3]=255; palette[3,3]=four?255:0;
                ulong alphaBits=0;
                if(bc3) {
                    alpha[0]=bytes[offset]; alpha[1]=bytes[offset+1];
                    if(alpha[0]>alpha[1]) {
                        for(int i=2;i<8;i++) alpha[i]=((8-i)*alpha[0]+(i-1)*alpha[1])/7;
                    } else {
                        for(int i=2;i<6;i++) alpha[i]=((6-i)*alpha[0]+(i-1)*alpha[1])/5;
                        alpha[6]=0; alpha[7]=255;
                    }
                    for(int i=0;i<6;i++) alphaBits|=(ulong)bytes[offset+2+i]<<(8*i);
                }
                uint indices=U32(bytes,c+4);
                for(int py=0;py<4;py++) for(int px=0;px<4;px++) {
                    int x=bx*4+px, y=by*4+py, pixel=py*4+px;
                    if(x>=width || y>=height) continue;
                    int index=(int)((indices>>(2*pixel))&3), target=(y*width+x)*4;
                    for(int ch=0;ch<3;ch++) image.Rgba[target+ch]=(byte)palette[index,ch];
                    image.Rgba[target+3]=(byte)(bc3?alpha[(int)((alphaBits>>(3*pixel))&7)]:palette[index,3]);
                }
            }
            return image;
        }
        private static void WriteUInt32BE(Stream stream, uint value) {
            stream.WriteByte((byte)(value >> 24));
            stream.WriteByte((byte)(value >> 16));
            stream.WriteByte((byte)(value >> 8));
            stream.WriteByte((byte)value);
        }
        private static uint UpdateCrc32(uint crc, byte[] data) {
            foreach(byte value in data) {
                crc ^= value;
                for(int bit=0;bit<8;bit++) {
                    crc=(crc&1)!=0
                        ? (crc>>1)^0xEDB88320u
                        : crc>>1;
                }
            }
            return crc;
        }
        private static void WritePngChunk(
            Stream stream, string type, byte[] data) {

            byte[] name=Encoding.ASCII.GetBytes(type);

            WriteUInt32BE(stream,(uint)data.Length);
            stream.Write(name,0,name.Length);
            stream.Write(data,0,data.Length);

            uint crc=UpdateCrc32(0xFFFFFFFFu,name);
            crc=UpdateCrc32(crc,data)^0xFFFFFFFFu;

            WriteUInt32BE(stream,crc);
        }
        public static void SavePng(
            DdsImage image, string path, bool checkerboard) {

            byte[] compressed;

            using(MemoryStream buffer=new MemoryStream()) {
                using(ZLibStream zlib=new ZLibStream(
                    buffer,CompressionLevel.Optimal,true)) {

                    // PNG filter type 0 followed by RGBA pixels.
                    byte[] row=new byte[checked(1+image.Width*4)];

                    for(int y=0;y<image.Height;y++) {
                        row[0]=0;

                        for(int x=0;x<image.Width;x++) {
                            int source=(y*image.Width+x)*4;
                            int dest=1+x*4;
                            int a=image.Rgba[source+3];

                            int background=
                                ((x/16+y/16)%2==0)?48:72;

                            for(int ch=0;ch<3;ch++) {
                                int value=image.Rgba[source+ch];

                                row[dest+ch]=(byte)(checkerboard
                                    ? (value*a+background*(255-a)+127)/255
                                    : value);
                            }

                            row[dest+3]=(byte)(checkerboard?255:a);
                        }

                        zlib.Write(row,0,row.Length);
                    }
                }

                compressed=buffer.ToArray();
            }

            using(FileStream output=new FileStream(
                path,FileMode.CreateNew,
                FileAccess.Write,FileShare.None)) {

                // Standard PNG signature.
                byte[] signature={
                    137,80,78,71,13,10,26,10
                };

                output.Write(signature,0,signature.Length);

                using(MemoryStream header=new MemoryStream()) {
                    WriteUInt32BE(header,(uint)image.Width);
                    WriteUInt32BE(header,(uint)image.Height);

                    header.WriteByte(8); // Bit depth.
                    header.WriteByte(6); // RGBA color type.
                    header.WriteByte(0); // Compression method.
                    header.WriteByte(0); // Filter method.
                    header.WriteByte(0); // No interlacing.

                    WritePngChunk(output,"IHDR",header.ToArray());
                }

                WritePngChunk(output,"IDAT",compressed);
                WritePngChunk(output,"IEND",Array.Empty<byte>());
            }
        }
    }
}
