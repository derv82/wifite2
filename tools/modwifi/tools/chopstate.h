
#ifndef CHOPCHOP_H
#define CHOPCHOP_H

#include <stdint.h>

class ChopState
{
public:
	void init(uint8_t *buf, size_t len);
	void set_decrypted(uint8_t *decrypted, size_t len);
	void clear();
	bool empty() { return !this->isinit; }
	/** length of the buffer being attacked */
	int length() { return len; }
	/** current byte we are guessing (but still don't know!!) */
	int currpos() { return pos; }
	/** number of keystream bytes we have derived */
	int chopped() { return len - pos - 1; }

	/** try next value */
	void next_guess();
	/** set a given guess (mainly used for debugging) */
	void set_guess(int guess);
	/** get current guess */
	int get_guess() { return guess; }
	/** get the modified packet (ICV) corresponding to current guess */
	int getbuf(uint8_t *buf, size_t len);

	/** current guess is correct - advance to next position */
	bool advance();

	/** revert previous guess (call if something went wrong) */
	void revert();
	/** call if you know the plaintext at the current position of the original packet */
	bool simulate(uint8_t plain);

	/** result of ChopChop attack is partly (or fully) decrpted packet */
	int get_result(uint8_t *buf, size_t len);
	/** uses the current chopped bytes to guess the remaining content of ARP request */
	int guess_arprequest(uint8_t *buf, size_t len);

	/** automatic tests to verify implementation */
	static int unittests();


private:
	/** is the structure initialized / being used? */
	bool isinit;

	/** original packet we are attacking */
	uint8_t original[1024];
	/** decrypted packet for debugging */
	uint8_t decrypted[1024];
	bool have_decrypted;
	/** length of original and decrypted */
	size_t len;

	/** derived keystream from the chopchop process - filled in at [pos+1:] */
	uint8_t keystream[1024];

	/** packet being chopped */
	uint8_t buf[1024];
	/** current position of byte we are guessing */
	size_t pos;
	/** current guess for plaintext value */
	int guess;

	void clear_guess();
};


#endif // CHOPCHOP_H
