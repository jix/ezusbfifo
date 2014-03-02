import time
import sys
import os
from ezusbfifo.client import connect

comm = connect()

try:
    datalen = int(sys.argv[2])
except:
    datalen = 1024 * 128
try:
    blocks = int(sys.argv[1])
except:
    blocks = 22 * 8

datafoo = os.urandom(datalen) * blocks

start = time.time()
last_block = None
block = None
for i in range(blocks):
    last_block, block = block, datafoo[datalen * i: datalen * (i + 1)]

    comm.write(block)

    if last_block is not None:
        read = comm.read(datalen)
        ok = read == last_block
        if not ok:
            print("error")
            for i in range(datalen):
                if read[i] != last_block[i]:
                    print(i)
                    sys.exit(1)
                    break

print(comm.read(datalen) == block)
print(time.time() - start)
