from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="env-sentinel",
    version="0.1.0",
    author="Monis Malik",
    description="Catch environment variable drift, format errors, and secret leaks before they reach production.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MONISMALIK1/env-sentinel",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
    ],
    entry_points={
        "console_scripts": [
            "env-sentinel=env_sentinel.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Utilities",
    ],
    keywords="env dotenv environment secrets drift validation ci devops",
)
