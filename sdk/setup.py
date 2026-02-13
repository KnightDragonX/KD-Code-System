from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kdcode-sdk",
    version="1.0.0",
    author="K. D. Sithara Nimsara and J. A. Umeda Sammani",
    author_email="contact@kdcode.example.com",
    description="SDK for integrating KD-Code functionality into third-party applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kdcode/kdcode-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.0.0",
            "flake8>=3.8.0",
        ],
    },
)