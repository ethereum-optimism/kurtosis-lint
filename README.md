# Kurtosis Lint

> **DISCLAIMER**: This tool is currently experimental and under active development. APIs and functionality may change without notice.

A linter for Starlark files in Kurtosis packages, that's meant to improve maintainability.

## Features

This linter performs several checks on Starlark files:

1. **Call Analysis**: Checks function calls for compatibility with function signatures
2. **Function Visibility**: Checks if functions are either private or documented
3. **Import Naming**: Checks if global variables assigned import_module() results start with underscore

## Installation

### From PyPI (not yet available)

```bash
pip install kurtosis-lint
```

### From Source

```bash
git clone https://github.com/ethereum-optimism/kurtosis-lint.git
cd kurtosis-lint
pip install -e .
```

## Usage

### Command Line

```bash
# Run all checks on a directory
kurtosis-lint --all path/to/directory

# Run all checks on specific files
kurtosis-lint --all path/to/file1.star path/to/file2.star

# Run specific checks
kurtosis-lint --checked-calls path/to/directory
kurtosis-lint --function-visibility path/to/directory
kurtosis-lint --import-naming path/to/directory

# Enable verbose output
kurtosis-lint -v path/to/directory
```

### Options

- `--checked-calls`: Check function calls for compatibility
- `--function-visibility`: Check function visibility
- `--import-naming`: Check import_module variable naming
- `--all`: Run all checks
- `-v, --verbose`: Enable verbose output

## Development

### Setup Development Environment

```bash
git clone https://github.com/ethereum-optimism/kurtosis-lint.git
cd kurtosis-lint
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## License

All files within this repository are licensed under the MIT License unless stated otherwise.
