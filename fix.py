import os
import json
import html
import re
from typing import Union
from typing import Optional

import requests
from github import Github
from whatthepatch import parse_patch

def fix(original: str) -> str:
    response = requests.get(
        'https://m.search.naver.com/p/csearch/ocontent/util/SpellerProxy',
        params=dict(q=original, color_blindness=0)
    )
    return html.unescape(response.json()['message']['result']['notag_html'])


def comment_fix_suggestion(gh_token: str, repo_name: Union[str, int], pr_number: int, target: str, extensions: Optional[str]) -> None:
    g = Github(gh_token)
    pr = g.get_repo(repo_name).get_pull(pr_number)
    commits = pr.get_commits()
    comments = []
    extensions = extensions.split(",") if extensions else []
    for file in pr.get_files():
        if (target and not re.match(target, file.filename)) or (len(extensions) > 0 and file.filename.split(".")[-1] not in extensions):
            continue
        for diff in parse_patch(file.patch):
            for change in diff.changes:
                fixed = fix(change.line)
                if not change.old and fixed != change.line:
                    comments.append({
                        "path": file.filename,
                        "position": change.new,
                        "body": f"""```suggestion\n{fixed}\n```"""
                    })
    pr.create_review(
        commit=commits[commits.totalCount-1],
        body='grammar check',
        event='COMMENT',
        comments=comments
    )

if 'GITHUB_EVENT_PATH' in os.environ:
    with open(os.environ.get('GITHUB_EVENT_PATH')) as gh_event:
        json_data = json.load(gh_event)
        comment_fix_suggestion(
            gh_token=os.environ.get('GITHUB_TOKEN'),
            repo_name=os.environ.get('GITHUB_REPOSITORY'),
            pr_number=json_data['issue']['number'],
            target=os.environ.get('INPUT_TARGET'),
            extensions=os.environ.get('INPUT_EXTENSIONS')
        )
