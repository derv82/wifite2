#include <string.h>
#include <assert.h>

#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/aes.h>
#include <openssl/rc4.h>

#include <stdexcept>

#include "ieee80211header.h"
#include "crc.h"
#include "crypto.h"

#if OPENSSL_VERSION_NUMBER < 0x10100000L
EVP_CIPHER_CTX *EVP_CIPHER_CTX_new(void)
{
    EVP_CIPHER_CTX *ctx;

    ctx = OPENSSL_malloc(sizeof(*ctx));
    if (!ctx) return NULL;

    EVP_CIPHER_CTX_init(ctx);

    return ctx;
}

void EVP_CIPHER_CTX_free(EVP_CIPHER_CTX *ctx)
{
    if (ctx == NULL) return;

    EVP_CIPHER_CTX_cleanup(ctx);
    OPENSSL_free(ctx);
}
#endif

//
// EPAOL functions
//

void calc_pmk(const char *psk, const char *essid, uint8_t pmk[32])
{
	PKCS5_PBKDF2_HMAC_SHA1(psk, strlen(psk), (uint8_t*)essid, strlen(essid), 4096, 32, pmk);
}


void calc_ptk(uint8_t bssid[8], uint8_t stmac[8], uint8_t anonce[32], uint8_t snonce[32],
              uint8_t pmk[32], uint8_t ptk[80])
{
	uint8_t pke[100];
	int i;

	memcpy(pke, "Pairwise key expansion", 23);

	if(memcmp(stmac, bssid, 6) < 0) {
		memcpy(pke + 23, stmac, 6);
		memcpy(pke + 29, bssid, 6);
	} else {
		memcpy(pke + 23, bssid, 6);
		memcpy(pke + 29, stmac, 6);
	}

	if(memcmp(snonce, anonce, 32) < 0) {
		memcpy(pke + 35, snonce, 32);
		memcpy(pke + 67, anonce, 32);
	} else {
		memcpy(pke + 35, anonce, 32);
		memcpy(pke + 67, snonce, 32);
	}

	for(i = 0; i < 4; i++) {
		pke[99] = i;
		// hash of pke of length 100, using secret pmk and sha1, save to ptk
		HMAC(EVP_sha1(), pmk, 32, pke, 100, ptk + i * 20, NULL);
	}
}


bool verify_mic(uint8_t *buf, size_t len, int keyver, uint8_t mic[16], uint8_t kck[16])
{
	uint8_t calcmic[20];

	if (keyver == 1)
		HMAC(EVP_md5(), kck, 16, buf, len, calcmic, NULL);
	else
		HMAC(EVP_sha1(), kck, 16, buf, len, calcmic, NULL);

	return memcmp(calcmic, mic, 16) == 0;
}


// FIXME: Where is MD5 used....? Verify integrity....?
static int decrypt_eapol_key_data_rc4(uint8_t ek[32], uint8_t *buf, uint8_t *out, size_t len)
{
	unsigned char skip_buf[256] = {0};
	EVP_CIPHER_CTX *ctx;
	int outl;

	// initialize RC4 stream cipher
	ctx = EVP_CIPHER_CTX_new();
	if (ctx == NULL || !EVP_CIPHER_CTX_set_padding(ctx, 0)
		|| !EVP_CipherInit_ex(ctx, EVP_rc4(), NULL, NULL, NULL, 1)
		|| !EVP_CIPHER_CTX_set_key_length(ctx, 32)
		|| !EVP_CipherInit_ex(ctx, NULL, NULL, ek, NULL, 1))
	{
		fprintf(stderr, "%s: failed to initialize RC4 stream cipher\n", __FUNCTION__);
		EVP_CIPHER_CTX_free(ctx);
		return -1;
	}

	// skip first 256 bytes of RC4 cipher
	if (!EVP_CipherUpdate(ctx, skip_buf, &outl, skip_buf, sizeof(skip_buf))) {
		fprintf(stderr, "%s: failed to skip first 256 bytes of RC4\n", __FUNCTION__);
		EVP_CIPHER_CTX_free(ctx);
		return -1;
	}

#if 0
	printf("skip_buf: ");
	for (size_t i = 0; i < sizeof(skip_buf); ++i) printf("%02X", skip_buf[i]);
	printf("\n");
#endif

	// decrypt data using current RC4 keystream
	if (!EVP_CipherUpdate(ctx, out, &outl, buf, len)) {
		fprintf(stderr, "%s: failed to decrypt EAPOL key data\n", __FUNCTION__);
		EVP_CIPHER_CTX_free(ctx);
		return -1;
	}

#if 0
	printf("Decrypted: ");
	for (size_t i = 0; i < len; ++i) printf("%02X", out[i]);
	printf("\n");
#endif

	EVP_CIPHER_CTX_free(ctx);
	return len;
}


static int decrypt_eapol_key_data_aes(uint8_t kek[16], uint8_t *buf, uint8_t *out, size_t len)
{
	AES_KEY aeskey;
	int outlen;

	if (AES_set_decrypt_key(kek, 128, &aeskey) != 0) {
		fprintf(stderr, "%s: AES_set_decrypt_key failed\n", __FUNCTION__);
		return -1;
	}

	outlen = AES_unwrap_key(&aeskey, NULL, out, buf, len);
	if (outlen <= 0) {
		fprintf(stderr, "%s: AES_unwrap_key failed: %d\n", __FUNCTION__, outlen);
		return outlen;
	}

	return outlen;
}


int decrypt_eapol_key_data(uint8_t iv[16], uint8_t kek[16], EapolKeyVer keyver, uint8_t *buf, uint8_t *out, size_t len)
{
	uint8_t ek[32];

	switch (keyver) {
	case EapolKeyVer_HMAC_MD5_RC4:
		memcpy(ek, iv, 16);
		memcpy(ek + 16, kek, 16);
		for (int i = 0; i < 32; ++i) printf("%02X", ek[i]);
		printf("\n");
		return decrypt_eapol_key_data_rc4(ek, buf, out, len);
	case EapolKeyVer_HMAC_SHA1_AES:
	case EapolKeyVer_AES_128_CMAC:
		return decrypt_eapol_key_data_aes(kek, buf, out, len);
	default:
		fprintf(stderr, "%s: Unsupported keyver %d\n", __FUNCTION__, keyver);
		return -1;
	}
}


//
// TKIP Decryption functions
//

/**
 * IEEE 802.11 2012 - 11.4.2.5 TKIP mixing function
 *
 * Apparently this is the same S-Box as used in AES.
 */
const uint16_t tkipSbox[2][256]=
{
	{
		0xC6A5, 0xF884, 0xEE99, 0xF68D, 0xFF0D, 0xD6BD, 0xDEB1, 0x9154,
		0x6050, 0x0203, 0xCEA9, 0x567D, 0xE719, 0xB562, 0x4DE6, 0xEC9A,
		0x8F45, 0x1F9D, 0x8940, 0xFA87, 0xEF15, 0xB2EB, 0x8EC9, 0xFB0B,
		0x41EC, 0xB367, 0x5FFD, 0x45EA, 0x23BF, 0x53F7, 0xE496, 0x9B5B,
		0x75C2, 0xE11C, 0x3DAE, 0x4C6A, 0x6C5A, 0x7E41, 0xF502, 0x834F,
		0x685C, 0x51F4, 0xD134, 0xF908, 0xE293, 0xAB73, 0x6253, 0x2A3F,
		0x080C, 0x9552, 0x4665, 0x9D5E, 0x3028, 0x37A1, 0x0A0F, 0x2FB5,
		0x0E09, 0x2436, 0x1B9B, 0xDF3D, 0xCD26, 0x4E69, 0x7FCD, 0xEA9F,
		0x121B, 0x1D9E, 0x5874, 0x342E, 0x362D, 0xDCB2, 0xB4EE, 0x5BFB,
		0xA4F6, 0x764D, 0xB761, 0x7DCE, 0x527B, 0xDD3E, 0x5E71, 0x1397,
		0xA6F5, 0xB968, 0x0000, 0xC12C, 0x4060, 0xE31F, 0x79C8, 0xB6ED,
		0xD4BE, 0x8D46, 0x67D9, 0x724B, 0x94DE, 0x98D4, 0xB0E8, 0x854A,
		0xBB6B, 0xC52A, 0x4FE5, 0xED16, 0x86C5, 0x9AD7, 0x6655, 0x1194,
		0x8ACF, 0xE910, 0x0406, 0xFE81, 0xA0F0, 0x7844, 0x25BA, 0x4BE3,
		0xA2F3, 0x5DFE, 0x80C0, 0x058A, 0x3FAD, 0x21BC, 0x7048, 0xF104,
		0x63DF, 0x77C1, 0xAF75, 0x4263, 0x2030, 0xE51A, 0xFD0E, 0xBF6D,
		0x814C, 0x1814, 0x2635, 0xC32F, 0xBEE1, 0x35A2, 0x88CC, 0x2E39,
		0x9357, 0x55F2, 0xFC82, 0x7A47, 0xC8AC, 0xBAE7, 0x322B, 0xE695,
		0xC0A0, 0x1998, 0x9ED1, 0xA37F, 0x4466, 0x547E, 0x3BAB, 0x0B83,
		0x8CCA, 0xC729, 0x6BD3, 0x283C, 0xA779, 0xBCE2, 0x161D, 0xAD76,
		0xDB3B, 0x6456, 0x744E, 0x141E, 0x92DB, 0x0C0A, 0x486C, 0xB8E4,
		0x9F5D, 0xBD6E, 0x43EF, 0xC4A6, 0x39A8, 0x31A4, 0xD337, 0xF28B,
		0xD532, 0x8B43, 0x6E59, 0xDAB7, 0x018C, 0xB164, 0x9CD2, 0x49E0,
		0xD8B4, 0xACFA, 0xF307, 0xCF25, 0xCAAF, 0xF48E, 0x47E9, 0x1018,
		0x6FD5, 0xF088, 0x4A6F, 0x5C72, 0x3824, 0x57F1, 0x73C7, 0x9751,
		0xCB23, 0xA17C, 0xE89C, 0x3E21, 0x96DD, 0x61DC, 0x0D86, 0x0F85,
		0xE090, 0x7C42, 0x71C4, 0xCCAA, 0x90D8, 0x0605, 0xF701, 0x1C12,
		0xC2A3, 0x6A5F, 0xAEF9, 0x69D0, 0x1791, 0x9958, 0x3A27, 0x27B9,
		0xD938, 0xEB13, 0x2BB3, 0x2233, 0xD2BB, 0xA970, 0x0789, 0x33A7,
		0x2DB6, 0x3C22, 0x1592, 0xC920, 0x8749, 0xAAFF, 0x5078, 0xA57A,
		0x038F, 0x59F8, 0x0980, 0x1A17, 0x65DA, 0xD731, 0x84C6, 0xD0B8,
		0x82C3, 0x29B0, 0x5A77, 0x1E11, 0x7BCB, 0xA8FC, 0x6DD6, 0x2C3A
	},
	/** Note: this is identical to the previous table but byte-swapped */
	{
		0xA5C6, 0x84F8, 0x99EE, 0x8DF6, 0x0DFF, 0xBDD6, 0xB1DE, 0x5491,
		0x5060, 0x0302, 0xA9CE, 0x7D56, 0x19E7, 0x62B5, 0xE64D, 0x9AEC,
		0x458F, 0x9D1F, 0x4089, 0x87FA, 0x15EF, 0xEBB2, 0xC98E, 0x0BFB,
		0xEC41, 0x67B3, 0xFD5F, 0xEA45, 0xBF23, 0xF753, 0x96E4, 0x5B9B,
		0xC275, 0x1CE1, 0xAE3D, 0x6A4C, 0x5A6C, 0x417E, 0x02F5, 0x4F83,
		0x5C68, 0xF451, 0x34D1, 0x08F9, 0x93E2, 0x73AB, 0x5362, 0x3F2A,
		0x0C08, 0x5295, 0x6546, 0x5E9D, 0x2830, 0xA137, 0x0F0A, 0xB52F,
		0x090E, 0x3624, 0x9B1B, 0x3DDF, 0x26CD, 0x694E, 0xCD7F, 0x9FEA,
		0x1B12, 0x9E1D, 0x7458, 0x2E34, 0x2D36, 0xB2DC, 0xEEB4, 0xFB5B,
		0xF6A4, 0x4D76, 0x61B7, 0xCE7D, 0x7B52, 0x3EDD, 0x715E, 0x9713,
		0xF5A6, 0x68B9, 0x0000, 0x2CC1, 0x6040, 0x1FE3, 0xC879, 0xEDB6,
		0xBED4, 0x468D, 0xD967, 0x4B72, 0xDE94, 0xD498, 0xE8B0, 0x4A85,
		0x6BBB, 0x2AC5, 0xE54F, 0x16ED, 0xC586, 0xD79A, 0x5566, 0x9411,
		0xCF8A, 0x10E9, 0x0604, 0x81FE, 0xF0A0, 0x4478, 0xBA25, 0xE34B,
		0xF3A2, 0xFE5D, 0xC080, 0x8A05, 0xAD3F, 0xBC21, 0x4870, 0x04F1,
		0xDF63, 0xC177, 0x75AF, 0x6342, 0x3020, 0x1AE5, 0x0EFD, 0x6DBF,
		0x4C81, 0x1418, 0x3526, 0x2FC3, 0xE1BE, 0xA235, 0xCC88, 0x392E,
		0x5793, 0xF255, 0x82FC, 0x477A, 0xACC8, 0xE7BA, 0x2B32, 0x95E6,
		0xA0C0, 0x9819, 0xD19E, 0x7FA3, 0x6644, 0x7E54, 0xAB3B, 0x830B,
		0xCA8C, 0x29C7, 0xD36B, 0x3C28, 0x79A7, 0xE2BC, 0x1D16, 0x76AD,
		0x3BDB, 0x5664, 0x4E74, 0x1E14, 0xDB92, 0x0A0C, 0x6C48, 0xE4B8,
		0x5D9F, 0x6EBD, 0xEF43, 0xA6C4, 0xA839, 0xA431, 0x37D3, 0x8BF2,
		0x32D5, 0x438B, 0x596E, 0xB7DA, 0x8C01, 0x64B1, 0xD29C, 0xE049,
		0xB4D8, 0xFAAC, 0x07F3, 0x25CF, 0xAFCA, 0x8EF4, 0xE947, 0x1810,
		0xD56F, 0x88F0, 0x6F4A, 0x725C, 0x2438, 0xF157, 0xC773, 0x5197,
		0x23CB, 0x7CA1, 0x9CE8, 0x213E, 0xDD96, 0xDC61, 0x860D, 0x850F,
		0x90E0, 0x427C, 0xC471, 0xAACC, 0xD890, 0x0506, 0x01F7, 0x121C,
		0xA3C2, 0x5F6A, 0xF9AE, 0xD069, 0x9117, 0x5899, 0x273A, 0xB927,
		0x38D9, 0x13EB, 0xB32B, 0x3322, 0xBBD2, 0x70A9, 0x8907, 0xA733,
		0xB62D, 0x223C, 0x9215, 0x20C9, 0x4987, 0xFFAA, 0x7850, 0x7AA5,
		0x8F03, 0xF859, 0x8009, 0x171A, 0xDA65, 0x31D7, 0xC684, 0xB8D0,
		0xC382, 0xB029, 0x775A, 0x111E, 0xCB7B, 0xFCA8, 0xD66D, 0x3A2C
	}
};

static inline uint8_t LOW8(uint32_t x) { return x % 0x100; }
static inline uint8_t HIGH8(uint32_t x) { return (x >> 8) % 0x100; }
static inline uint16_t LOW16(uint32_t x) { return x % 0x10000; }
static inline uint16_t HIGH16(uint32_t x) { return (x >> 16 ) % 0x10000; }
static inline uint16_t ROTR1(uint16_t x) { return ((x >> 1) & 0x7FFF) ^ ((x & 1) << 15); }
static inline uint16_t MK16(uint8_t high, uint8_t low) { return low ^ (LOW8(high) << 8); }

// #define _S_(x)        (TkipSbox[0][LO8(x)] ^ TkipSbox[1][HI8(x)])
static inline uint16_t get_sbox(uint16_t x)
{
	return tkipSbox[0][LOW8(x)] ^ tkipSbox[1][HIGH8(x)];
}

// #define TK16(N)       MK16(enckey[2*(N)+1], enckey[2*(N)])
static void enckey8_to_16(uint8_t enckey8[16], uint16_t enckey16[8])
{
	for (int i = 0; i < 8; ++i)
		enckey16[i] = MK16(enckey8[2 * i + 1], enckey8[2 * i]);
}


bool encrypt_wep(uint8_t *data, size_t len, uint8_t wepseed[16], uint8_t *out)
{
	RC4_KEY rc4key;

	RC4_set_key(&rc4key, 16, wepseed);
	RC4(&rc4key, len, data, out);

	return true;
}

bool decrypt_wep(uint8_t *data, size_t len, uint8_t wepseed[16], uint8_t *out)
{
	encrypt_wep(data, len, wepseed, out);
	return endswith_valid_crc(out, len);
}

/** we combine phase-1 and phase-2 */
int calc_tkip_ppk(uint8_t *buf, size_t len, uint8_t enckey8[16], uint8_t wepseed[16])
{
	ieee80211header *hdr = (ieee80211header*)buf;
	tkipheader *tkip;
	int i, z;
	uint32_t iv32;
	uint16_t iv16;
	uint16_t ppk[6];
	uint16_t enckey[8];
	uint8_t *macTA;

	enckey8_to_16(enckey8, enckey);

	if (len < sizeof(ieee80211header))
		return -1;

	// get MAC address of transmitter
	macTA = hdr->addr2;

	z = sizeof(ieee80211header);
	if (ieee80211_dataqos(hdr)) z += 2;
	tkip = (tkipheader*)(buf + z);

	iv16 = MK16(tkip->iv.tsc1, tkip->iv.tsc0);
	iv32 = tkip->eiv.tsc2 | (tkip->eiv.tsc3 << 8) | (tkip->eiv.tsc4 << 16) | (tkip->eiv.tsc5 << 24);

	ppk[0] = LOW16( iv32 );
	ppk[1] = HIGH16( iv32 );
	ppk[2] = MK16( macTA[1], macTA[0] );
	ppk[3] = MK16( macTA[3], macTA[2] );
	ppk[4] = MK16( macTA[5], macTA[4] );

	for( i = 0; i < 8; i++ )
	{
		ppk[0] += get_sbox( ppk[4] ^ enckey[ (i & 1) + 0 ] );
		ppk[1] += get_sbox( ppk[0] ^ enckey[ (i & 1) + 2 ] );
		ppk[2] += get_sbox( ppk[1] ^ enckey[ (i & 1) + 4 ] );
		ppk[3] += get_sbox( ppk[2] ^ enckey[ (i & 1) + 6 ] );
		ppk[4] += get_sbox( ppk[3] ^ enckey[ (i & 1) + 0 ] ) + i;
	}

	ppk[5] = ppk[4] + iv16;

	ppk[0] += get_sbox( ppk[5] ^ enckey[0] );
	ppk[1] += get_sbox( ppk[0] ^ enckey[1] );
	ppk[2] += get_sbox( ppk[1] ^ enckey[2] );
	ppk[3] += get_sbox( ppk[2] ^ enckey[3] );
	ppk[4] += get_sbox( ppk[3] ^ enckey[4] );
	ppk[5] += get_sbox( ppk[4] ^ enckey[5] );

	ppk[0] += ROTR1( ppk[5] ^ enckey[6] );
	ppk[1] += ROTR1( ppk[0] ^ enckey[7] );
	ppk[2] += ROTR1( ppk[1] );
	ppk[3] += ROTR1( ppk[2] );
	ppk[4] += ROTR1( ppk[3] );
	ppk[5] += ROTR1( ppk[4] );

	wepseed[0] =   HIGH8( iv16 );
	wepseed[1] = ( HIGH8( iv16 ) | 0x20 ) & 0x7F;
	wepseed[2] =   LOW8( iv16 );
	wepseed[3] =   LOW8( (ppk[5] ^ enckey[0] ) >> 1);

	for( i = 0; i < 6; i++ )
	{
		wepseed[4 + ( 2 * i)] = LOW8( ppk[i] );
		wepseed[5 + ( 2 * i)] = HIGH8( ppk[i] );
	}

	return 0;
}


int decrypt_tkip(uint8_t *buf, size_t len, uint8_t enckey[16], uint8_t *out)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	uint8_t wepseed[16];
	int pos;

	// get position of encrypted data
	pos = sizeof(ieee80211header) + sizeof(tkipheader);
	if (ieee80211_dataqos(hdr))
		pos += sizeof(ieee80211qosheader);

	// calculate ppk and decrypt packet
	calc_tkip_ppk(buf, len, enckey, wepseed);
	memcpy(out, buf, pos);
	return decrypt_wep(buf + pos, len - pos, wepseed, out + pos);
}

//
//	MICHAEL FUNCTIONS
//

#define ROL32( A, n ) ( ((A) << (n)) | ( ((A)>>(32-(n))) & ( (1UL << (n)) - 1 ) ) )
#define ROR32( A, n ) ROL32( (A), 32-(n) )

struct mic_state
{
	uint32_t l;
	uint32_t r;

	uint32_t word;
	int bytesin;
};

// FIXME: Version of GETWORD and SETWORD for big endian systesm

#define GETWORD(buffer)		\
	( (buffer)[0]		\
	| ( (buffer)[1] << 8  )	\
	| ( (buffer)[2] << 16 )	\
	| ( (buffer)[3] << 24 )	\
	)

#define SETWORD(buffer, word)		\
	(buffer)[0] = (word);		\
	(buffer)[1] = (word) >> 8;	\
	(buffer)[2] = (word) >> 16;	\
	(buffer)[3] = (word) >> 24;

static void block(mic_state *state, uint32_t word)
{
	assert(state->bytesin == 0);

	state->l ^= word;
	state->r ^= ROL32(state->l, 17);
	state->l += state->r;
	state->r ^= ((state->l & 0xff00ff00) >> 8) | ((state->l & 0x00ff00ff) << 8);
	state->l += state->r;
	state->r ^= ROL32(state->l, 3);
	state->l += state->r;
	state->r ^= ROR32(state->l, 2);
	state->l += state->r;
}

static void block_reverse(mic_state *state, uint32_t word)
{
	state->l -= state->r;
	state->r ^= ROR32(state->l, 2);
	state->l -= state->r;
	state->r ^= ROL32(state->l, 3);
	state->l -= state->r;
	state->r ^= ((state->l & 0xff00ff00) >> 8) | ((state->l & 0x00ff00ff) << 8);
	state->l -= state->r;
	state->r ^= ROL32(state->l, 17);
	state->l ^= word;
}

static void append_byte(mic_state *state, uint8_t byte)
{
	state->word |= byte << (state->bytesin * 8);
	state->bytesin++;

	if (state->bytesin == 4) {
		state->bytesin = 0;
		block(state, state->word);
		state->word = 0;
	}
}

void michael(uint8_t key[8], uint8_t *buffer, size_t len, uint8_t mic[8])
{
	mic_state state;
	size_t i;

	memset(&state, 0, sizeof(state));
	state.l = GETWORD(key);
	state.r = GETWORD(key + 4);

	for (i = 0; i + 4 < len;  i += 4)
		block(&state, GETWORD(buffer + i));

	// append last bytes of message
	for (; i < len; ++i)
		append_byte(&state, buffer[i]);

	// append the minimum padding
	append_byte(&state, 0x5A);
	append_byte(&state, 0x00);
	append_byte(&state, 0x00);
	append_byte(&state, 0x00);
	append_byte(&state, 0x00);
	// and then zeroes until the length is a multiple of 4
	while (state.bytesin != 0)
		append_byte(&state, 0x00);

	SETWORD(mic, state.l);
	SETWORD(mic + 4, state.r);
}

void reverse_michael(uint8_t key[8], uint8_t *buffer, size_t len, uint8_t mic[8])
{
	uint8_t packet[4096];
	mic_state state;
	int i;

	if (sizeof(packet) + 10 < len)
		throw std::invalid_argument("given buffer is too large to handle");

#if 0
	printf("Reverse Michael over: ");
	for (size_t i = 0; i < len; ++i)
		printf("%02X ", buffer[i]);
	printf("\n");

	printf("With MIC: ");
	for (size_t i = 0; i < 8; ++i)
		printf("%02X ", mic[i]);
	printf("\n");
#endif

	// append Michael padding
	memcpy(packet, buffer, len);
	packet[len++] = 0x5A;
	packet[len++] = 0x00;
	packet[len++] = 0x00;
	packet[len++] = 0x00;
	packet[len++] = 0x00;
	// create 4-byte aligned packet
	while (len % 4 != 0)
		packet[len++] = 0;

	// init state
	memset(&state, 0, sizeof(state));
	state.l = GETWORD(mic);
	state.r = GETWORD(mic + 4);

	// apply reverse block until all words have been processed
	for (i = len - 4; i >= 0; i -= 4)
		block_reverse(&state, GETWORD(&packet[i]));

	// extract key
	SETWORD(key, state.l);
	SETWORD(key + 4, state.r);
}


static int test_michael_block()
{
	mic_state state;
	int i;

	memset(&state, 0, sizeof(state));
	state.l = 1;
	state.r = 0;

	for (i = 0; i < 1000; ++i)
		block(&state, 0);

	return state.l == 0x9f04c4ad && state.r == 0x2ec6c2bf;
}


static int test_michael_mic()
{
	uint8_t key[] = "\xD5\x5e\x10\x05\x10\x12\x89\x86";
	uint8_t mic[8];

	michael(key, (uint8_t*)"Michael", 7, mic);

	return memcmp(mic, "\x0a\x94\x2b\x12\x4e\xca\xa5\x46", 8) == 0;
}

static int test_reverse_michael()
{
	uint8_t key[] = "\xD5\x5e\x10\x05\x10\x12\x89\x86";
	uint8_t mic[8];
	uint8_t reversekey[8];
	uint8_t test1[] = "Michael";
	uint8_t test2[] = "MichaelXY";

	michael(key, test1, sizeof(test1), mic);
	reverse_michael(reversekey, test1, sizeof(test1), mic);
	if (memcmp(reversekey, key, 8) != 0)
		return -1;

	michael(key, test2, sizeof(test2), mic);
	reverse_michael(reversekey, test2, sizeof(test2), mic);
	if (memcmp(reversekey, key, 8) != 0)
		return -1;

	return 0;
}

int test_michael()
{
	if (!test_michael_block()) {
		fprintf(stderr, "Michael block function failed\n");
		return -1;
	}

	if (!test_michael_mic()) {
		fprintf(stderr, "Michael MIC function failed\n");
		return -1;
	}

	if (test_reverse_michael() < 0) {
		fprintf(stderr, "Reverse Michael MIC function failed\n");
		return -1;
	}

	return 0;
}


int calc_michael_key(uint8_t *buf, size_t len, uint8_t mickey[8])
{
	ieee80211header *hdr = (ieee80211header*)buf;
	size_t datapos, datalen;
	uint8_t michaelbuf[2048];
	size_t michaellen;
	uint8_t *dest, *source;
	int priority;

	// get source and destination MAC
	if (hdr->fc.tods) {
		source = hdr->addr2;
		dest = hdr->addr3;
	} else {
		source = hdr->addr3;
		dest = hdr->addr1;
	}

	// get position of decrypted data & priority
	datapos = sizeof(ieee80211header) + sizeof(tkipheader);
	priority = 0;
	if (ieee80211_dataqos(hdr)) {
		ieee80211qosheader *qos = (ieee80211qosheader*)(hdr + 1);

		datapos += sizeof(ieee80211qosheader);
		priority = qos->tid;
	}
	datalen = len - datapos;

	// construct data given to michael algorithm
	memcpy(michaelbuf, dest, 6);
	memcpy(michaelbuf + 6, source, 6);
	michaelbuf[12] = priority;
	memset(michaelbuf + 13, 0, 3);
	memcpy(michaelbuf + 16, buf + datapos, datalen);
	michaellen = 16 + datalen - 4 - 8;

	// calculate MIC key
	reverse_michael(mickey, michaelbuf, michaellen, michaelbuf + michaellen);

	return 0;
}


