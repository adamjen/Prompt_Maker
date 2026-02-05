#!/usr/bin/env python3
"""
Script to update requirements.txt with exact versions from installed packages
"""

import subprocess
import sys
import os


def get_installed_packages():
    """Get list of installed packages with versions"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error getting installed packages: {e}")
        return []


def read_requirements():
    """Read current requirements.txt file"""
    try:
        with open("requirements.txt", "r") as f:
            return [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        print("requirements.txt not found")
        return []


def update_requirements():
    """Update requirements.txt with current installed versions"""
    installed = get_installed_packages()
    current_requirements = read_requirements()

    # Create a dictionary of installed packages (name: version)
    installed_dict = {}
    for package in installed:
        if "==" in package:
            name, version = package.split("==", 1)
            installed_dict[name] = f"{name}=={version}"
        elif ">=" in package:
            name, version = package.split(">=", 1)
            installed_dict[name] = f"{name}>={version}"
        elif "<=" in package:
            name, version = package.split("<=", 1)
            installed_dict[name] = f"{name}<={version}"
        elif "~=" in package:
            name, version = package.split("~=", 1)
            installed_dict[name] = f"{name}~={version}"
        elif ">" in package:
            name, version = package.split(">", 1)
            installed_dict[name] = f"{name}>{version}"
        elif "<" in package:
            name, version = package.split("<", 1)
            installed_dict[name] = f"{name}<{version}"

    # Update requirements.txt with current versions
    updated_lines = []
    for req in current_requirements:
        if "==" in req:
            name = req.split("==")[0]
            if name in installed_dict:
                updated_lines.append(installed_dict[name])
            else:
                updated_lines.append(req)
        elif ">=" in req:
            name = req.split(">=")[0]
            if name in installed_dict:
                updated_lines.append(installed_dict[name])
            else:
                updated_lines.append(req)
        elif "<=" in req:
            name = req.split("<=")[0]
            if name in installed_dict:
                updated_lines.append(installed_dict[name])
            else:
                updated_lines.append(req)
        elif "~=" in req:
            name = req.split("~=")
            if len(name) > 1:
                name = name[0]
                if name in installed_dict:
                    updated_lines.append(installed_dict[name])
                else:
                    updated_lines.append(req)
        else:
            # Handle packages without version specifiers
            name = req.split(">=")[0].split("<=")[0].split("==")[0]
            if name in installed_dict:
                updated_lines.append(installed_dict[name])
            else:
                updated_lines.append(req)

    # Write updated requirements back to file
    with open("requirements.txt", "w") as f:
        for line in updated_lines:
            f.write(f"{line}\n")

    print("requirements.txt has been updated with current installed package versions")


if __name__ == "__main__":
    update_requirements()
