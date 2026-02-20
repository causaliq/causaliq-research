# causaliq-research

![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

CausalIQ Research is for developing, publishing, and reproducing research
work based on the CausalIQ ecosystem. It provides a curated collection of
experimental setups, benchmark datasets, and published results that enable
reproducible research and method comparison in causal discovery and inference.

It is part of the [CausalIQ ecosystem](https://causaliq.org/) for intelligent
causal discovery and inference.


## Repository Structure

This repository is organised around research concepts rather than file types:

```
causaliq-research/
├── src/              # Minimal code (CLI, utilities)
├── models/           # Bayesian model specifications - by model
│   └── asia/
│   └── sachs/
├── experiments/      # Workflows + results - by series
│   └── llm-benchmark-2026/
│       ├── workflow.yaml
│       └── results.db
├── papers/           # Generated assets - by paper
│   └── llm-priors-2026/
│       ├── tables/
│       └── figures/
└── scratch/          # Gitignored working directory
```

- **models/** - Reusable Bayesian model specifications, organised by model
- **experiments/** - Workflows and result caches, organised by experiment series
- **papers/** - Generated tables and figures, organised by paper
- **scratch/** - Gitignored scratch space for development work

### Asset Management

Currently, workflows, model specifications, and result caches are committed
to GitHub for safety and reproducibility. The CLI will eventually support
downloading assets from Zenodo for published work.


## Status

🚧 **Active Development** 

- This repository is currently in active development. 
- Work for new published papers will be created in this repo.
- Work from previously published papers will be migrated from the legacy monolithic discovery repo as the CausalIQ ecosystem supports the required functionality.


## Features

Completed releases:

- None

Planned releases:

- **Release v0.1.0 - Graph Averaging** *(in development)*: Models and workflows for LLM-assisted graph averaging

### Feature Overview

- 📁 **Standardised project structure**: following current best practices
- ⌨️ **CLI Interface**: An initial dummy command-line interface.
- 📖 **Documentation framework**: using mkdocs with shared CausalIQ branding.
- 🐍 **Python setup**: providing virtual environments for Python 3.9, 3.10, 3.11, 3.12 and 3.13.
- 🔬 **pytest test framework**: for unit, functional and integration testing including code coverage.
- 🔄 **Continuous Integration testing**: across Python versions and operating systems using GitHub actions 


### Usage

Full instructions on using this as a template to start a new CausalIQ repo are given [here](docs/userguide/template.md)

---

## Upcoming Key Innovations

### 🤷 TO BE COMPLETED
- tbc

## Integration with CausalIQ Ecosystem

- 💯 **tbc** - to be completed.

## LLM Support

The following provides project-specific context for this repo which should be provided after the [personal and ecosystem context](https://github.com/causaliq/causaliq/blob/main/LLM_DEVELOPMENT_GUIDE.md):

```text
to be completed
```

## Quick Start

```python
# to be completed
```

## Getting started

### Prerequisites

- Git 
- Latest stable versions of Python 3.9, 3.10. 3.11, 3.12 and 3.13


### Clone the new repo locally and check that it works

Clone the causaliq-research repo locally as normal

```bash
git clone https://github.com/causaliq/causaliq-research.git
```

Set up the Python virtual environments and activate the default Python virtual environment. You may see
messages from VSCode (if you are using it as your IDE) that new Python environments are being created
as the scripts/setup-env runs - these messages can be safely ignored at this stage.

```text
scripts/setup-env -Install
scripts/activate
```

Check that the causaliq-newcapability CLI is working, check that all CI tests pass, and start up the local mkdocs webserver. There should be no errors  reported in any of these.

```text
causaliq-newcapability --help
scripts/check_ci
mkdocs serve
```

Enter **http://127.0.0.1:8000/** in a browser and check that the 
causaliq-data documentation is visible.

If all of the above works, this confirms that the code is working successfully on your system.


## Documentation

Full API documentation is available at: **http://127.0.0.1:8000/** (when running `mkdocs serve`)

## Contributing

This repository is part of the CausalIQ ecosystem. For development setup:

1. Clone the repository
2. Run `scripts/setup-env -Install` to set up environments  
3. Run `scripts/check_ci` to verify all tests pass
4. Start documentation server with `mkdocs serve`

---

**Supported Python Versions**: 3.9, 3.10, 3.11, 3.12, 3.13  
**Default Python Version**: 3.11  
**License**: MIT

