"""Fixture application: serves files from a base directory by name."""

import os


def read_user_file(base_dir, name):
    # Deliberate defect for the code-audit fixtures: the name is joined
    # without confinement, so "../" escapes base_dir.
    path = os.path.join(base_dir, name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def list_user_files(base_dir):
    return sorted(os.listdir(base_dir))
