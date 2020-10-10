DIRS = bin2hex
TARGET_DIR = ./bin

all:
	@mkdir -p $(TARGET_DIR)
	@for i in $(DIRS) ; do $(MAKE) -C $$i || exit $? ; done

clean :
	@for i in $(DIRS) ; do $(MAKE) -C $$i clean; done
