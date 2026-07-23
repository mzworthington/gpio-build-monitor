#!/usr/bin/env python3
import os
from collections.abc import Mapping

from monitor.ci_gateway.constants import IntegrationAdapter, IntegrationType
from monitor.config import TOKEN_ENV_VARS, IntegrationConfig


class IntegrationMapper:
    def __init__(
        self,
        available_integrations: Mapping[IntegrationType, type[IntegrationAdapter]],
    ):
        self.available_integrations = available_integrations

    def get(self, integrations: list[IntegrationConfig]) -> list[IntegrationAdapter]:
        for integration in integrations:
            if integration['type'] not in IntegrationType.__members__:
                raise MismatchError(integration['type'])

        return [self._map(integration) for integration in integrations]

    def _map(self, integration: IntegrationConfig) -> IntegrationAdapter:
        integration_type = IntegrationType[integration['type']]
        token_env = TOKEN_ENV_VARS[integration_type]
        adapter_cls = self.available_integrations[integration_type]
        return adapter_cls(
            type=integration['type'],
            username=integration['username'],
            repo=integration['repo'],
            excluded_workflows=integration.get('excluded_workflows', []),
            token=os.getenv(token_env),
        )


class MismatchError(Exception):
    """An Integration Error Exception"""

    def __init__(self, integration):
        self.integration = integration

    def __str__(self):
        return f'Integration error: we currently do not integrate with {self.integration}.'
