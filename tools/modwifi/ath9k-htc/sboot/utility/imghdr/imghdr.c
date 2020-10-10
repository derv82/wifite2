/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#include <stdio.h>
#include <string.h>


#define MAX_READ_SIZE	80

static void crc16ccitt_init(unsigned short *uCcitt16)
{
	*uCcitt16 = 0xFFFF;
}

static void crc16ccitt_update(unsigned short *uCcitt16, unsigned char *pBuffer, unsigned long uBufSize)
{
	unsigned long i = 0;
	unsigned long j = 0;

	for(i = 0; i < uBufSize; i++)
	{
		for(j=0; j<3; j++)
		{
			*uCcitt16 = (*uCcitt16 >> 8) | (*uCcitt16 << 8);
			*uCcitt16 ^= pBuffer[3-j];
			*uCcitt16 ^= (*uCcitt16 & 0xFF) >> 4;
			*uCcitt16 ^= (*uCcitt16 << 8) << 4;
			*uCcitt16 ^= ((*uCcitt16 & 0xFF) << 4) << 1;
		}
	}
}

static void crc16ccitt_final(unsigned short *uCcitt16)
{
	*uCcitt16 = ~(*uCcitt16);
}

void write_file(unsigned short crc, unsigned short file_size, FILE *out, FILE *in)
{
	unsigned char buffer[MAX_READ_SIZE];
	unsigned short size;

	//set file pointer to start of the file
	if( feof(in) )
		fseek(in,0,SEEK_SET);

	while(1)
	{
		size = fread(buffer, sizeof(unsigned char), sizeof(buffer), in);
	
		if (size<MAX_READ_SIZE)
		{
			if( size%4==1 )
			{
				buffer[size] = 0x0;
				buffer[size+1] = 0x0;
				buffer[size+2] = 0x0;
				size+=3;
			}
			else if ( size%4==2 )
			{
				buffer[size] = 0x0;
				buffer[size+1] = 0x0;
				size+=2;
			}
			else if ( size%4==3 )
			{
				buffer[size] = 0x0;
				size+=1;
			}
			fwrite(buffer, sizeof(unsigned char), size, out);
			goto ERR_DONE;
		}
		fwrite(buffer, sizeof(unsigned char), MAX_READ_SIZE, out);
	}
ERR_DONE:

	fwrite(&crc, sizeof(unsigned char), sizeof(short), out);
	fwrite(&file_size, sizeof(unsigned char), sizeof(short), out);

	return;
}


unsigned short cal_crc(FILE *in)
{
	int size;
	long file_size;
	unsigned short crc = 0;
	unsigned char buffer[MAX_READ_SIZE];

	file_size = size = 0;

    crc16ccitt_init(&crc);

	while(1)
	{
		size = fread(buffer, sizeof(unsigned char), sizeof(buffer), in);
		file_size += size;

		if( size%4==1 )
		{
			buffer[size] = 0x0;
			buffer[size+1] = 0x0;
			buffer[size+2] = 0x0;
			size+=3;
		}
		else if ( size%4==2 )
		{
			buffer[size] = 0x0;
			buffer[size+1] = 0x0;
			size+=2;
		}
		else if ( size%4==3 )
		{
			buffer[size] = 0x0;
			size+=1;
		}

		crc16ccitt_update(&crc, (unsigned char*)buffer, size);

		if (size<MAX_READ_SIZE)
			goto ERR_DONE;
	}

ERR_DONE:
	
    crc16ccitt_final(&crc);
    printf(" ==> output crc 0x%04x with file size 0x%04x\n\r", crc, file_size);

	return crc;
}


int main(int argc, char* argv[])
{
	FILE *in, *out;
	int retVal;
	int i=0;
	unsigned short crc = 0;
	unsigned short size = 0;
	char input_file_name[80];
	char output_file_name[80];
	
	in = out = 0x0;

	if( argc < 3 )
	{
		printf("\"imghdr [input_file] [output_file] - calculate the image and prefix to the binary \"!\n\r");
		goto ERR_DONE;
	}
	strcpy(input_file_name, argv[1]);
	strcpy(output_file_name, argv[2]);

	printf("imghdr %s %s!\n\r", input_file_name, output_file_name);

	if((in = fopen(input_file_name,"rb")) == NULL)
		goto ERR_DONE;

	if((out = fopen(output_file_name,"wt")) == NULL)
		goto ERR_DONE;
	
	crc = cal_crc(in);
	
	fseek( in, 0, SEEK_END );
	size = ftell(in);    // get file length
	fseek( in, 0, SEEK_SET );
	
	printf(" ==> (2) output crc 0x%04x with file size 0x%04x\n\r", crc, size);
	write_file(crc, size, out, in);


ERR_DONE:

	if(in) fclose(in);
	if(out) fclose(out);

	return 0;

}
