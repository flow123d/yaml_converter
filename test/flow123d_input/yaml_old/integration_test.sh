#!/bin/bash
set -x

IN_DIR=.
OUT_DIR=../yaml_new
REV_DIR=../yaml_rev
CONV_SCRIPT="python3 ../../../yaml_converter.py" 

# $CONV_SCRIPT "*.yaml"
# 
# for f in $IN_DIR/*.orig.yaml
# do
#     base=${f##*/}
#     base=${base%.orig.yaml}
#     out=$IN_DIR/$base.yaml
#     ref=$OUT_DIR/$base.yaml
#     cp -f $out $ref
#     mv -f $f $out
# done

ls $OUT_DIR
$CONV_SCRIPT -r "$OUT_DIR/*.yaml" 
for f in $OUT_DIR/*.orig.yaml
do
    base=${f##*/}
    base=${base%.orig.yaml}
    out=$OUT_DIR/$base.yaml
    ref=$REV_DIR/$base.yaml
    cp -f $out $ref
    mv -f $f $out
done
