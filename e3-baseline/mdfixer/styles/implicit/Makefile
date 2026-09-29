CC = cc
CFLAGS = -Wall -Wextra
DEPFLAGS = -MMD -MP
TARGET = app

$(TARGET): main.o
	$(CC) main.o -o $(TARGET)

%.o: %.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

-include main.d

clean:
	rm -f $(TARGET) main.o main.d
