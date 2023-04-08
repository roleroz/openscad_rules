#!/bin/bash
echo "$@"

bazel_tools/scad_unittest "$@"
