# causaliq-repo-template

![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

This is a template for **creating new CausalIQ repos** which provides a new **capability** and follows CausalIQ development practices. It is part of the [CausalIQ ecosystem](https:/causaliq.org/) for intelligent causal discovery.


## Status

🚧 **Active Development** 

- This repository is currently in active development. It will be updated periodically to align with the latest approaches used in CausalIQ repos.
- New repos within the CausalIQ project should follow the naming convention causaliq-[newcapability], e.g. "causaliq-discovery" or "causaliq-analysis".


## Features

Completed releases:

- **Release v1.0.0 Foundation**: ready for use as template for new CausalIQ repos

Planned releases:

- **Release v1.1.0 Maintenance**: Maintenance to include new features into template

### Feature Overview

- 📁 **Standardised project structure**: following current best practices
- ⌨️ **CLI Interface**: An initial dummy command-line interface.
- 📖 **Documentation framework**: using mkdocs with shared CausalIQ branding.
- 🐍 **Python setup**: providing virtual environments for Python 3.9, 3.10, 3.11 and 3.12.
- 🔬 **pytest test framework**: for unit, functional and integration testing including code coverage.
- 🔄 **Continuous Integration testing**: across Python versions and operating systems using GitHub actions 


### Usage

Full instructions on using this as a template to start a new CausalIQ repo are given [here](docs/userguide/template.md)

---

## Upcoming Key Innovations

### 🤷 None planned
- **not applicable** - for this repo template, but will be for concrete projects

## Integration with CausalIQ Ecosystem

- 💯 **All CausalIQ projects** - this repo template is used as a starting point for all CausalIQ repos.

## LLM Support

The following provides project-specific context for this repo which should be provided after the [personal and ecosystem context](https://github.com/causaliq/causaliq/blob/main/LLM_DEVELOPMENT_GUIDE.md):

```text
I wish to migrate the code in legacy/core/metrics.py following all CausalIQ development guidelines
so that the legacy repo can use the migrated code instead. 
```

## Quick Start

```python
# to be completed
```

## Getting started

### Prerequisites

- Git 
- Latest stable versions of Python 3.9, 3.10. 3.11 and 3.12


### Clone the new repo locally and check that it works

Clone the causaliq-newcapability repo locally as normal

```bash
git clone https://github.com/causaliq/causaliq-newcapability.git
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

**Supported Python Versions**: 3.9, 3.10, 3.11, 3.12  
**Default Python Version**: 3.11  
**License**: MIT

