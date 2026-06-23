load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "pyproject.toml",
    "requirements.in",
    "skel.permissions",
])

# --- runtime skeleton (init.d, gunicorn.conf, rc.d link) -------------------
pkg_files(
    name = "skel",
    srcs = glob(
        ["skel/**/*"],
        exclude = ["skel/etc/init.d/*"],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = glob(["skel/etc/init.d/*"]),
    attributes = pkg_attributes(mode = "0755"),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "10-orbvis-backend",
    link_name = "skel/etc/rc.d/10-orbvis-backend",
    target = "../init.d/orbvis-backend",
)

pkg_tar(
    name = "omd_skel_tar",
    srcs = [
        ":10-orbvis-backend",
        ":skel",
        ":skel_755",
    ],
    visibility = ["//omd:__pkg__"],
)

# --- python package --------------------------------------------------------
py_library(
    name = "cmk-orbvis-backend",
    srcs = glob(["cmk/orbvis_backend/**/*.py"]),
    data = glob(
        ["cmk/orbvis_backend/**/*"],
        exclude = ["cmk/orbvis_backend/**/*.py"],
    ),
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("bcrypt"),
        requirement("defusedxml"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("pydantic"),
        requirement("python-multipart"),
        requirement("uvicorn"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-orbvis-backend",
    strip_path_prefixes = ["packages/cmk-orbvis-backend"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [":cmk-orbvis-backend"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = ":wheel",
)

py_requirements_test(
    name = "requirements_test",
    src = "pyproject.toml",
    requirements = "requirements.in",
)
