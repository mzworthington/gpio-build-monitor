#!/usr/bin/env python3

from monitor.ci_gateway import integration_actions
from monitor.ci_gateway.circleci import CircleCI
from monitor.ci_gateway.constants import IntegrationType
from monitor.ci_gateway.github import GitHubAction


class TestIntegrations:
    def test_get_all(self):
        result = integration_actions.get_all()

        assert GitHubAction is result[IntegrationType.GITHUB]
        assert CircleCI is result[IntegrationType.CIRCLECI]
        assert len(result) == 2
