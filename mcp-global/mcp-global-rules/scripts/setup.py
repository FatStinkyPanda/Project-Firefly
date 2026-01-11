"""
MCP Setup Commands
==================
Install hooks, profiles, and configure MCP.

Usage:
    python mcp.py setup --hooks     # Install git hooks
    python mcp.py setup --profile   # Install shell profile
    python mcp.py setup --all       # Full setup
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys

from .utils import Console, find_project_root, get_package_root
import importlib
import stat


def install_dependencies() -> int:
    """Install required Python dependencies."""
    Console.info("Checking dependencies...")

    # Detect NVIDIA GPU
    has_gpu = False
    try:
        subprocess.run(['nvidia-smi'], capture_output=True, check=True)
        has_gpu = True
        Console.ok("NVIDIA GPU detected, will use faiss-gpu")
    except (subprocess.CalledProcessError, FileNotFoundError):
        Console.info("No NVIDIA GPU detected, using faiss-cpu fallback")

    faiss_pkg = 'faiss-gpu' if has_gpu else 'faiss-cpu'
    dependencies = [faiss_pkg, 'watchdog']

    for dep in dependencies:
        # Check for faiss generically but verify GPU support if needed
        is_faiss = 'faiss' in dep
        check_name = 'faiss' if is_faiss else dep.replace('-', '_')

        try:
            # Check if already installed
            module = importlib.import_module(check_name)

            # Special check for FAISS GPU support
            if dep == 'faiss-gpu':
                try:
                    import faiss
                    if faiss.get_num_gpus() > 0:
                        Console.ok(f"Dependency already satisfied: {dep} (GPU support verified)")
                        continue
                    else:
                        Console.warn("FAISS installed but NO GPU support found. Upgrading to faiss-gpu...")
                        raise ImportError("No GPU support")
                except Exception:
                    raise ImportError("FAISS GPU check failed")
            else:
                Console.ok(f"Dependency already satisfied: {dep}")
                continue
        except ImportError:
            Console.info(f"Installing missing dependency: {dep}...")
            # If we're installing faiss-gpu, ensure faiss-cpu is gone to avoid conflicts
            if dep == 'faiss-gpu':
                subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'faiss-cpu'], capture_output=True)

            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
                Console.ok(f"Successfully installed {dep}")
            except Exception as e:
                if dep == 'faiss-gpu':
                    Console.warn(f"Failed to install faiss-gpu: {e}. Falling back to faiss-cpu...")
                    try:
                        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'faiss-cpu'])
                        Console.ok("Successfully installed faiss-cpu fallback")
                    except Exception as e2:
                        Console.fail(f"Failed to install faiss-cpu fallback: {e2}")
                        return 1
                else:
                    Console.fail(f"Failed to install {dep}: {e}")
                    return 1

    return 0


def install_git_hooks(project_root: Path = None) -> int:
    """Install MCP git hooks to a project."""
    project_root = project_root or find_project_root() or Path.cwd()

    # Find MCP installation
    # Find MCP installation
    mcp_root = get_package_root()
    hooks_source = mcp_root / '.git-hooks'

    if not hooks_source.exists():
        Console.fail(f"Hooks not found: {hooks_source}")
        return 1

    # Target
    git_hooks = project_root / '.git' / 'hooks'

    if not (project_root / '.git').exists():
        Console.fail("Not a git repository")
        return 1

    git_hooks.mkdir(parents=True, exist_ok=True)

    # Copy hooks
    hooks = ['pre-commit', 'post-commit', 'commit-msg', 'pre-push', 'post-checkout', 'post-merge']
    installed = 0

    for hook in hooks:
        source = hooks_source / hook
        target = git_hooks / hook

        if source.exists():
            shutil.copy2(source, target)
            # Make executable
            target.chmod(target.stat().st_mode | stat.S_IEXEC)
            installed += 1
            Console.ok(f"Installed: {hook}")

    Console.ok(f"Installed {installed} hooks to {git_hooks}")
    return 0


def install_shell_profile() -> int:
    """Install shell startup script to user profile."""
    mcp_root = get_package_root()

    home = Path.home()

    # Detect shell
    if os.name == 'nt':
        # PowerShell
        ps_profile = home / 'Documents' / 'PowerShell' / 'Microsoft.PowerShell_profile.ps1'
        ps_profile.parent.mkdir(parents=True, exist_ok=True)

        startup_script = mcp_root / 'scripts' / 'mcp-startup.ps1'

        if startup_script.exists():
            # Add source line to profile
            source_line = f'. "{startup_script}"'

            existing = ps_profile.read_text() if ps_profile.exists() else ""
            if source_line not in existing:
                with open(ps_profile, 'a') as f:
                    f.write(f"\n# MCP Integration\n{source_line}\n")
                Console.ok(f"Added to PowerShell profile: {ps_profile}")
            else:
                Console.ok("PowerShell profile already configured")
    else:
        # Bash/Zsh
        startup_script = mcp_root / 'scripts' / 'mcp-startup.sh'

        for rc_file in ['.bashrc', '.zshrc']:
            rc_path = home / rc_file
            if rc_path.exists():
                source_line = f'source "{startup_script}"'

                existing = rc_path.read_text()
                if source_line not in existing and str(startup_script) not in existing:
                    with open(rc_path, 'a') as f:
                        f.write(f"\n# MCP Integration\n{source_line}\n")
                    Console.ok(f"Added to {rc_file}")

    return 0


def install_ci_cd(project_root: Path = None) -> int:
    """Auto-create CI/CD if not exists."""
    project_root = project_root or find_project_root() or Path.cwd()

    # Check if CI already exists
    github_ci = project_root / '.github' / 'workflows' / 'ci.yml'
    gitlab_ci = project_root / '.gitlab-ci.yml'

    if github_ci.exists() or gitlab_ci.exists():
        Console.ok("CI/CD already configured")
        return 0

    # Check for .git
    if not (project_root / '.git').exists():
        Console.warn("Not a git repository, skipping CI setup")
        return 0

    # Generate GitHub Action
    try:
        from .cicd import write_github_action
        path = write_github_action(project_root)
        Console.ok(f"Created: {path}")
    except Exception as e:
        Console.warn(f"Could not create CI: {e}")

    return 0


def full_setup(project_root: Path = None) -> int:
    """Run full MCP setup."""
    project_root = project_root or find_project_root() or Path.cwd()

    Console.header("MCP Full Setup")

    # 0. Install dependencies
    Console.info("Verifying dependencies...")
    if install_dependencies() != 0:
        Console.fail("Dependency installation failed, aborting setup.")
        return 1

    # 1. Install hooks
    Console.info("Installing git hooks...")
    install_git_hooks(project_root)

    # 2. Install shell profile
    Console.info("Installing shell profile...")
    install_shell_profile()

    # 3. Create CI/CD
    Console.info("Setting up CI/CD...")
    install_ci_cd(project_root)

    # 4. Initial index
    Console.info("Building initial index...")
    try:
        from .index_all import run_all_indexes
        run_all_indexes(project_root, verbose=False)
    except Exception:
        Console.warn("Could not build initial index")

    # 5. Create .mcp directory
    mcp_dir = project_root / '.mcp'
    mcp_dir.mkdir(exist_ok=True)

    Console.ok("MCP setup complete!")
    print("\nNext steps:")
    print("  1. Restart your terminal to load shell integration")
    print("  2. Run 'mcp help' to see available commands")
    print("  3. Run 'mcp index-all' to build full indexes")

    return 0


def main():
    """CLI entry point."""
    Console.header("MCP Setup")

    if '--hooks' in sys.argv:
        return install_git_hooks()

    if '--profile' in sys.argv:
        return install_shell_profile()

    if '--ci' in sys.argv or '--cicd' in sys.argv:
        return install_ci_cd()

    if '--all' in sys.argv or len(sys.argv) <= 1:
        return full_setup()

    Console.info("Usage:")
    Console.info("  mcp setup --hooks     Install git hooks")
    Console.info("  mcp setup --profile   Install shell profile")
    Console.info("  mcp setup --ci        Create CI/CD pipeline")
    Console.info("  mcp setup --all       Full setup")

    return 0


if __name__ == "__main__":
    sys.exit(main())
