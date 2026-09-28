#!/bin/sh
for i in a b c d e f g h i j k l m n o p q r s t u v w x y z
do
 cd $i
 for n in *; do printf '%s\n' "\"$n\","; done
# ls
 cd ..
done
