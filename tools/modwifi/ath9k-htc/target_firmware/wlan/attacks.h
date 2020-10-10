#ifndef ATTACKS_H
#define ATTACKS_H

// Utility functions
int attack_confradio(struct ath_softc_tgt *sc, int jam);
struct ath_tx_buf * attack_build_packet(struct ath_softc_tgt *sc, uint8_t *data,
			a_int32_t len, char waitack, unsigned char destmac[6]);
void attack_free_packet(struct ath_softc_tgt *sc, struct ath_tx_buf *bf);

// Attack implementations
int attack_reactivejam(struct ath_softc_tgt *sc, unsigned char source[6],
		       unsigned int msecs);
int attack_constantjam_start(struct ath_softc_tgt *sc, char waitack,
			     unsigned char destmac[6], a_uint16_t length);
int attack_constantjam_stop(struct ath_softc_tgt *sc);
int attack_fastreply(struct ath_softc_tgt *sc, struct ath_tx_buf *bf,
		     unsigned char source[6], unsigned int msecs, int jam);

#endif // ATTACKS_H

