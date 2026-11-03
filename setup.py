from pathlib import Path
from setuptools import setup, find_packages

readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="syntropy-client",
    version="2.5.0",
    author="Synproof (Robert Macků)",
    author_email="developers@synproof.ai",
    description="Official Python SDK, CLI & MCP Server for Synproof's Syntropy — The Deterministic Dialectical Verification Layer for AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://synproof.ai",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.24.0",
        "websockets>=11.0",
        "pydantic>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "syntropy=syntropy.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Legal Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="syntropy, synproof, ai-verification, formal-logic, epistemic-ai, guardrails, llm-verification, mcp, small-worlds",
)
