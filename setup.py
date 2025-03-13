from setuptools import setup, find_packages

setup(
    name="kurtosis-lint",
    version="0.1.0",
    description="Linter for Starlark files in Kurtosis packages",
    author="Kurtosis Tech",
    author_email="info@kurtosis.com",
    url="https://github.com/ethereum-optimism/kurtosis-lint",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "kurtosis-lint=analysis.unified_analyzer:main",
        ],
    },
    python_requires=">=3.7",
    install_requires=[
        "setuptools>=42.0.0",
        "wheel>=0.37.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 