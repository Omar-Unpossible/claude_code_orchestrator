"""Setup configuration for Claude Code Orchestrator."""

from setuptools import setup, find_packages

setup(
    name="claude-code-orchestrator",
    version="1.2.0",
    description="Intelligent orchestration system for Claude Code CLI",
    author="Omar",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "jinja2>=3.1.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "watchdog>=3.0.0",
        "pyyaml>=6.0",
        "scipy>=1.11.0",  # PHASE_6 TASK_6.2: A/B testing statistical analysis
        "colorama>=0.4.6",  # Interactive Streaming: Colored terminal output
        "prompt_toolkit>=3.0.0",  # Interactive Streaming: Rich interactive input
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
