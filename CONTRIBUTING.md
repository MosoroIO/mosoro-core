# Contributing to Mosoro

Thank you for your interest in contributing to Mosoro! We welcome contributions from the community.

## Contributor License Agreement

By submitting a pull request or any other contribution, you agree that your contribution is licensed under the Apache License 2.0 and that you grant Mosoro Inc. a perpetual, worldwide, non-exclusive, royalty-free license to use, reproduce, and distribute your contribution.

We also require a simple CLA for larger contributions (enterprise adapters, security modules). The CLA template is in `docs/Open Source License/docs/CLA.md`.

## How to Contribute

### Adding a New Robot Adapter

This is the most impactful way to contribute. See the [adapter guide in the README](README.md#adding-a-new-robot-adapter).

1. Create `agents/adapters/yourrobot_adapter.py`
2. Subclass `BaseMosoroAdapter`
3. Implement `_fetch_robot_status()` and `send_command()`
4. Create `agents/config/yourrobot.yaml`
5. Add tests in `tests/`
6. Submit a pull request

### Bug Reports

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, Docker version)

### Code Style

- Python 3.11+ with type hints
- Pydantic v2 for all data models
- `async`/`await` for I/O operations
- Structured logging via `logging` module
- All source files must include the Apache 2.0 header (see `docs/Open Source License/Source-file header.md`)

### Source File Header

All new source files must include:

```
// Copyright 2026 Mosoro Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0
```

For Python files, use `#` instead of `//`.

## License

All contributions are licensed under [Apache License 2.0](LICENSE).
