load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "orbvis",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    # NOTE: deps are completed/validated at merge time in the Checkmk monorepo
    # (Bazel is not run from this staging tree). The Monitor/Setup integration
    # added imports of cmk.gui.pages, cmk.gui.watolib.main_menu, cmk.gui.header,
    # cmk.gui.page_menu, cmk.gui.breadcrumb, cmk.gui.main_menu, cmk.ccc.site and
    # cmk.shared_typing.main_menu; the sidebar snapin dep was dropped.
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/utils:paths",
    ],
)
