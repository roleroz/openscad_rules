import logging
import subprocess


# Runs OpenSCAD to render an STL file, input code stored in scad_file, output will be stored at output_file
#
# Returns the exit code of OpenSCAD when executing the provided code
def _run_openscad(scad_file, output_file):
    cmd = "openscad --export-format stl -o %s %s" % (output_file, scad_file)
    logging.info("Executing OpenSCAD as '%s'" % cmd)
    cmd_output = subprocess.run(cmd, shell=True, capture_output=True)
    cmd_return_code = cmd_output.returncode
    cmd_stderr = str(cmd_output.stderr)
    # Fail the render if it can't open an import
    if ("WARNING: Can't open import file" in cmd_stderr) or ("WARNING: Can't open library" in cmd_stderr):
        logging.error("Failed import")
        cmd_return_code = 1
    if "WARNING: Ignoring unknown variable" in cmd_stderr:
        logging.error("Unknown variable when parsing")
        cmd_return_code = 1
    return cmd_return_code, cmd_stderr


# Writes the requested SCAD code to the requested file, so OpenSCAD can be run on that code
def _write_scad_code_to_file(scad_code, scad_file):
    logging.info("Will run SCAD code '%s'" % scad_code)
    file = open(scad_file, 'w')
    file.write(scad_code)
    file.close()


# Runs OpenSCAD to generate an STL based on the code proposed
#
# scad_code: The code to be rendered
# scad_file: Filename to be used to write the code before rendering
# output_file: Filename where to store the rendered STL file
#
# Returns the exit status of the openscad command and the logs printed to stderr
def render_stl(scad_code, scad_file, output_file):
    _write_scad_code_to_file(scad_code, scad_file)
    return _run_openscad(scad_file, output_file)


# Checks if the object in STL file f1 contains the object in STL file f2
def _stl_contains_stl(f1, f2, scad_file, output_file):
    # Create SCAD file for diff
    _write_scad_code_to_file("difference() { import(\"%s\"); import(\"%s\");}" % (f1, f2), scad_file)

    # Use OpenSCAD to diff
    #
    # If f1 contains f2, then the resulting STL has no model, hence openscad return with exit code non-zero.
    # If f1 doesn't contain f2, then there is a residual model and the openscad run returns exit code 0
    openscad_return_code, openscad_stderr = _run_openscad(scad_file, output_file)
    if openscad_return_code > 0 and "Current top level object is empty" in openscad_stderr:
        return True
    for line in openscad_stderr.split("\\n"):
        logging.error(line)
    return False


# Compares the 2 provided STLs, returns True if they are different
#
# expected_stl, actual_stl: Files containing the 2 STLs to be compared
# scad_file: File where to write the scad code that will be used to diff the provided STL files
# new_parts_stl: File where to store an STL with parts that exist in actual_stl, but don't in expected_stl
# missing_parts_stl: File where to store an STL with parts that exist in expected_stl, but don't in actual_stl
def diff_stls(expected_stl, actual_stl, scad_file, new_parts_stl, missing_parts_stl):
    logging.info("Comparing STL in %s with expected value in %s", actual_stl, expected_stl)
    logging.info("Looking for new areas in the STL")
    if not _stl_contains_stl(actual_stl, expected_stl, scad_file, new_parts_stl):
        logging.error("New areas located in the STL")
        return True
    logging.info("Looking for missing areas in the STL")
    if not _stl_contains_stl(expected_stl, actual_stl, scad_file, missing_parts_stl):
        logging.error("Missing areas in the STL")
        return True
    return False
