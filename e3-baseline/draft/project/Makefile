CC = gcc
CFLAGS = -Wall -Wextra
TARGET = hello
SOURCE = src/hello.c

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) $(SOURCE) -o $(TARGET)

clean:
	rm -f $(TARGET)

# make:编译生成hello;
# make clean:删除生成的hello;