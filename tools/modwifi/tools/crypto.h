#ifndef CRYPTO_H__
#define CRYPTO_H__

#include <stdint.h>

#include "eapol.h"

//
// Key configuration and EAPOL functions
//

/** calculate pairwise master key from passphrase and essid */
void calc_pmk(const char *psk, const char *essid, uint8_t pmk[32]);

/* derive the pairwise transcient keys from a bunch of stuff */
void calc_ptk(uint8_t bssid[8], uint8_t stmac[8], uint8_t anonce[32], uint8_t snonce[32],
              uint8_t pmk[32], uint8_t ptk[80]);

/** verify the MIC of an eapol message */
bool verify_mic(uint8_t *buf, size_t len, int keyver, uint8_t mic[16], uint8_t kck[16]);

/**
 * decrypt the WPA Key Data in an EAPOL handshake message
 *
 * len is the length of buf
 * out must be at least of size (len - 8)
 */
int decrypt_eapol_key_data(uint8_t iv[16], uint8_t kek[16], EapolKeyVer keyver, uint8_t *buf, uint8_t *out, size_t len);


//
// Packet decryption functions
//

/** WEP decryption/encryption functions */
bool encrypt_wep(uint8_t *data, size_t len, uint8_t wepseed[16]);
bool decrypt_wep(uint8_t *data, size_t len, uint8_t wepseed[16]);

/** calculate per packet key for TKIP */
int calc_tkip_ppk(uint8_t *buf, size_t len, uint8_t enckey8[16], uint8_t wepseed[16]);

/** decrypt a tkip packet in place */
int decrypt_tkip(uint8_t *buf, size_t len, uint8_t enckey[16], uint8_t *out);


int test_michael();

/** reverse Michael algorithm to get MIC key */
int calc_michael_key(uint8_t *buf, size_t len, uint8_t mickey[8]);

#endif // CRYPTO_H__
