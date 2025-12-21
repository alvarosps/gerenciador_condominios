"""
Code Quality Metrics Generator for Condominios Manager

This script generates a comprehensive baseline report of code quality metrics
including:
- Lines of code (LOC)
- Cyclomatic complexity
- Maintainability index
- Flake8 violations
- Pylint score
- Security issues (Bandit)

The report is saved to the metrics/ directory with a timestamp.

Usage:
    python scripts/generate_metrics.py

Output:
    metrics/baseline_metrics_{timestamp}.txt

Author: Development Team
Date: 2025-10-19
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, description, ignore_errors=False):
    """
    Run a shell command and capture output.

    Args:
        cmd (str): Command to execute
        description (str): Description of what the command does
        ignore_errors (bool): Whether to ignore command errors

    Returns:
        str: Command output or error message
    """
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*80}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )

        if result.returncode != 0 and not ignore_errors:
            output = f"Command failed with exit code {result.returncode}\n"
            output += f"STDOUT:\n{result.stdout}\n"
            output += f"STDERR:\n{result.stderr}\n"
        else:
            output = result.stdout if result.stdout else result.stderr

        return output

    except Exception as e:
        return f"Error executing command: {e}"


def install_missing_tools():
    """Install required tools if not present"""
    print("Checking for required tools...")

    tools = {
        'radon': 'radon',
        'bandit': 'bandit',
    }

    for tool, package in tools.items():
        try:
            subprocess.run(
                f'{tool} --version',
                shell=True,
                capture_output=True,
                check=True
            )
            print(f"  ✓ {tool} is installed")
        except subprocess.CalledProcessError:
            print(f"  ✗ {tool} not found, installing...")
            subprocess.run(
                f'pip install {package}',
                shell=True,
                check=True
            )


def count_lines_of_code():
    """Count lines of code manually (alternative to cloc)"""
    output = "Lines of Code Analysis\n"
    output += "=" * 60 + "\n\n"

    core_dir = project_root / 'core'
    project_dir = project_root / 'condominios_manager'

    total_lines = 0
    total_files = 0

    for directory in [core_dir, project_dir]:
        if not directory.exists():
            continue

        output += f"\nDirectory: {directory.name}\n"
        output += "-" * 60 + "\n"

        for py_file in directory.rglob('*.py'):
            # Skip migrations
            if 'migrations' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    num_lines = len(lines)
                    total_lines += num_lines
                    total_files += 1
                    output += f"{py_file.name:40} {num_lines:6} lines\n"
            except Exception as e:
                output += f"{py_file.name:40} Error: {e}\n"

    output += "\n" + "=" * 60 + "\n"
    output += f"Total Files: {total_files}\n"
    output += f"Total Lines: {total_lines}\n"
    output += "=" * 60 + "\n"

    return output


def generate_metrics():
    """Generate all code quality metrics"""
    metrics_dir = project_root / 'metrics'
    metrics_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = metrics_dir / f'baseline_metrics_{timestamp}.txt'

    print("=" * 80)
    print("Condominios Manager - Code Quality Metrics Generator")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Report will be saved to: {report_file}")

    # Install missing tools
    install_missing_tools()

    # Open report file
    with open(report_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("CONDOMINIOS MANAGER - BASELINE CODE QUALITY METRICS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Phase: 0 - Pre-Refactoring Setup\n")
        f.write("=" * 80 + "\n\n")

        # 1. Lines of Code
        print("\n[1/6] Counting lines of code...")
        output = count_lines_of_code()
        f.write(output + '\n\n')
        print("✓ Lines of code counted")

        # 2. Flake8 Violations
        print("\n[2/6] Running Flake8...")
        output = run_command(
            'flake8 core condominios_manager --count --statistics',
            'Flake8 Code Quality Analysis',
            ignore_errors=True
        )
        f.write("=" * 80 + "\n")
        f.write("FLAKE8 VIOLATIONS\n")
        f.write("=" * 80 + "\n")
        f.write(output + '\n\n')
        print("✓ Flake8 analysis complete")

        # 3. Pylint Score
        print("\n[3/6] Running Pylint...")
        output = run_command(
            'pylint core --exit-zero',
            'Pylint Analysis',
            ignore_errors=True
        )
        f.write("=" * 80 + "\n")
        f.write("PYLINT ANALYSIS\n")
        f.write("=" * 80 + "\n")
        f.write(output + '\n\n')
        print("✓ Pylint analysis complete")

        # 4. Security Analysis (Bandit)
        print("\n[4/6] Running Bandit security scan...")
        output = run_command(
            'bandit -r core condominios_manager -f txt',
            'Security Analysis (Bandit)',
            ignore_errors=True
        )
        f.write("=" * 80 + "\n")
        f.write("SECURITY ANALYSIS (BANDIT)\n")
        f.write("=" * 80 + "\n")
        f.write(output + '\n\n')
        print("✓ Security scan complete")

        # 5. Cyclomatic Complexity
        print("\n[5/6] Calculating cyclomatic complexity...")
        output = run_command(
            'radon cc core condominios_manager -a -nb',
            'Cyclomatic Complexity (Radon)',
            ignore_errors=True
        )
        f.write("=" * 80 + "\n")
        f.write("CYCLOMATIC COMPLEXITY\n")
        f.write("=" * 80 + "\n")
        f.write(output + '\n\n')
        print("✓ Complexity analysis complete")

        # 6. Maintainability Index
        print("\n[6/6] Calculating maintainability index...")
        output = run_command(
            'radon mi core condominios_manager -nb',
            'Maintainability Index (Radon)',
            ignore_errors=True
        )
        f.write("=" * 80 + "\n")
        f.write("MAINTAINABILITY INDEX\n")
        f.write("=" * 80 + "\n")
        f.write(output + '\n\n')
        print("✓ Maintainability analysis complete")

        # Summary
        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write("\nThis baseline report captures the current state of the codebase\n")
        f.write("before the enterprise-level refactoring process begins.\n\n")
        f.write("Key Metrics to Track:\n")
        f.write("  1. Lines of Code (LOC) - Should decrease as code is refactored\n")
        f.write("  2. Flake8 Violations - Target: 0 violations\n")
        f.write("  3. Pylint Score - Target: 9.0+/10.0\n")
        f.write("  4. Security Issues - Target: 0 high/medium severity issues\n")
        f.write("  5. Cyclomatic Complexity - Target: All functions < 10\n")
        f.write("  6. Maintainability Index - Target: A rating (20-100)\n\n")
        f.write("Next Steps:\n")
        f.write("  1. Review this baseline report\n")
        f.write("  2. Set specific improvement targets for each phase\n")
        f.write("  3. Generate comparative reports after each phase\n")
        f.write("  4. Track progress towards quality goals\n")
        f.write("=" * 80 + "\n")

    print("\n" + "=" * 80)
    print("✓ METRICS REPORT GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nReport saved to: {report_file}")
    print(f"File size: {report_file.stat().st_size / 1024:.2f} KB")
    print("\nTo view the report:")
    print(f"  type {report_file}")
    print("=" * 80)

    return report_file


def main():
    """Main function"""
    try:
        report_file = generate_metrics()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error generating metrics: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
