#!/usr/bin/env python3

import os

import pytest

from monitor.ci_gateway import integration_actions as available_integrations
from monitor.ci_gateway.circleci import CircleCI
from monitor.ci_gateway.constants import IntegrationType
from monitor.ci_gateway.github import GitHubAction
from monitor.service.integration_mapper import IntegrationMapper, MismatchError

os.environ['GITHUB_TOKEN'] = 'secret'
os.environ['CIRCLE_CI_TOKEN'] = 'secret'


class TestIntegrationMapper:
    def test_fails_when_integration_is_unknown(self):
        integrations = [
            dict(type='BLURGH', username='meee', repo='super-repo')
        ]

        with pytest.raises(MismatchError) as excinfo:
            IntegrationMapper(
                available_integrations.get_all()).get(integrations)

        assert str(excinfo.value) == (
            'Integration error: we currently do not integrate with BLURGH.'
        )

    def test_maps_github_integrations(self):
        integrations = [
            dict(type='GITHUB', username='meee', repo='super-repo'),
            dict(type='GITHUB', username='you', repo='another-repo'),
        ]
        result = IntegrationMapper(
            available_integrations.get_all()).get(integrations)

        assert len(result) == 2
        assert all(isinstance(adapter, GitHubAction) for adapter in result)
        assert result[0].username == 'meee'
        assert result[1].repo == 'another-repo'

    def test_maps_circleci_integration(self):
        integrations = [
            dict(
                type='CIRCLECI',
                username='them',
                repo='special-repo',
                excluded_workflows=['scan'],
            ),
        ]
        result = IntegrationMapper(
            available_integrations.get_all()).get(integrations)

        assert len(result) == 1
        assert isinstance(result[0], CircleCI)
        assert result[0].username == 'them'
        assert result[0].excluded_workflows == ['scan']

    def test_passes_token_to_adapter(self):
        integrations = [
            dict(type='GITHUB', username='meee', repo='super-repo'),
        ]
        result = IntegrationMapper(
            available_integrations.get_all()).get(integrations)

        assert result[0].token == 'secret'
        assert result[0].get_type() == IntegrationType.GITHUB
