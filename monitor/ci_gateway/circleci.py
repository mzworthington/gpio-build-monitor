import logging
import os
from abc import ABC

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    APIError,
    BuildStatus,
    CiResult,
    IntegrationAdapter,
    IntegrationType,
)

API_BASE = "https://circleci.com/api/v2"
MAX_PIPELINES = 10


class CircleCI(IntegrationAdapter, ABC):
    def __init__(self, **kwargs):
        self.username = kwargs.get('username')
        self.repo = kwargs.get('repo')
        self.token = kwargs.get('token') or os.getenv('CIRCLE_CI_TOKEN')
        self.excluded_workflows = kwargs.get('excluded_workflows') or []

    def get_type(self) -> IntegrationType:
        return IntegrationType.CIRCLECI

    @property
    def project_slug(self) -> str:
        return f"gh/{self.username}/{self.repo}"

    @property
    def vcs_url(self) -> str:
        return f"https://github.com/{self.username}/{self.repo}"

    def _headers(self) -> dict[str, str]:
        return {
            "Circle-Token": f"{self.token}",
            "Accept": "application/json",
        }

    async def get_latest(self, session: ClientSession) -> list[BuildStatus]:
        pipelines_url = f"{API_BASE}/project/{self.project_slug}/pipeline"
        logging.debug(f"Calling {pipelines_url}")

        resp = await session.get(pipelines_url, headers=self._headers())
        if resp.status != 200:
            raise APIError("GET", pipelines_url, resp.status)

        pipelines = (await resp.json()).get("items", [])
        workflows_by_name: dict[str, dict] = {}

        for pipeline in pipelines[:MAX_PIPELINES]:
            pipeline_id = pipeline["id"]
            workflows_url = f"{API_BASE}/pipeline/{pipeline_id}/workflow"
            workflow_resp = await session.get(workflows_url, headers=self._headers())
            if workflow_resp.status != 200:
                raise APIError("GET", workflows_url, workflow_resp.status)

            for workflow in (await workflow_resp.json()).get("items", []):
                name = workflow["name"]
                if name in self.excluded_workflows:
                    continue

                existing = workflows_by_name.get(name)
                if existing is None or workflow["created_at"] > existing["created_at"]:
                    workflows_by_name[name] = workflow

        response = [
            CircleCI.map_result(workflow, self.vcs_url)
            for workflow in sorted(
                workflows_by_name.values(),
                key=lambda item: item["name"],
            )
        ]
        logging.info(f"Called {pipelines_url}")
        logging.info(f"Response {response}")
        return response

    @staticmethod
    def map_result(workflow: dict, vcs_url: str) -> BuildStatus:
        status = workflow["status"]
        return BuildStatus(
            type=IntegrationType.CIRCLECI,
            vcs=vcs_url,
            id=workflow["id"],
            name=workflow["name"],
            start=workflow["created_at"],
            status=CircleCI._map_status(status),
        )

    @staticmethod
    def _map_status(status: str) -> CiResult:
        if status in {"running", "on_hold", "failing"}:
            return CiResult.RUNNING
        if status == "success":
            return CiResult.PASS
        if status in {"failed", "error"}:
            return CiResult.FAIL
        return CiResult.UNKNOWN


if __name__ == "__main__":
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--username', help='repo username')
    parser.add_argument('--repo', help='repo to query')
    parser.add_argument('--excluded_workflows', nargs='*', default=[])
    args = parser.parse_args()

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(screen_handler)

    async def _main():
        async with ClientSession() as session:
            action = CircleCI(
                username=args.username,
                repo=args.repo,
                excluded_workflows=args.excluded_workflows,
            )
            result = await action.get_latest(session)
            print(result)

    asyncio.run(_main())
