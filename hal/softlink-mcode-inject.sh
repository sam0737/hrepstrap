#!/bin/sh
# Create softlink for mcode-inject. So EMC2 will invoke the mcode-inject.py when these M Codes are reached.

ln -s mcode-inject.py M101
ln -s mcode-inject.py M102
ln -s mcode-inject.py M103
ln -s mcode-inject.py M104
ln -s mcode-inject.py M105
ln -s mcode-inject.py M106
ln -s mcode-inject.py M107
ln -s mcode-inject.py M108
ln -s mcode-inject.py M150
