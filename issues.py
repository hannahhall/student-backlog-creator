import sys
import os
import urllib.request
import urllib.error
import urllib.parse
import json
import base64
import datetime


http_error_messages = {}
http_error_messages[401] = "ERROR: There was a problem during authentication.\nDouble check that your username and password are correct, and that you have permission to read from or write to the specified repositories."
# Basically the same problem. GitHub returns 403 instead to prevent abuse.
http_error_messages[403] = http_error_messages[401]
http_error_messages[404] = "ERROR: Unable to find the specified repository.\nDouble check the spelling for the source and target repositories. If either repository is private, make sure the specified user is allowed access to it."


def import_issues(config, issues, repo):

    new_issues = []

    for issue in issues:

        new_issue = {}
        new_issue['title'] = issue['title']

        # Temporary fix for marking closed issues
        if issue['closed_at']:
            new_issue['title'] = "[CLOSED] " + new_issue['title']

        template_data = {}
        template_data['user_name'] = issue['user']['login']
        template_data['user_url'] = issue['user']['html_url']
        template_data['user_avatar'] = issue['user']['avatar_url']
        template_data['date'] = format_date(config, issue['created_at'])
        template_data['url'] = issue['html_url']
        template_data['body'] = issue['body']

        new_issue['body'] = format_issue(config, template_data)
        new_issues.append(new_issue)

    print(f"You are about to add to {repo}:")
    print(f"\t* {len(new_issues)} new issues")

    result_issues = []
    for issue in new_issues:
        issue['labels'] = ['enhancement']
        result_issue = send_import_request(config, repo, issue)
        print(f"Successfully created issue '{result_issue['title']}'")
        result_issues.append(result_issue)

    return result_issues

def send_import_request(config, repo, post_data=None):

    if post_data is not None:
        post_data = json.dumps(post_data).encode("utf-8")

    full_url = f"{repo}/issues"
    req = urllib.request.Request(full_url, post_data)

    username = config.get('target', 'username')
    password = config.get('target', 'password')

    req.add_header("Authorization", b"Basic " + base64.urlsafe_b64encode(
        username.encode("utf-8") + b":" + password.encode("utf-8")))

    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "nss/ticket-migrator")

    try:
        response = urllib.request.urlopen(req)
        json_data = response.read()
    except urllib.error.HTTPError as error:

        error_details = error.read()
        error_details = json.loads(error_details.decode("utf-8"))

        if error.code in http_error_messages:
            sys.exit(http_error_messages[error.code])
        else:
            error_message = "ERROR: There was a problem importing the issues.\n%s %s" % (
                error.code, error.reason)
            if 'message' in error_details:
                error_message += "\nDETAILS: " + error_details['message']
            sys.exit(error_message)

    return json.loads(json_data.decode("utf-8"))


def format_from_template(template_filename, template_data):
    from string import Template
    template_file = open(template_filename, 'r')
    template = Template(template_file.read())
    return template.substitute(template_data)


def format_issue(config, template_data):
    __location__ = os.path.realpath(os.path.join(
        os.getcwd(), os.path.dirname(__file__)))
    default_template = os.path.join(__location__, 'templates', 'issue.md')
    template = config.get('format', 'issue_template',
                          fallback=default_template)
    return format_from_template(template, template_data)


def format_date(config, datestring):
    # The date comes from the API in ISO-8601 format
    date = datetime.datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ")
    date_format = config.get(
        'format', 'date', fallback='%A %b %d, %Y at %H:%M GMT', raw=True)
    return date.strftime(date_format)


def get_issues_by_state(config, which, state):
    issues = []
    page = 1
    while True:
        new_issues = send_import_request(
            config, which, f'issues?state={state}&direction=asc&page={page}')
        if not new_issues:
            break
        issues.extend(new_issues)
        page += 1
    return issues


def get_issue_by_id(config, which, issue_id):
    return send_import_request(config, which, "issues/%d" % issue_id)


def get_issues_by_id(config, which, issue_ids):
    issues = []
    for issue_id in issue_ids:
        issues.append(get_issue_by_id(config, which, int(issue_id)))

    return issues


