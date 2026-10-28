#!/usr/bin/env bash
set -x

ruff check fastapi_validation_override tests examples docs_src --fix
ruff format fastapi_validation_override tests examples docs_src
