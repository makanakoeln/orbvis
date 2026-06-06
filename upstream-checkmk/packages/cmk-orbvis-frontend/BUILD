# Bazel targets for the built-in OrbVis frontend bundle, modelled 1:1 on
# packages/cmk-frontend-vue/BUILD. Buildable only inside the checkmk
# monorepo (needs @npm, @rules_pkg, the pnpm workspace entry and the
# sibling cmk-frontend-vue + cmk-frontend packages); see README.md for
# the merge-time wiring checklist.

load("@aspect_rules_js//js:defs.bzl", "js_binary", "js_run_binary")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//packages/cmk-orbvis-frontend:vite/package_json.bzl", vite_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["package.json"])

npm_link_all_packages(name = "node_modules")

SRCS = glob([
    "src/**/*.ts",
    "src/**/*.vue",
    "src/**/*.css",
    "src/**/*.svg",
    "src/**/*.json",
]) + [
    "index.html",
    "package.json",
    "tsconfig.json",
    "vite.config.ts",
] + glob(["public/**"])

# de.po is the translation source of truth; the JSON catalogs under
# src/assets/locale/ are generated from it at build time (mirrors
# cmk-frontend-vue's :compile_i18n).
js_binary(
    name = "gettext-compile",
    entry_point = ":node_modules/vue3-gettext/dist/bin/gettext_compile.js",
)

js_run_binary(
    name = "compile_i18n",
    srcs = [
        "gettext.config.js",
        "locale/de.po",
        ":node_modules/vue3-gettext",
    ],
    outs = ["src/assets/locale/de.json"],
    tool = ":gettext-compile",
    visibility = ["//visibility:private"],
)

vite_bin.vite(
    name = "dist",
    srcs = SRCS + [
        ":compile_i18n",
        ":node_modules",
        "//packages/cmk-frontend-vue:src_ts",
        "//packages/cmk-frontend-vue:src_vue",
        "//packages/cmk-frontend:dist",
    ],
    args = ["build"],
    chdir = package_name(),
    out_dirs = ["dist"],
)

# Ship the SPA as static files; the per-site Apache config (written by
# the OrbVis backend setup) serves them at /<site>/orbvis/.
pkg_files(
    name = "orbvis_frontend_dist_pkg",
    srcs = [":dist"],
    prefix = "share/check_mk/web/htdocs/cmk-orbvis-frontend",
    strip_prefix = "dist",
)

pkg_tar(
    name = "cmk-orbvis-frontend",
    srcs = [":orbvis_frontend_dist_pkg"],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)
