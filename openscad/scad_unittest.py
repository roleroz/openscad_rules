# Framework to run tests on openscad. These tests are executed via scad_test() as defined in scad.bzl

import argparse
import logging
import sys
import scad_utils

parser = argparse.ArgumentParser(prog="scad_unittest",
                                 description="Unittest for scad libraries")
parser.add_argument("--scad_file_under_test",
                    type=argparse.FileType('r'),
                    required=True,
                    help="SCAD library under test")
parser.add_argument("--testcases",
                    type=str,
                    action="append",
                    required=True,
                    help="Code to test and corresponding expected STL. Both values are separated by '#'")
parser.add_argument("--assertion_check",
                    type=str,
                    action="append",
                    required=False,
                    help="Code to be tested to produce an assertion")
parser.add_argument("--scad_code_file",
                    type=str,
                    required=True,
                    help="Temporary file to write scad code to")
parser.add_argument("--render_stl",
                    type=str,
                    required=True,
                    help="File that can be used to render STLs")
parser.add_argument("--new_parts_stl",
                    type=str,
                    required=True,
                    help="Output STL file with new sections")
parser.add_argument("--missing_parts_stl",
                    type=str,
                    required=True,
                    help="Output STL file with missing sections")
args = parser.parse_args()

logging.getLogger().setLevel(logging.INFO)

logging.info(args.testcases)
for testcase in args.testcases:
    pieces = testcase.split("#")
    code_under_test = pieces[0]
    expected_stl = pieces[1]

    logging.info("Testing '%s' against %s" % (code_under_test, expected_stl))

    # Render the model under test
    render_result, render_stderr = scad_utils.render_stl(
        "$fn=50; use <%s>; %s;" % (args.scad_file_under_test.name, code_under_test),
        args.scad_code_file,
        args.render_stl)
    if render_result > 0:
        logging.error("Failed to render '%s'", code_under_test)
        for line in render_stderr.split("\\n"):
            logging.error(line)
        sys.exit(1)

    # Diff the generated and expected STL files
    testing_result = scad_utils.diff_stls(expected_stl,
                                          args.render_stl,
                                          args.scad_code_file,
                                          args.new_parts_stl,
                                          args.missing_parts_stl)
    if testing_result:
        logging.error("Failed testing '%s' against %s, new parts STL in %s and missing part STL in %s" % (
            code_under_test,
            expected_stl,
            args.new_parts_stl,
            args.missing_parts_stl))
        sys.exit(1)

if args.assertion_check:
    for assertion_code in args.assertion_check:
        logging.info("Testing that '%s' generates an assertion" % assertion_code)
        render_result, render_stderr = scad_utils.render_stl(
            "$fn=50; use <%s>; %s;" % (args.scad_file_under_test.name, assertion_code),
            args.scad_code_file,
            args.render_stl)
        if "ERROR: Assertion" not in render_stderr:
            logging.error("Code didn't produce assertion")
            for line in render_stderr.split("\\n"):
                logging.error(line)
            sys.exit(1)
