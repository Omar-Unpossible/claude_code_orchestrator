"""Setup configuration for Claude Code Orchestrator."""

from setuptools import setup, find_packages

setup(
    name="claude-code-orchestrator",
    version="0.1.0",
    description="Intelligent orchestration system for Claude Code CLI",
    author="Omar",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # Will be populated as we implement more milestones
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pylint>=3.0.0",
            "mypy>=1.5.0",
            "black>=23.7.0",
            "isort>=5.12.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
