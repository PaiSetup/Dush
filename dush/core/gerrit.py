import base64
import http.client
import json
from urllib.parse import urlparse

from dush.utils import CommandError, Stdin, Stdout, run_command


class GerritError(Exception):
    pass


def get_gerrit_lastest_change_revision(base_url, change_id):
    # Get credentials from git. This assumes we already used git to clone the repo and have credentials stored.
    creds = run_command("git credential fill", stdin=Stdin.string(f"url={base_url}\n\n"), stdout=Stdout.return_back(), stderr=Stdout.ignore()).stdout
    creds = dict(line.split("=", 1) for line in creds.splitlines() if "=" in line)
    username = creds.get("username")
    password = creds.get("password")

    # Prepare Basic Auth header
    auth_str = f"{username}:{password}"
    auth_header = base64.b64encode(auth_str.encode()).decode()

    # Make HTTPS request to gerrit
    host = urlparse(base_url).netloc
    conn = http.client.HTTPSConnection(host)
    headers = {"Authorization": f"Basic {auth_header}"}
    conn.request("GET", f"/a/changes/{change_id}/detail", headers=headers)
    response = conn.getresponse()
    if response.status != 200:
        raise GerritError("Could not fetch change details from Gerrit")
    detail_data = response.read().decode()

    # Step 5: Strip Gerrit XSSI prefix and parse JSON
    detail_data = detail_data.lstrip(")]}'\n")
    detail_data = json.loads(detail_data)

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(detail_data, f, indent=4, ensure_ascii=False)

    # Step 6: Output (for example, latest ref)
    latest_revision = 0
    for message in detail_data["messages"]:
        if "_revision_number" in message:
            revision = int(message["_revision_number"])
            if revision > latest_revision:
                latest_revision = revision

    if latest_revision == 0:
        raise GerritError("No patch sets found")

    return latest_revision


def checkout_gerrit_change_https(base_url, repo, change_id, force):
    # Get latest revision
    print("Retrieving latest revision for change", change_id)
    revision = get_gerrit_lastest_change_revision(base_url, change_id)
    print("Latest revision is", revision)
    print()

    # Fetch the change
    command = f"git fetch {base_url}/a/{repo} refs/changes/{str(change_id)[-2:]}/{change_id}/{revision}"
    print("Fetching the change")
    print(command)
    run_command(command)
    print()

    # Get fetched commit hash and existing branch commit hash (if exists)
    branch = f"gerrit_{change_id}"
    fetch_commit = run_command("git rev-parse FETCH_HEAD", stdout=Stdout.return_back(), stderr=Stdout.ignore()).stdout.strip()
    try:
        existing_commit = run_command(f"git rev-parse {branch}", stdout=Stdout.return_back(), stderr=Stdout.ignore()).stdout.strip()
    except CommandError:
        existing_commit = None

    # Checkout into a branch
    if existing_commit:
        if existing_commit == fetch_commit:
            run_command(f"git checkout {branch}")
            print(f"Branch {branch} already exists and is up to date.")
        elif force:
            print(f"Branch {branch} already exists but points to a different commit - {existing_commit[:7]}. Recreating it.")
            run_command("git checkout -f FETCH_HEAD")
            run_command(f"git branch -D {branch}")
            run_command(f"git checkout -b {branch}")
        else:
            raise GerritError(f"Branch {branch} already exists but points to a different commit. Please delete it first.")
    else:
        run_command(f"git checkout -b {branch} FETCH_HEAD")
        print(f"Fetched into branch {branch}")


def push_gerrit_change(remote, target_branch):
    # Push the current branch to Gerrit
    command = f"git push {remote} HEAD:refs/for/{target_branch}"
    print(command)
    run_command(command)
