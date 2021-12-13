/*
#
#    Copyright 2008-2011 Lukas Lueg, lukas.lueg@gmail.com
#
#    This file is part of Pyrit.
#
#    Pyrit is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Pyrit is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pyrit.  If not, see <http://www.gnu.org/licenses/>.
#
#    Additional permission under GNU GPL version 3 section 7
#
#    If you modify this Program, or any covered work, by linking or
#    combining it with any library or libraries implementing the
#    Khronos Group OpenCL Standard v1.0 or later (or modified
#    versions of those libraries), containing parts covered by the
#    terms of the licenses of their respective copyright owners,
#    the licensors of this Program grant you additional permission
#    to convey the resulting work.
*/

void sha1_process(__private const SHA_DEV_CTX ctx, __private SHA_DEV_CTX *data)
{

  uint32_t temp, W[16], A, B, C, D, E;

  W[ 0] = data->h0; W[ 1] = data->h1;
  W[ 2] = data->h2; W[ 3] = data->h3;
  W[ 4] = data->h4; W[ 5] = 0x80000000;
  W[ 6] = 0; W[ 7] = 0;
  W[ 8] = 0; W[ 9] = 0;
  W[10] = 0; W[11] = 0;
  W[12] = 0; W[13] = 0;
  W[14] = 0; W[15] = (64+20)*8;

  A = ctx.h0;
  B = ctx.h1;
  C = ctx.h2;
  D = ctx.h3;
  E = ctx.h4;

#undef R
#define R(t)                                              \
(                                                         \
    temp = W[(t -  3) & 0x0F] ^ W[(t - 8) & 0x0F] ^       \
           W[(t - 14) & 0x0F] ^ W[ t      & 0x0F],        \
    ( W[t & 0x0F] = rotate((int)temp,1) )                 \
)

#undef P
#define P(a,b,c,d,e,x)                                    \
{                                                         \
    e += rotate((int)a,5) + F(b,c,d) + K + x; b = rotate((int)b,30);\
}

#define F(x,y,z) (z ^ (x & (y ^ z)))
#define K 0x5A827999
  
  P( A, B, C, D, E, W[0]  );
  P( E, A, B, C, D, W[1]  );
  P( D, E, A, B, C, W[2]  );
  P( C, D, E, A, B, W[3]  );
  P( B, C, D, E, A, W[4]  );
  P( A, B, C, D, E, W[5]  );
  P( E, A, B, C, D, W[6]  );
  P( D, E, A, B, C, W[7]  );
  P( C, D, E, A, B, W[8]  );
  P( B, C, D, E, A, W[9]  );
  P( A, B, C, D, E, W[10] );
  P( E, A, B, C, D, W[11] );
  P( D, E, A, B, C, W[12] );
  P( C, D, E, A, B, W[13] );
  P( B, C, D, E, A, W[14] );
  P( A, B, C, D, E, W[15] );
  P( E, A, B, C, D, R(16) );
  P( D, E, A, B, C, R(17) );
  P( C, D, E, A, B, R(18) );
  P( B, C, D, E, A, R(19) );

#undef K
#undef F

#define F(x,y,z) (x ^ y ^ z)
#define K 0x6ED9EBA1
  
  P( A, B, C, D, E, R(20) );
  P( E, A, B, C, D, R(21) );
  P( D, E, A, B, C, R(22) );
  P( C, D, E, A, B, R(23) );
  P( B, C, D, E, A, R(24) );
  P( A, B, C, D, E, R(25) );
  P( E, A, B, C, D, R(26) );
  P( D, E, A, B, C, R(27) );
  P( C, D, E, A, B, R(28) );
  P( B, C, D, E, A, R(29) );
  P( A, B, C, D, E, R(30) );
  P( E, A, B, C, D, R(31) );
  P( D, E, A, B, C, R(32) );
  P( C, D, E, A, B, R(33) );
  P( B, C, D, E, A, R(34) );
  P( A, B, C, D, E, R(35) );
  P( E, A, B, C, D, R(36) );
  P( D, E, A, B, C, R(37) );
  P( C, D, E, A, B, R(38) );
  P( B, C, D, E, A, R(39) );
  
#undef K
#undef F
  
#define F(x,y,z) ((x & y) | (z & (x | y)))
#define K 0x8F1BBCDC
  
  P( A, B, C, D, E, R(40) );
  P( E, A, B, C, D, R(41) );
  P( D, E, A, B, C, R(42) );
  P( C, D, E, A, B, R(43) );
  P( B, C, D, E, A, R(44) );
  P( A, B, C, D, E, R(45) );
  P( E, A, B, C, D, R(46) );
  P( D, E, A, B, C, R(47) );
  P( C, D, E, A, B, R(48) );
  P( B, C, D, E, A, R(49) );
  P( A, B, C, D, E, R(50) );
  P( E, A, B, C, D, R(51) );
  P( D, E, A, B, C, R(52) );
  P( C, D, E, A, B, R(53) );
  P( B, C, D, E, A, R(54) );
  P( A, B, C, D, E, R(55) );
  P( E, A, B, C, D, R(56) );
  P( D, E, A, B, C, R(57) );
  P( C, D, E, A, B, R(58) );
  P( B, C, D, E, A, R(59) );
  
#undef K
#undef F

#define F(x,y,z) (x ^ y ^ z)
#define K 0xCA62C1D6
  
  P( A, B, C, D, E, R(60) );
  P( E, A, B, C, D, R(61) );
  P( D, E, A, B, C, R(62) );
  P( C, D, E, A, B, R(63) );
  P( B, C, D, E, A, R(64) );
  P( A, B, C, D, E, R(65) );
  P( E, A, B, C, D, R(66) );
  P( D, E, A, B, C, R(67) );
  P( C, D, E, A, B, R(68) );
  P( B, C, D, E, A, R(69) );
  P( A, B, C, D, E, R(70) );
  P( E, A, B, C, D, R(71) );
  P( D, E, A, B, C, R(72) );
  P( C, D, E, A, B, R(73) );
  P( B, C, D, E, A, R(74) );
  P( A, B, C, D, E, R(75) );
  P( E, A, B, C, D, R(76) );
  P( D, E, A, B, C, R(77) );
  P( C, D, E, A, B, R(78) );
  P( B, C, D, E, A, R(79) );

#undef K
#undef F

  data->h0 = ctx.h0 + A;
  data->h1 = ctx.h1 + B;
  data->h2 = ctx.h2 + C;
  data->h3 = ctx.h3 + D;
  data->h4 = ctx.h4 + E;

}

__kernel
void opencl_pmk_kernel(__global gpu_inbuffer *inbuffer, __global gpu_outbuffer *outbuffer) {
    int i;
    const int idx = get_global_id(0);
    SHA_DEV_CTX temp_ctx;
    SHA_DEV_CTX pmk_ctx;
    SHA_DEV_CTX ipad;
    SHA_DEV_CTX opad;
    
    CPY_DEVCTX(inbuffer[idx].ctx_ipad, ipad);
    CPY_DEVCTX(inbuffer[idx].ctx_opad, opad);
    
    CPY_DEVCTX(inbuffer[idx].e1, temp_ctx);
    CPY_DEVCTX(temp_ctx, pmk_ctx);
    for( i = 0; i < 4096-1; i++ )
    {
        sha1_process(ipad, &temp_ctx);
        sha1_process(opad, &temp_ctx);
        pmk_ctx.h0 ^= temp_ctx.h0; pmk_ctx.h1 ^= temp_ctx.h1;
        pmk_ctx.h2 ^= temp_ctx.h2; pmk_ctx.h3 ^= temp_ctx.h3;
        pmk_ctx.h4 ^= temp_ctx.h4;
    }
    CPY_DEVCTX(pmk_ctx, outbuffer[idx].pmk1);
    
    
    CPY_DEVCTX(inbuffer[idx].e2, temp_ctx);
    CPY_DEVCTX(temp_ctx, pmk_ctx);
    for( i = 0; i < 4096-1; i++ )
    {
        sha1_process(ipad, &temp_ctx);
        sha1_process(opad, &temp_ctx);
        pmk_ctx.h0 ^= temp_ctx.h0; pmk_ctx.h1 ^= temp_ctx.h1;
        pmk_ctx.h2 ^= temp_ctx.h2; pmk_ctx.h3 ^= temp_ctx.h3;
        pmk_ctx.h4 ^= temp_ctx.h4;
    }
    CPY_DEVCTX(pmk_ctx, outbuffer[idx].pmk2);
}
