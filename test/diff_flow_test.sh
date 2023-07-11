#!/bin/bash
#
# Script for debugging the Flow123d changes test: 'test_flow123d_rules.py'
#
# diff_flow_test.sh diff [dir/file]  - call kdiff3 for given file using # fold comparison: org, converted, reference file
# diff_flow_test.sh apply   - overwrite the reference files by the results of the test conversion.
# diff_flow_test.sh revert  - revert changes in reference files

SRCDIR=`dirname "$0"`
echo "SRC:" $SRCDIR


if [ "$1" == "copy" ]
then
  for f in $SRCDIR/flow123d_input/yaml_old/*.out.yaml
  do
    if [ -f $f ]
    then
        fbase=${f##*/}
        fbase=${fbase%.out.yaml}.yaml
        #echo $f $SRCDIR/flow123d_input/yaml_rev/$fbase
        cp $f $SRCDIR/flow123d_input/yaml_new/$fbase
    fi
  done
  for f in $SRCDIR/flow123d_input/yaml_new/*.rev.yaml
  do
    if [ -f $f ]
    then
        fbase=${f##*/}
        fbase=${fbase%.rev.yaml}.yaml
        #echo $f $SRCDIR/flow123d_input/yaml_rev/$fbase
        cp $f $SRCDIR/flow123d_input/yaml_rev/$fbase
    fi
  done
elif [ "$1" == "revert" ]
then
  (cd $SRCDIR/flow123d_input && git checkout yaml_new yaml_old)
  (cd $SRCDIR/flow123d_input && rm yaml_new/*.orig??.yaml yaml_new/*.rev.yaml yaml_old/*.orig??.yaml yaml_old/*.out.yaml)
elif [ "$1" == "diff" ]
    if [ -n "$2" ]
      base = $2
      kdiff3 ./yaml_old/${base}.yaml ../yaml_new/${converted}.yaml
else
    echo "Not supported"
    #fbase=`pwd`/$1

    #converted=${1%.yaml}
    kdiff3 ./${converted}.new.yaml ../yaml_new/${converted}.yaml
fi
