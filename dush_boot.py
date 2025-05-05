import platform
from pathlib import Path, PurePosixPath


is_windows = platform.system() == "Windows"
home = Path.home()
dush_path = Path(__file__).parent
dush_path_bash_on_windows = ""
symlink_dir = dush_path / "links"
pythonpath_separator=";" if is_windows else ":"

def convert_path_to_bash_compatible(path):
    if is_windows:
        drive = path.parts[0][0].lower()
        parts = path.parts[1:]
        return PurePosixPath("/", drive, *parts)
    else:
        return path

def create_profile_symlinks():
    symlink_dir.mkdir(exist_ok=True, parents=True)

    profiles = [
        (home / ".bash_profile", "bash_profile", False),
        (home / ".bashrc", "bashrc", False),
        (home / ".profile", "profile", False),
        (home / ".gitconfig", "gitconfig", False),
    ]
    if is_windows:
        profiles += [
            (home / "Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1", "powershell_profile.ps1", True)
        ]

    result = []
    for real_path, symlink_name, create_if_missing in profiles:
        symlink_path = symlink_dir / symlink_name
        symlink_path.unlink(missing_ok=True)

        if not real_path.exists():
            if create_if_missing:
                real_path.touch()
            else:
                continue

        symlink_path.symlink_to(real_path)
        result.append(f"{symlink_path} -> {real_path}")

    return '\n'.join(result)

def generate_sample_bash_profile():
    dush_path_bash = convert_path_to_bash_compatible(dush_path)

    return f"""\
PYTHONPATH="{dush_path_bash}{pythonpath_separator}$PYTHONPATH"
DUSH_PATH="{dush_path_bash}"
DUSH_WORKSPACE="{dush_path_bash.parent}"
DUSH_ENABLE_AUTOLOAD=1
. $DUSH_PATH/projects/bashies/main.sh
. $DUSH_PATH/projects/yuview/main.sh"""

def generate_sample_powershell_profile():
    return f"""\
$env:PYTHONPATH = "{dush_path}{pythonpath_separator}$env:PYTHONPATH"
$env:DUSH_WORKSPACE = "C:/develop"
$env:DUSH_PATH = "C:/develop/dush"
$env:DUSH_ENABLE_AUTOLOAD = $true
Import-Module $env:DUSH_PATH/projects/bashies/main.ps1
Import-Module $env:DUSH_PATH/projects/yuview/main.ps1"""

def print_section(name, content):
    expected_width = 80

    name = f" {name.strip()} "
    filler_count = expected_width - len(name)
    if filler_count > 0:
        filler_count_left = filler_count // 2
        filler_count_right = filler_count - filler_count_left
        header = ('#' * filler_count_left) + name + ('#' * filler_count_right)
    else:
        header = name

    footer = '#' * expected_width
    print(header)
    print(content)
    print(footer)
    print()
    print()
    print()

print_section("Symlinks to profiles", create_profile_symlinks())
print_section("Example Bash profile", generate_sample_bash_profile())
print_section("Example Powershell profile", generate_sample_powershell_profile())
