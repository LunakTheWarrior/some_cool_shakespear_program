"""Compile a Shakespeare play with the original SPL-to-C compiler."""

load("@rules_cc//cc:cc_binary.bzl", "cc_binary")

def _spl_translate_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".c")
    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        tools = [ctx.executable._compiler],
        outputs = [output],
        command = '"$1" < "$2" > "$3"',
        arguments = [ctx.executable._compiler.path, ctx.file.src.path, output.path],
        mnemonic = "ShakespeareCompile",
        progress_message = "Translating Shakespeare play %{input}",
    )
    return [DefaultInfo(files = depset([output]))]

spl_translate = rule(
    implementation = _spl_translate_impl,
    attrs = {
        "src": attr.label(allow_single_file = [".spl"], mandatory = True),
        "_compiler": attr.label(
            default = "//third_party/spl:spl2c",
            executable = True,
            cfg = "exec",
        ),
    },
)

def spl_binary(name, src, **kwargs):
    """Translate SPL into C and link a native executable with the SPL runtime."""
    spl_translate(name = name + "_c", src = src)
    cc_binary(
        name = name,
        srcs = [":" + name + "_c"],
        deps = ["//third_party/spl:runtime"],
        **kwargs
    )
