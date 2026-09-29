CC = cc
CFLAGS = -Wall -Wextra
TARGET = app
DEPS = main.c config.h

$(TARGET): main.o
	$(CC) main.o -o $(TARGET)

main.o: $(DEPS)
	$(CC) $(CFLAGS) -c main.c -o main.o

clean:
	rm -f $(TARGET) main.o
