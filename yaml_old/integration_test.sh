#!/bin/bash

IN_DIR=.
OUT_DIR=../yaml_new
REV_DIR=../yaml_rev
python3 ../new_convertor.py "*.yaml"

for f in $IN_DIR/*.new.yaml
do
    
    ref=${f##*/}
    ref=$OUT_DIR/${ref%.new.yaml}.yaml
    output=`diff $f $ref -w`
    if [ -n "$output" ]
    then
        echo $f $ref
    fi
done
