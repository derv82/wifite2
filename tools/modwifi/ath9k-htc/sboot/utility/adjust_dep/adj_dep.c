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

#define BUF_LEN 256


int main(int argc, char **argv)
{
   FILE *file_in, *file_out;
   char line_in_buf[BUF_LEN], line_out_buf[2 * BUF_LEN];


   if ((file_in = fopen("tmp1_file", "r")) == NULL)
   {
      fprintf(stderr, "Can not open input file: <<tmp1_file>>\n"); 
      exit(1);
   }

   if ((file_out = fopen("tmp2_file", "w")) == NULL)
   {
      fprintf(stderr, "Can not open output file: <<tmp2_file>>\n");
      fclose(file_in);
      exit(1);
   }

   while (fgets(line_in_buf, BUF_LEN, file_in) != NULL)
   {
      if (line_in_buf[0] != ' ')
      {
         strcpy(line_out_buf, argv[1]);
         strcat(line_out_buf, line_in_buf);
      }
      else
      {
         strcpy(line_out_buf, line_in_buf);
      }

      fputs(line_out_buf, file_out);
   }

   fclose(file_in);
   fclose(file_out);
}
