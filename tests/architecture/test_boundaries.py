from pytestarch import Rule

from .helpers import (
    evaluable,
    module_prefix,
)


def test_core_does_not_import_adapters_or_infra():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.core",
    ).should_not().import_modules_that().are_sub_modules_of(
        [f"{prefix}.adapters", f"{prefix}.infra"],
    ).assert_applies(evaluable())


def test_domain_is_isolated_from_outer_layers():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.core.domain",
    ).should_not().import_modules_that().are_sub_modules_of(
        [
            f"{prefix}.core.ports",
            f"{prefix}.core.use_cases",
            f"{prefix}.adapters",
            f"{prefix}.infra",
        ],
    ).assert_applies(evaluable())


def test_ports_do_not_import_use_cases_or_outer_layers():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.core.ports",
    ).should_not().import_modules_that().are_sub_modules_of(
        [
            f"{prefix}.core.use_cases",
            f"{prefix}.adapters",
            f"{prefix}.infra",
        ],
    ).assert_applies(evaluable())


def test_use_cases_do_not_import_adapters_or_infra():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.core.use_cases",
    ).should_not().import_modules_that().are_sub_modules_of(
        [f"{prefix}.adapters", f"{prefix}.infra"],
    ).assert_applies(evaluable())


def test_adapters_do_not_import_infra():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.adapters",
    ).should_not().import_modules_that().are_sub_modules_of(
        f"{prefix}.infra",
    ).assert_applies(evaluable())


def test_input_adapters_do_not_import_use_cases():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        f"{prefix}.adapters.input",
    ).should_not().import_modules_that().are_sub_modules_of(
        f"{prefix}.core.use_cases",
    ).assert_applies(evaluable())


def test_supporting_infra_does_not_import_adapters():
    prefix = module_prefix()
    Rule().modules_that().are_sub_modules_of(
        [f"{prefix}.infra.settings", f"{prefix}.infra.logging"],
    ).should_not().import_modules_that().are_sub_modules_of(
        f"{prefix}.adapters",
    ).assert_applies(evaluable())
