TARGET = ../bin/adj_dep	# for Linux environment
#TARGET = ../bin/adj_dep.exe		# for CygWin environment

all: $(TARGET)

$(TARGET):
	gcc -o $(TARGET) adj_dep.c

install:
	cp adj_dep ../bin

clean:
	-rm $(TARGET)
