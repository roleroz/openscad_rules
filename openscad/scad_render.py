import argparse
import logging
import os.path

import scad_utils

parser = argparse.ArgumentParser(prog="scad_render",
                                 description="Utility to render expected files for scad_test()")
parser.add_argument("--scad_file_under_test",
                    type=argparse.FileType('r'),
                    required=True,
                    help="SCAD library under test")
parser.add_argument("--render_cases",
                    type=str,
                    action="append",
                    required=True,
                    help=("String representation of a str->str dict, where the key is the code to be rendered, and " +
                          "the value is the expected STL filename"))
parser.add_argument("--output_basedir",
                    type=str,
                    required=True,
                    help="Base directory where to put all the outputs")
args = parser.parse_args()

logging.getLogger().setLevel(logging.INFO)

for testcase in args.render_cases:
    pieces = testcase.split("#")
    code_under_test = pieces[0]
    render_stl = os.path.join(args.output_basedir, pieces[1])

    logging.info("Rendering '%s' into %s" % (code_under_test, render_stl))

    render_stl_dir = os.path.dirname(render_stl)
    if not os.path.exists(render_stl_dir):
        logging.info("Creating missing directory %s" % render_stl_dir)
        os.makedirs(render_stl_dir)

    render_result, render_stderr = scad_utils.render_stl(
        "$fn=50; use <%s>; %s;" % (args.scad_file_under_test.name, code_under_test),
        "code.scad",
        render_stl)
    if render_result > 0:
        logging.error("Failed to render '%s'" % code_under_test)
        for line in render_stderr.split("\\n"):
            logging.error(line)
