#!/usr/bin/env python3
from collections.abc import Mapping

from monitor.ci_gateway.circleci import CircleCI
from monitor.ci_gateway.constants import IntegrationAdapter, IntegrationType
from monitor.ci_gateway.github import GitHubAction


def get_all() -> Mapping[IntegrationType, type[IntegrationAdapter]]:
    return {
        IntegrationType.GITHUB: GitHubAction,
        IntegrationType.CIRCLECI: CircleCI,
    }
