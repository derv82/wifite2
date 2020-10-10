TARGET = ../bin/patch_gen		# for Linux environment
#TARGET = ../bin/_gen.exe	# for CygWin environment

INC = $(HOME)/project/src/inc

all: $(TARGET)

$(TARGET):
	gcc -o $(TARGET) -I$(INC) main.c patch.c


clean:
	-rm $(TARGET)
