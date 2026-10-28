#!/usr/bin/env bash

set -e
set -x

mypy fastapi_validation_override examples
ty check fastapi_validation_override examples
ruff check fastapi_validation_override tests examples docs_src
ruff format fastapi_validation_override tests examples docs_src --check
