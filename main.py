import json
import urllib.request
import urllib.error

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from packaging.requirements import Requirement


PYTHON_VERSION = Version("3.11")


def get_release(package, version):
    url = f"https://pypi.org/pypi/{package}/{version}/json"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ASE-Dependency-Checker"}
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    except urllib.error.URLError as error:
        print(f"Connection error for {package}: {error}")
        return None


def get_minimum_python_version(python_requirement):
    if not python_requirement:
        return None

    specifiers = SpecifierSet(python_requirement)
    minimum_versions = []

    for spec in specifiers:
        if spec.operator in (">=", ">", "~="):
            try:
                minimum_versions.append(Version(spec.version))
            except Exception:
                continue

    if not minimum_versions:
        return None

    return max(minimum_versions)


def check_requirements():

    with open("requirements.txt", "r", encoding="utf-8") as file:
        lines = [
            line.strip()
            for line in file
            if line.strip() and not line.strip().startswith("#")
        ]

    total_checked = len(lines)
    missing_packages = []
    incompatible_packages = []

    highest_requirement = None

    for line in lines:

        try:
            requirement = Requirement(line)

            if requirement.marker and not requirement.marker.evaluate():
                continue

            package = requirement.name

            # This task checks exact pinned versions.
            pinned_versions = [
                spec for spec in requirement.specifier
                if spec.operator == "=="
            ]

            if (
                len(pinned_versions) != 1
                or len(list(requirement.specifier)) != 1
                or "*" in pinned_versions[0].version
            ):
                print(f"Skipping unsupported requirement: {line}")
                continue

            version = pinned_versions[0].version

            print(f"Checking {package}=={version}")

            release_data = get_release(package, version)

            if release_data is None:
                missing_packages.append(line)
                continue

            python_requirement = (
                release_data.get("info", {}).get("requires_python")
            )

            # A release without requires_python is considered compatible.
            if not python_requirement:
                continue

            supported_versions = SpecifierSet(python_requirement)

            if not supported_versions.contains(PYTHON_VERSION):
                incompatible_packages.append(
                    (package, version, python_requirement)
                )

            minimum_version = get_minimum_python_version(
                python_requirement
            )

            if minimum_version is not None:

                if (
                    highest_requirement is None
                    or minimum_version > highest_requirement[0]
                ):
                    highest_requirement = (
                        minimum_version,
                        package,
                        version
                    )

        except Exception as error:
            print(f"Could not process '{line}': {error}")

    print("\nDependencies checked:", total_checked)
    print("Not found on PyPI:", len(missing_packages))
    print(
        "Incompatible with Python 3.11:",
        len(incompatible_packages)
    )

    if highest_requirement is not None:

        minimum, package, version = highest_requirement

        print(
            f"Highest requirement: "
            f"{package}=={version} (>= {minimum})"
        )

    else:
        print("Highest requirement: None")


if __name__ == "__main__":
    check_requirements()