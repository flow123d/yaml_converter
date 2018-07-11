#!/bin/bash
set -x

IN_DIR=.
OUT_DIR=../yaml_new
REV_DIR=../yaml_rev
CONV_SCRIPT="python3 ../../../yaml_converter.py"
$CONV_SCRIPT "*.yaml"

for f in $IN_DIR/*.new.yaml
do
    ref=${f##*/}
    ref=$OUT_DIR/${ref%.new.yaml}.yaml
    cp -f $f $ref
done

$CONV_SCRIPT -r "$OUT_DIR/*.yaml" 
for f in $OUT_DIR/*.new.yaml
do
    ref=${f##*/}
    ref=$REV_DIR/${ref%.new.yaml}.yaml
    mv -f $f $ref
done
