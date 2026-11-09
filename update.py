import json
import os
import re
import urllib.request

USER = """
{
  viewer {
    id
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER) { totalCount nodes { name stargazerCount } }
    contributed: repositories(ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) { totalCount }
  }
}
"""

HISTORY = """
query($name: String!, $id: ID!, $cursor: String) {
  viewer {
    repository(name: $name) {
      defaultBranchRef {
        target {
          ... on Commit {
            history(first: 100, after: $cursor, author: {id: $id}) {
              totalCount
              pageInfo { hasNextPage endCursor }
              nodes { additions deletions }
            }
          }
        }
      }
    }
  }
}
"""


def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["data"]


def put(svg, key, value, pad=None):
    pad = f"{pad or key}_dots"
    old = re.search(f'id="{key}">([^<]*)<', svg)[1]
    dots = re.search(f'id="{pad}">([^<]*)<', svg)[1]
    svg = svg.replace(f'id="{key}">{old}<', f'id="{key}">{value}<')
    return svg.replace(f'id="{pad}">{dots}<', f'id="{pad}">{"." * max(1, len(dots) + len(old) - len(value))}<')


me = gql(USER)["viewer"]
repos = me["repositories"]

commits = added = deleted = 0
for repo in repos["nodes"]:
    cursor = None
    while True:
        branch = gql(HISTORY, name=repo["name"], id=me["id"], cursor=cursor)["viewer"]["repository"]["defaultBranchRef"]
        if not branch:
            break
        history = branch["target"]["history"]
        added += sum(c["additions"] for c in history["nodes"])
        deleted += sum(c["deletions"] for c in history["nodes"])
        if not history["pageInfo"]["hasNextPage"]:
            commits += history["totalCount"]
            break
        cursor = history["pageInfo"]["endCursor"]

for path in ("dark_mode.svg", "light_mode.svg"):
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    svg = put(svg, "repos", f"{repos['totalCount']:,}")
    svg = put(svg, "contributed", f"{me['contributed']['totalCount']:,}", pad="repos")
    svg = put(svg, "stars", f"{sum(r['stargazerCount'] for r in repos['nodes']):,}")
    svg = put(svg, "commits", f"{commits:,}")
    svg = put(svg, "followers", f"{me['followers']['totalCount']:,}")
    svg = put(svg, "loc", f"{added - deleted:,}")
    svg = put(svg, "added", f"{added:,}++", pad="loc")
    svg = put(svg, "deleted", f"{deleted:,}--", pad="loc")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
