import subprocess
import sys

commands = [
    ["black", "."],
    ["flake8", "."],
    ["mypy", "-p", "app"],
    ["ruff", "check", "."],
]


def main():
    for cmd in commands:
        print(f"\n🚀 Running: {' '.join(cmd)}")
        result = subprocess.run(["poetry", "run"] + cmd)
        if result.returncode != 0:
            print(f"❌ Command failed: {' '.join(cmd)}")
            sys.exit(result.returncode)
    print("\n✅ All linters passed successfully!")


if __name__ == "__main__":
    main()
