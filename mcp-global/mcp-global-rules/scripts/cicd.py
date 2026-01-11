"""
CI/CD Pipeline Generator
========================
Generate CI/CD pipelines for various providers.

Usage:
    python mcp.py github-action
    python mcp.py pipeline --gitlab
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json
import sys

from .utils import Console, find_project_root


@dataclass
class ProjectType:
    """Detected project type."""
    language: str
    framework: Optional[str]
    package_manager: str
    test_command: str
    lint_command: str
    has_docker: bool


# GitHub Actions Templates
GITHUB_PYTHON = '''name: Python CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov flake8 mypy

    - name: Lint with flake8
      run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

    - name: Type check with mypy
      run: mypy . --ignore-missing-imports || true

    - name: Test with pytest
      run: pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
'''

GITHUB_NODE = '''name: Node.js CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ['18.x', '20.x']

    steps:
    - uses: actions/checkout@v4

    - name: Use Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Lint
      run: npm run lint || true

    - name: Test
      run: npm test

    - name: Build
      run: npm run build --if-present
'''

GITHUB_DOCKER = '''name: Docker Build

on:
  push:
    branches: [ main, master ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main, master ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to DockerHub
      if: github.event_name != 'pull_request'
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: ${{ github.event_name != 'pull_request' }}
        tags: |
          ${{ github.repository }}:latest
          ${{ github.repository }}:${{ github.sha }}
'''

# GitLab CI Templates
GITLAB_PYTHON = '''stages:
  - lint
  - test
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"

cache:
  paths:
    - .pip-cache/

lint:
  stage: lint
  image: python:3.11
  script:
    - pip install flake8 mypy
    - flake8 . --count --select=E9,F63,F7,F82
    - mypy . --ignore-missing-imports || true

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=. --cov-report=xml
  coverage: '/TOTAL.*\\s+(\\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
'''

GITLAB_NODE = '''stages:
  - lint
  - test
  - build

cache:
  paths:
    - node_modules/

lint:
  stage: lint
  image: node:20
  script:
    - npm ci
    - npm run lint

test:
  stage: test
  image: node:20
  script:
    - npm ci
    - npm test

build:
  stage: build
  image: node:20
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
'''


def detect_project_type(root: Path) -> ProjectType:
    """Detect project type from files."""
    # Check for Python
    has_requirements = (root / 'requirements.txt').exists()
    has_setup_py = (root / 'setup.py').exists()
    has_pyproject = (root / 'pyproject.toml').exists()

    # Check for Node
    has_package_json = (root / 'package.json').exists()

    # Check for Docker
    has_docker = (root / 'Dockerfile').exists()

    if has_requirements or has_setup_py or has_pyproject:
        framework = None
        if has_pyproject:
            content = (root / 'pyproject.toml').read_text()
            if 'fastapi' in content.lower():
                framework = 'fastapi'
            elif 'django' in content.lower():
                framework = 'django'
            elif 'flask' in content.lower():
                framework = 'flask'

        return ProjectType(
            language='python',
            framework=framework,
            package_manager='pip',
            test_command='pytest',
            lint_command='flake8',
            has_docker=has_docker
        )

    if has_package_json:
        framework = None
        try:
            pkg = json.loads((root / 'package.json').read_text())
            deps = list(pkg.get('dependencies', {}).keys()) + list(pkg.get('devDependencies', {}).keys())
            if 'next' in deps:
                framework = 'nextjs'
            elif 'react' in deps:
                framework = 'react'
            elif 'vue' in deps:
                framework = 'vue'
        except Exception:
            pass

        return ProjectType(
            language='node',
            framework=framework,
            package_manager='npm',
            test_command='npm test',
            lint_command='npm run lint',
            has_docker=has_docker
        )

    # Default
    return ProjectType(
        language='unknown',
        framework=None,
        package_manager='',
        test_command='',
        lint_command='',
        has_docker=has_docker
    )


def generate_github_action(project_type: ProjectType) -> str:
    """Generate GitHub Actions workflow."""
    if project_type.has_docker:
        return GITHUB_DOCKER

    if project_type.language == 'python':
        return GITHUB_PYTHON

    if project_type.language == 'node':
        return GITHUB_NODE

    return GITHUB_PYTHON  # Default


def generate_gitlab_ci(project_type: ProjectType) -> str:
    """Generate GitLab CI config."""
    if project_type.language == 'python':
        return GITLAB_PYTHON

    if project_type.language == 'node':
        return GITLAB_NODE

    return GITLAB_PYTHON  # Default


def write_github_action(root: Path) -> Path:
    """Write GitHub Actions workflow to file."""
    project_type = detect_project_type(root)
    content = generate_github_action(project_type)

    workflow_dir = root / '.github' / 'workflows'
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_file = workflow_dir / 'ci.yml'
    workflow_file.write_text(content)

    return workflow_file


def write_gitlab_ci(root: Path) -> Path:
    """Write GitLab CI config to file."""
    project_type = detect_project_type(root)
    content = generate_gitlab_ci(project_type)

    ci_file = root / '.gitlab-ci.yml'
    ci_file.write_text(content)

    return ci_file


def main():
    """CLI entry point."""
    Console.header("CI/CD Generator")

    root = find_project_root() or Path.cwd()
    project_type = detect_project_type(root)

    Console.info(f"Detected: {project_type.language}")
    if project_type.framework:
        Console.info(f"Framework: {project_type.framework}")
    if project_type.has_docker:
        Console.info("Docker: Yes")

    if '--gitlab' in sys.argv:
        path = write_gitlab_ci(root)
        Console.ok(f"Generated: {path}")
        return 0

    if '--print' in sys.argv:
        content = generate_github_action(project_type)
        print(content)
        return 0

    # Default: GitHub Actions
    path = write_github_action(root)
    Console.ok(f"Generated: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
