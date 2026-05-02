from pytestarch import Rule

from .helpers import (
    evaluable,
    module_prefix,
)


def test_core_does_not_import_adapters_or_infra():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.core"
    ).should_not().import_modules_that().are_sub_modules_of(
        [f"{prefix}.adapters", f"{prefix}.infra"]
    ).assert_applies(evaluable())


def test_adapters_do_not_import_infra():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.adapters"
    ).should_not().import_modules_that().are_sub_modules_of(
        f"{prefix}.infra"
    ).assert_applies(evaluable())
