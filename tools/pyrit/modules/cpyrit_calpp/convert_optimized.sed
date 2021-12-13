s/\([a-zA-Z]\+\)\.\([0-9]\+\)/\1\2/g
s/(\([a-zA-Z0-9]\+\) r>> \([0-9]\+\))/rotate(\1,32-\2)/g
s/ \([a-zA-Z0-9]\+\) r>> \([0-9]\+\);/ rotate(\1,32-\2);/
s/ (\(.\+\)) r>> \([0-9]\+\);/ rotate((\1),32-\2);/
s/data->/data./g
s/ctx->/ctx./g
s/unsigned int/uint2/g
