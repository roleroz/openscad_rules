srcs_attrs = attr.label_list(
    mandatory = True,
    allow_empty = False,
    allow_files = [".scad"],
    doc = "Filenames for the files that are included in this rule",
)

deps_attrs = attr.label_list(
    mandatory = False,
    allow_empty = True,
    providers = [DefaultInfo],
    doc = "Other libraries that the files on this rule depend on",
)

def _scad_library_impl(ctx):
    files = depset(ctx.files.srcs, transitive = [dep[DefaultInfo].files for dep in ctx.attr.deps])
    return [DefaultInfo(
        files = files,
        runfiles = ctx.runfiles(
            files = files.to_list(),
            collect_data = True,
        ),
    )]

scad_library = rule(
    implementation = _scad_library_impl,
    attrs = {
        "srcs": srcs_attrs,
        "deps": deps_attrs,
    },
    doc = "Group of files that will help define OpenSCAD files",
)

def _scad_object_impl(ctx):
    stl_output = ctx.actions.declare_file(ctx.label.name + ".stl")
    stl_inputs = ctx.files.srcs
    deps = []
    for one_transitive_dep in [dep[DefaultInfo].files for dep in ctx.attr.deps]:
        deps += one_transitive_dep.to_list()
    ctx.actions.run_shell(
        outputs = [stl_output],
        inputs = stl_inputs + deps,
        command = "openscad --export-format=stl -o {} {}".format(
            stl_output.path,
            " ".join([f.path for f in stl_inputs]),
        ),
    )
    files = depset(ctx.files.srcs + [stl_output], transitive = [dep[DefaultInfo].files for dep in ctx.attr.deps])
    return [DefaultInfo(
        files = files,
        runfiles = ctx.runfiles(
            files = files.to_list(),
            collect_data = True,
        ),
    )]

scad_object = rule(
    implementation = _scad_object_impl,
    attrs = {
        "srcs": srcs_attrs,
        "deps": deps_attrs,
    },
    doc = "Generator for OpenSCAD objects",
)

def scad_test(
        name,
        file_under_test,
        tests,
        deps,
        assertions = []):
    # Get a base label to create all other relative ones to this
    test_label = Label("//%s:%s" % (native.package_name(), name))

    deps_label = []
    for dep in deps:
        deps_label += [test_label.relative(dep)]
    expected_stls_label = []
    expected_stls_filenames = []
    testcases = []
    rendercases = []
    for scad_cmd, expected_stl in tests.items():
        scad_cmd = scad_cmd.replace("(", "\\(").replace(")", "\\)")
        expected_stl_label = test_label.relative(expected_stl)
        testcases += ["--testcases %s#$(rootpath %s)" % (scad_cmd, expected_stl_label)]
        rendercases += ["--render_cases %s#%s" % (scad_cmd, expected_stl)]
        if not expected_stl_label in expected_stls_label:
            expected_stls_label += [expected_stl_label]
            expected_stls_filenames += [expected_stl]
    file_under_test_label = test_label.relative(file_under_test)
    assertions_flag = []
    for assertion in assertions:
        assertions_flag += ["--assertion_check %s" % assertion]

    native.sh_test(
        name = name,
        size = "medium",
        srcs = ["//bazel_tools:scad_unittest_script.sh"],
        data = expected_stls_label + [Label("//bazel_tools:scad_unittest"), file_under_test_label] + deps_label,
        args = [
            "--scad_file_under_test $(rootpath %s)" % file_under_test_label,
            " ".join(testcases),
            " ".join(assertions_flag),
            "--scad_code_file scad.code",
            "--render_stl render.stl",
            "--new_parts_stl new_parts.stl",
            "--missing_parts_stl missing_parts.stl",
        ],
    )

    # Create a genrule to re-generate the expected STLs with the current library implementation
    # Command to render the STLs
    render_cmd = "$(execpath //bazel_tools:scad_render) --scad_file_under_test $(rootpath %s) %s --output_basedir $(RULEDIR);" % (
        file_under_test_label,
        " ".join(rendercases),
    )

    # Command to print a command that the user can use to copy the generated files into testdata
    cp_cmd = (
        "echo To update the expected STLs for this test go to the workspace directory and run:;" +
        "echo 'for file in %s; do cp bazel-bin/%s/$${file} %s/$${file}; chmod 666 %s/$${file}; done'" % (
            " ".join(expected_stls_filenames),
            native.package_name(),
            native.package_name(),
            native.package_name(),
        )
    )
    native.genrule(
        name = "%s_render" % name,
        outs = expected_stls_filenames,
        srcs = [
            file_under_test_label,
        ] + deps_label,
        exec_tools = ["//bazel_tools:scad_render"],
        cmd = render_cmd + "echo;echo;echo;" + cp_cmd,
    )
