load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "orbvis",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/orbvis"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/orbvis",
        "//cmk/gui/sidebar/_snapin:snapin_registry",
        "//cmk/gui/utils:output_funnel",
        "//cmk/utils:paths",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
