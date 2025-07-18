from utils.build_config import Compiler, Bitness
from utils.run_command import run_command, Stdout, wrap_command_with_vcvarsall, CommandError, CommandTimeout
from utils import windows_only, EnvPath
import xml.etree.ElementTree as XmlElementTree
import multiprocessing
from pathlib import Path
import os
import re

class CompilationFailedError(Exception):
    pass

def compile_with_cmake(config, build_dir, targets, additional_env={}, additional_paths=[], additional_ld_library_paths=[]):
    build_type_args = ""
    if config.compiler == Compiler.VisualStudio:
        build_type_args = f"--config {config.build_type}"

    command = f'cmake --build "{build_dir}" --target {targets} {build_type_args}'
    try:
        run_command(command, paths=additional_paths, env=additional_env, ld_library_paths=additional_ld_library_paths)
    except CommandError:
        raise CompilationFailedError("Compilation failed")

def compile_with_ninja(target, build_dir):
    command = f"ninja -C {build_dir} {target}"
    try:
        run_command(command)
    except CommandError:
        raise CompilationFailedError("Compilation failed")

@windows_only
def compile_with_msbuild(msbuild_path, config, solution_path, targets, env={}, timeout_seconds=None, print_stdout=True):
    # Target name is not always equal to project name shown in VS. It can be taken from .metaproj file that can be
    # generated by extract_target_names_from_msbuild_metaproj() function.
    build_type = str(config.build_type)
    match config.bitness:
        case Bitness.x32:
            bitness = "Win32"
        case Bitness.x64:
            bitness = "x64"
        case _:
            raise KeyError("Unsupported bitness")

    command = f"{msbuild_path} {solution_path} /p:Configuration={build_type} /p:Platform={bitness}"
    for target in targets:
        command += f" /target:{target}"
    try:
        stdout = Stdout.print_to_console() if not print_stdout else Stdout.ignore()
        run_command(command, env=env, timeout_seconds=timeout_seconds, stdout=stdout, stderr=stdout)
    except CommandError:
        raise CompilationFailedError("Compilation failed")

def compile_with_make(target="",
                      directory=None,
                      *,
                      additional_paths=[],
                      additional_env={},
                      all_cores=True,
                      verbose=False):
    parallelism_arg = ""
    if all_cores:
        parallelism_arg = f"-j{multiprocessing.cpu_count()}"

    env = additional_env.copy()
    if verbose:
        env["VERBOSE"] = "1"

    command = f"make {target} {parallelism_arg}"
    run_command(command, env=env, paths=additional_paths, cwd=directory)

@windows_only
def compile_with_nmake(target="",
                            directory=None,
                            vc_varsall_path=None,
                            additional_paths=[],
                            additional_env={},
                            verbose=False):
    # jom is an nmake clone that can build in parallel.
    # Fall back to nmake if it's not available.
    jom_path = EnvPath("JOM_PATH", required=False, is_directory=False)
    nmake_path = jom_path.get()
    if not nmake_path:
        nmake_path = "nmake"

    command = f"{nmake_path} {target}"
    if vc_varsall_path is not None:
        command = wrap_command_with_vcvarsall(vc_varsall_path, command, verbose)

    run_command(command, env=additional_env, paths=additional_paths, cwd=directory)

@windows_only
def extract_target_names_from_msbuild_metaproj(msbuild_path, config, solution_path, env={}, cleanup_root_dir=None):
    """
    Project names shown by the Visual Studio IDE are not what MSBuild expects when building from commandline. Their
    MSBuild counterparts are called targets. This function extract targets from .sln file.
    """

    # First build with MSBuildEmitSolution=1 to produce .sln.metaproj files.
    # See https://stackoverflow.com/questions/13915636/specify-project-file-of-a-solution-using-msbuild/40372894#40372894
    env["MSBuildEmitSolution"] = 1
    timeout_seconds = 2
    try:
        compile_with_msbuild(msbuild_path, config, solution_path, [], env, timeout_seconds, print_stdout=False)
    except CommandTimeout:
        pass

    # Open generated .sln.metaproj file as an XML document.
    metaproj_path = Path(solution_path)
    metaproj_path = metaproj_path.with_suffix(metaproj_path.suffix + ".metaproj")
    root_node = XmlElementTree.parse(metaproj_path).getroot()

    # Parse the XML to a dict - keys are project names visible in VS, values are target names for MSBuild
    target_mapping = {}
    for target_node in root_node.findall('{*}Target'):
        target_name = target_node.attrib['Name']

        # Skip targets with colons, because they are special targets for cleaning, rebuilding and publishing
        if ':' in target_name:
            continue

        # Get <MSBuild> tag
        msbuild_node = target_node.find("{*}MSBuild")
        if msbuild_node is None:
            continue

        # Get "Condition" attrib in <MSBuild> and match it to extract metaproj path of the target
        if "Condition" not in msbuild_node.attrib:
            continue
        condition = msbuild_node.attrib['Condition']
        condition_match = re.match(r"'%\(ProjectReference.Identity\)' == '(.*)'", condition)
        if condition_match is None:
            continue

        # Extract project name as shown in VS. Note that this method is not ideal, because it can be be different,
        # but it it will usually work and fully parsing it would be to much of a hassle. To properly parse we would
        # have to:
        #  - take metaproj path from the "Condition" attrib
        #  - open metaproj, find .vcxproj
        #  - open .sln, find line where .vcxproj is defined and extract the name
        vs_name = target_name
        slash_pos = vs_name.rfind('\\')
        if slash_pos != -1:
            vs_name = vs_name[slash_pos+1:]

        # Write entry to the dict
        target_mapping[vs_name] = target_name

    # Dump the dict as Python code.
    print("{")
    for vs_name, target_name in target_mapping.items():
        print(f'    "{vs_name}": r"{target_name}",')
    print("}")

    # Optionally cleanup generated .metaproj files
    if cleanup_root_dir is not None:
        for root, _, files in os.walk(cleanup_root_dir):
            for file_name in files:
                file = Path(root) / file_name
                extension = ''.join(file.suffixes)
                if extension in ['.sln.metaproj', '.sln.metaproj.tmp', '.vcxproj.metaproj', '.vcxproj.metaproj.tmp']:
                    file.unlink(missing_ok=False)
