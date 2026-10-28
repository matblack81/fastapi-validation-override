import inspect

from collections.abc import Callable
from typing import Any, get_args, get_type_hints

import pytest

from annotated_doc import Doc

from fastapi_validation_override import override_validation_error, patch_422_responses


def _doc_text(hint: Any) -> str | None:
    candidates = [hint, *get_args(hint)]
    return next(
        (
            meta.documentation
            for candidate in candidates
            for meta in getattr(candidate, "__metadata__", ())
            if isinstance(meta, Doc)
        ),
        None,
    )


@pytest.mark.parametrize("target", [override_validation_error, patch_422_responses])
def test_every_parameter_of_a_public_callable_is_documented(target: Callable[..., Any]) -> None:
    """The reference site is generated from these Doc annotations, so a parameter without one
    would be published with no description."""
    hints = get_type_hints(target, include_extras=True)
    names = list(inspect.signature(target).parameters)

    assert names
    undocumented = [name for name in names if not _doc_text(hints[name])]
    assert undocumented == []


@pytest.mark.parametrize("target", [override_validation_error, patch_422_responses])
def test_public_annotations_resolve_for_downstream_introspection(target: Callable[..., Any]) -> None:
    """typing.get_type_hints and inspect.signature(eval_str=True) are what third-party tools
    call on a typed package; both must resolve the Annotated/Doc annotations without a NameError."""
    assert get_type_hints(target)
    inspect.signature(target, eval_str=True)
