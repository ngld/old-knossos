"""
Build tasks for the Knossos / Nebula project

This file is written in Starlark a subset of Python.
A full specification can be found here: https://github.com/google/starlark-go/blob/master/doc/spec.md

Quick API reference:
  option(name, default): returns a command line option
  resolve_path(some, path, parts): joins the given path elements and resolves any special syntax (like "//")
  prepend_path(path): prepends the given path to the OS $PATH variable (only affects tasks launched from this script)
  getenv(name): returns the value of the given environment var
  setenv(name, value): overrides the given environment variable for any process launched from this script
  task(name, ...): define a new target

Path help:
  resolve_path(...)
    any path passed to this function is assumed to be relative to this script
    // is an alias for the project root which currently is just the directory that contains this script

  task(...):
    any option that contains paths is automatically processed by resolve_path() and thus follows the same rules

Task help:
  desc: a description; only displayed in the CLI help
  deps: a list of targets which should be run (if necessary) before this task
  base: working directory; all other paths specified in this task are relative to this path
  skip_if_exists: a list of files; if this task is called as a dependency of another task and at least one of the
    listed files exists, this task is skipped
  inputs: a list of files
  outputs: a list of files; if this task is called as a dependency of another task and all outputs exist and are newer
    than the input files, this task is skipped
  cmds: a list of commands to execute
    the following types are allowed as list items:
      string: Will be interpreted as a shell script. Bash syntax is supported (even on Windows)
      tuple: a list of command arguments the first item which does not contain a "=" is the command that should be run
        all items preceeding it are env vars which should be set for this sub process
        all items after the command are arguments which are passed as-is (no globs, shell expansion, etc)
      task: a reference to another task which will be called at exactly this point
"""

build = option("build", "Release", help = "Whether to build a Debug or Release build")
msys2_path = option("msys2_path", "//third_party/msys2", help = "The path to your MSYS2 installation. Only used on Windows. " +
                                                                "Defaults to the bundled MSYS2 directory")
generator_opt = option("generator", "", help = "The CMake generator to use. Defaults to ninja if available. " +
                                               "Please note that on Windows you'll  have to run the vcvarsall.bat if you don't choose a Visual Studio generator")
kn_args = option("args", "", help = "The parameters to pass to Knossos in the client-run target")

yarn_path = resolve_path(read_yaml(".yarnrc.yml", "yarnPath"))

def yarn(*args):
    if len(args) == 1 and type(args[0]) == "string":
        args = tuple(args[0].split(" "))

    return ("node", yarn_path) + args

def configure():
    generator = generator_opt

    if build not in ("Debug", "Release"):
        error("Invalid build mode %s passed. Only Debug or Release are valid." % build)

    if OS == "windows":
        libext = ".dll"
        binext = ".exe"

        prepend_path(resolve_path(msys2_path, "mingw64/bin"))
        setenv("GCCPATH", str(resolve_path(msys2_path, "mingw64/bin/gcc.exe")))

        #prepend_path(resolve_path(msys2_path, "mingw64/lib/ccache/bin"))
        prepend_path("third_party/ninja")

        compiler = getenv("CXX")
        if compiler == "":
            # user didn't specify a compiler, let's make sure we have a valid compiler
            if getenv("LIB") == "":
                # VC vars aren't set, run vcvarsall.bat to fix that
                info("Calling vcvarsall.bat")
                load_vcvars("amd64")

            # TODO Figure out how to properly disable /MP in the client package
            #if execute("clang-cl /?") != False:
            #    info("Using auto-detected clang-cl")

            #    setenv("CC", "clang-cl")
            #    setenv("CXX", "clang-cl")
            if execute("cl /?") != False:
                info("Using auto-detected cl")

                setenv("CC", "cl")
                setenv("CXX", "cl")
            else:
                error("No usable compiler found. CMake will fall back to gcc and fail under these circumstances")

        if generator == "":
            # ninja is always available because we download it in our fetch-deps step
            generator = "Ninja"

        info("Using MSYS2 installation at %s." % resolve_path(msys2_path))

    elif OS == "darwin":
        libext = ".dylib"
        binext = ""

        if generator == "":
            if execute("ninja -h") != False:
                generator = "Ninja"
            else:
                generator = "Unix Makefiles"

        if isdir("/usr/local/opt/ccache/libexec"):
            prepend_path("/usr/local/opt/ccache/libexec")
            info("Using ccache at /usr/local/opt/ccache/libexec")
    else:
        libext = ".so"
        binext = ""

        if generator == "":
            if execute("ninja -h") != False:
                generator = "Ninja"
            elif execute("ninja-build -h") != False:
                # TODO fix the hard references to ninja's name
                warn("Expected ninja to be available as ninja, not ninja-build, falling back to make")
                generator = "Unix Makefiles"
            else:
                generator = "Unix Makefiles"

    prepend_path("third_party/go/bin")
    prepend_path("third_party/protoc-dist")
    prepend_path("third_party/nodejs/bin")
    prepend_path(".tools")

    task(
        "build-tool",
        desc = "Build our build tool",
        inputs = [
            "packages/build-tools/**/*.go",
            "packages/libknossos/pkg/archives/*.go",
        ],
        outputs = [
            ".tools/tool%s" % binext,
        ],
        cmds = [
            "cd packages/build-tools",
            "go build -o ../../.tools/tool%s" % binext,
        ],
    )

    extra_tools = []
    if OS == "windows" and getenv("CI") == "":
        extra_tools = [
            "cd packages/build-tools",
            "go build -o ../../.tools/gcc%s ./ccache-helper" % binext,
        ]

    task(
        "install-tools",
        desc = "Installs necessary go tools in the workspace (task, pggen, protoc plugins, ...)",
        deps = ["build-tool"],
        inputs = ["packages/build-tools/tools.go", "packages/build-tools/go.mod", "packages/build-tools/ccache-helper/main.go"],
        outputs = [".tools/%s%s" % (name, binext) for name in ("modd", "pggen", "protoc-gen-go", "protoc-gen-twirp")],
        cmds = ["tool install-tools"] + extra_tools,
    )

    js_deps = task(
        "yarn-install",
        hidden = True,
        inputs = [
            "package.json",
            "yarn.lock",
        ],
        outputs = [
            ".yarn/cache/*.zip",
            ".pnp.js",
        ],
        cmds = [yarn("install")],
    )

    task(
        "fetch-deps",
        desc = "Automatically downloads dependencies not covered by install-tools",
        deps = ["build-tool"],
        cmds = [
            "tool fetch-deps",
            js_deps,
        ],
    )

    task(
        "update-deps",
        desc = "Update the checksums listed in DEPS.yml (only use this if you manually changed that file)",
        deps = ["build-tool"],
        cmds = ["tool fetch-deps -u"],
    )

    task(
        "check-deps",
        desc = "Checks the dependencies listed in DEPS.yml for updates",
        deps = ["build-tool"],
        cmds = ["tool check-deps"],
    )

    if OS == "windows":
        task(
            "bootstrap-mingw64",
            desc = "Runs first-time setup for MSYS2",
            deps = ["fetch-deps"],
            base = msys2_path,
            skip_if_exists = ["mingw64/bin/gcc.exe"],
            cmds = [
                'usr/bin/bash --login -c "mkdir /tmp || true"',
                'usr/bin/bash --login -c "pacman -Syuu --noconfirm"',
                'usr/bin/bash --login -c "pacman -Syuu --noconfirm"',
                'usr/bin/bash --login -c "pacman -Su --noconfirm --needed mingw-w64-x86_64-{gcc,ccache}"',
            ],
        )

    task(
        "proto-build",
        desc = "Generates TS and Go bindings from the .proto API definitions",
        deps = ["fetch-deps", "install-tools"],
        base = "packages/api",
        inputs = ["definitions/*.proto"],
        outputs = [
            "api/**/*.{ts,go}",
            "client/**/*.go",
        ],
        cmds = [
            "protoc -Idefinitions mod.proto --go_out=client --go_opt=paths=source_relative",
            "protoc -Idefinitions client.proto --go_out=client --go_opt=paths=source_relative --twirp_out=twirp",
            "protoc -Idefinitions service.proto --go_out=api --go_opt=paths=source_relative --twirp_out=twirp",
            # twirp doesn't support go.mod paths so we have to move the generated files to the correct location
            "mv twirp/github.com/ngld/knossos/packages/api/api/*.go api",
            "mv twirp/github.com/ngld/knossos/packages/api/client/*.go client",
            "rm -r twirp/github.com",
            yarn("protoc google/protobuf/timestamp.proto --ts_opt long_type_number --ts_out=api"),
            yarn("protoc -Idefinitions mod.proto --ts_opt long_type_number --ts_out=api"),
            yarn("protoc -Idefinitions client.proto --ts_opt long_type_number --ts_out=api"),
            yarn("protoc -Idefinitions service.proto --ts_opt long_type_number --ts_out=api"),
        ],
    )

    task(
        "server-build",
        desc = "Compiles the Nebula server code",
        deps = ["proto-build"],
        inputs = [
            "packages/server/cmd/**/*.go",
            "packages/server/pkg/**/*.go",
        ],
        outputs = ["build/nebula%s" % binext],
        cmds = [
            "cd packages/server",
            "go generate -x ./pkg/db/queries.go",
            "go build -o ../../build/nebula%s ./cmd/server/main.go" % binext,
        ],
    )

    task(
        "front-build",
        desc = "Builds the assets for Nebula's frontend",
        base = "packages/front",
        inputs = ["src/**/*.{ts,tsx,js,css}"],
        outputs = [
            "dist/prod/**/*.{html,css,js}",
        ],
        cmds = [
            ("NODE_ENV=production",) + yarn("postcss src/tw-index.css -o gen/tw-index.css"),
            yarn("webpack --env production --color --progress"),
        ],
    )

    task(
        "client-ui-css",
        desc = "Compiles Tailwind CSS for Knossos (only rarely necessary)",
        base = "packages/client-ui",
        inputs = [
            "src/tw-index.css",
            "tailwind.config.js",
        ],
        outputs = [
            "gen/tw-index.css",
        ],
        cmds = [yarn("postcss src/tw-index.css -o gen/tw-index.css")],
    )

    res_dir = ""
    if OS == "darwin":
        res_dir = "knossos.app/Contents/Frameworks/Chromium Embedded Framework.framework/Resources/"

    task(
        "client-ui-build",
        desc = "Builds the assets for Nebula's client UI",
        deps = ["build-tool", "fetch-deps"],
        base = "packages/client-ui",
        inputs = ["src/**/*.{ts,tsx,js,css}"],
        outputs = ["../../build/client/launcher/%s/%sui.kar" % (build, res_dir)],
        cmds = [
            ("NODE_ENV=production",) + yarn("postcss src/tw-index.css -o gen/tw-index.css"),
            yarn("webpack --env production --color --progress"),
            'tool pack-kar "../../build/client/launcher/%s/%sui.kar" dist/prod' % (build, res_dir),
        ],
    )

    task(
        "client-ui-watch",
        hidden = True,
        deps = ["fetch-deps"],
        base = "packages/client-ui",
        cmds = [yarn("client:watch")],
    )

    if OS == "windows":
        task(
            "libarchive-build",
            desc = "Builds libarchive with CMake (uses MSYS2)",
            deps = ["fetch-deps", "bootstrap-mingw64"],
            inputs = ["third_party/libarchive/libarchive/**/*.{c,h}"],
            outputs = ["build/libarchive/bin/libarchive.dll"],
            env = {
                # make sure CMake uses MSYS2's GCC
                "CC": "gcc",
                "CXX": "g++",
            },
            cmds = [
                ("cd", resolve_path(msys2_path)),
                ("usr/bin/bash", "--login", "-c", '"$(cygpath "%s")"' % resolve_path("packages/libarchive/msys2-build.sh")),
            ],
        )
    else:
        task(
            "libarchive-build",
            desc = "Builds libarchive with CMake",
            deps = ["fetch-deps"],
            inputs = ["third_party/libarchive/src/**/*.{c,h}"],
            outputs = ["build/libarchive/libarchive/libarchive.a"],
            cmds = [
                "cd packages/libarchive",
                "bash ./unix-build.sh",
            ],
        )

    task(
        "libknossos-build",
        desc = "Builds libknossos (client-side, non-UI logic)",
        deps = ["build-tool", "proto-build", "libarchive-build"],
        base = "packages/libknossos",
        inputs = [
            "../../.tools/tool%s" % binext,
            "**/*.go",
            "../libarchive/**/*.go",
        ],
        outputs = [
            "../../build/libknossos/libknossos%s" % libext,
            "../../build/libknossos/dynknossos.{h,cc}",
        ],
        env = {
            # cgo only supports gcc, make sure it doesn't try to use a compiler meant for our other packages
            "CC": "gcc",
        },
        cmds = [
            "go build -o ../../build/libknossos/libknossos%s -buildmode c-shared ./api" % libext,
            "tool gen-dyn-loader ../../build/libknossos/libknossos.h ../../build/libknossos/dynknossos.h",
        ],
    )

    if generator == "Ninja":
        build_cmd = "ninja knossos"
    elif generator == "Unix Makefiles":
        build_cmd = "make -j4 knossos"
    else:
        build_cmd = "cmake --build ."

    task(
        "client-build",
        desc = "Builds the Knossos client",
        deps = ["libarchive-build", "libknossos-build"],
        cmds = [
            """
    if [ ! -d build/client ]; then
        mkdir -p build/client
    fi

    cd build/client
    if [ ! -f CMakeCache.txt ] || [ ! -f ../../compile_commands.json ]; then
        cmake -G"{generator}" -DCMAKE_BUILD_TYPE={build} -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ../../packages/client
        mv compile_commands.json ../..
    fi
    """.format(generator = generator, build = build),
            build_cmd,
        ],
    )

    if OS == "darwin":
        kn_bin = "./launcher/%s/knossos.app/Contents/MacOS/knossos" % build
    else:
        kn_bin = "./launcher/%s/knossos" % build

    task(
        "client-run",
        desc = "Launches Knossos",
        deps = ["client-build", "client-ui-build"],
        base = "build/client",
        cmds = ["%s %s" % (kn_bin, kn_args)],
    )

    libkn_path = resolve_path("build/libknossos/libknossos%s" % libext)
    task(
        "client-run-dev",
        hidden = True,
        base = "build/client",
        deps = ["client-build"],
        cmds = ['%s --url="http://localhost:8080/" --libkn="%s"' % (kn_bin, libkn_path)],
    )

    task(
        "client-watch",
        desc = "Launch Knossos, recompile and restart after source changes",
        # run fetch-deps before we launch modd to make sure that it doesn't trigger
        # two parallel fetch-deps tasks
        deps = ["install-tools", "fetch-deps"],
        cmds = ["modd -f modd_client.conf"],
    )

    task(
        "clean",
        desc = "Delete all generated files",
        deps = ["build-tool"],
        cmds = [
            "rm -rf build/*",
            "rm -f packages/api/api/**/*.{ts,go}",
            "rm -f packages/api/client/**/*.go",
            "rm -rf packages/{client-ui,front}/dist",
            "rm -f packages/{cleint-ui,front}/gen/*",
        ],
    )

    for name in ("libknossos", "client"):
        task(
            "%s-clean" % name,
            desc = "Delete all generated files from the %s package" % name,
            deps = ["build-tool"],
            cmds = [
                "rm -rf build/%s" % name,
            ],
        )
