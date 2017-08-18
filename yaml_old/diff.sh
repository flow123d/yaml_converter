#!/bin/bash

converted=${1%.yaml}
kdiff3 ./${converted}.new.yaml ../yaml_new/${converted}.yaml