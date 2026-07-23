import logging
import os
from abc import ABC
from itertools import groupby

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    APIError,
    BuildStatus,
    CiResult,
    IntegrationAdapter,
    IntegrationType,
)


class GitHubAction(IntegrationAdapter, ABC):
    def __init__(self, **kwargs):
        self.username = kwargs.get('username')
        self.repo = kwargs.get('repo')
        self.token = kwargs.get('token') or os.getenv('GITHUB_TOKEN')
        self.excluded_workflows = kwargs.get('excluded_workflows') or []

    def get_type(self) -> IntegrationType:
        return IntegrationType.GITHUB

    async def get_latest(self, session: ClientSession) -> list[BuildStatus]:
        base = 'https://api.github.com'
        url = f'{base}/repos/{self.username}/{self.repo}/actions/runs'

        logging.debug(f'Calling {url}')

        resp = await session.get(
            url,
            headers={'Authorization': f'Bearer {self.token}'})

        if resp.status != 200:
            raise APIError('GET', url, resp.status)

        payload = await resp.json()

        response = list(
            map(
                GitHubAction.map_result,
                self.get_unique_latest_jobs(payload['workflow_runs'])))
        logging.info(f'Called {url}')
        logging.info(f'Response {response}')
        return response

    @staticmethod
    def map_result(latest) -> BuildStatus:
        conclusion = latest["conclusion"]
        status = latest["status"]
        return BuildStatus(
            type=IntegrationType.GITHUB,
            vcs=latest["html_url"],
            id=latest["id"],
            name=latest["name"],
            start=latest["created_at"],
            status=CiResult.FAIL if status == "completed" and conclusion == "failure" else
            CiResult.PASS if status == "completed" and conclusion == "success" else
            CiResult.RUNNING if conclusion is None and (status == "queued" or status == "in_progress") else
            CiResult.UNKNOWN)

    def get_unique_latest_jobs(self, json):
        jobs = []
        for k, g in groupby(
                sorted(
                    filter(
                        lambda x: x['name']
                        not in self.excluded_workflows,
                        json), key=lambda x: x['name']),
                lambda x: x['name']):
            jobs.append(list(g)[0])

        return jobs


if __name__ == "__main__":
    import argparse
    import asyncio
    import os
    import sys

    parser = argparse.ArgumentParser()

    parser.add_argument('--username', help='repo username')
    parser.add_argument('--repo', help='repo to query')

    args = parser.parse_args()

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(screen_handler)

    async def _main():
        async with ClientSession() as session:
            action = GitHubAction(
                username=args.username,
                repo=args.repo,
                token=os.getenv('GITHUB_TOKEN'),
            )
            result = await action.get_latest(session)
            print(result)

    asyncio.run(_main())
