TARGET = ../bin/bin2hex		# for Linux environment
TARGET_DIR = ../bin
E=echo

all: $(TARGET)

$(TARGET):
	@mkdir -p $(TARGET_DIR)
	gcc -o $(TARGET) bin2hex.c
	@$(E) "  CC " $@

clean:
	-rm $(TARGET)
