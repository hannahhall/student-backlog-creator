#!/Users/chortlehoort/.pyenv/shims/python

import json
import sys
import os
import query
import argparse
import configparser
from project import ProjectBoard
from issues import get_issues_by_id, get_issues_by_state, import_issues


__location__ = os.path.realpath(os.path.join(
    os.getcwd(), os.path.dirname(__file__)))
default_config_file = os.path.join(__location__, 'config.ini')
config = configparser.RawConfigParser()

def init_config():

    config.add_section('login')
    config.add_section('source')
    config.add_section('target')
    config.add_section('format')
    config.add_section('settings')

    arg_parser = argparse.ArgumentParser(
        description="Import issues from one GitHub repository into another.")

    config_group = arg_parser.add_mutually_exclusive_group(required=False)
    config_group.add_argument(
        '--config', help="The location of the config file (either absolute, or relative to the current working directory). Defaults to `config.ini` found in the same folder as this script.")
    config_group.add_argument('--no-config', dest='no_config',  action='store_true',
                              help="No config file will be used, and the default `config.ini` will be ignored. Instead, all settings are either passed as arguments, or (where possible) requested from the user as a prompt.")

    arg_parser.add_argument(
        '-u', '--username', help="The username of the account that will create the new issues. The username will not be stored anywhere if passed in as an argument.")
    arg_parser.add_argument(
        '-p', '--password', help="The password (in plaintext) of the account that will create the new issues. The password will not be stored anywhere if passed in as an argument.")
    arg_parser.add_argument(
        '-s', '--source', help="The source repository which the issues should be copied from. Should be in the format `user/repository`.")
    arg_parser.add_argument(
        '-t', '--target', help="The destination repository which the issues should be copied to. Should be in the format `user/repository`.")

    include_group = arg_parser.add_mutually_exclusive_group(required=True)
    include_group.add_argument("-a", "--all", dest='import_all', action='store_true',
                               help="Import all open issues.")
    include_group.add_argument('-i', '--issues', nargs='+', type=int, help="The list of issues to import. (e.g. -i 1 5 6 10 15)")

    args = arg_parser.parse_args()

    def load_config_file(config_file_name):
        try:
            config_file = open(config_file_name)
            config.read_file(config_file)
            return True
        except (FileNotFoundError, IOError):
            return False

    if args.no_config:
        print(
            "Ignoring default config file. You may be prompted for some missing settings.")
    elif args.config:
        config_file_name = args.config
        if load_config_file(config_file_name):
            print("Loaded config options from '%s'" % config_file_name)
        else:
            sys.exit("ERROR: Unable to find or open config file '%s'" %
                     config_file_name)
    else:
        config_file_name = default_config_file
        if load_config_file(config_file_name):
            print("Loaded options from default config file in '%s'" %
                  config_file_name)
        else:
            print("Default config file not found in '%s'" % config_file_name)
            print("You may be prompted for some missing settings.")

    if args.username:
        config.set('login', 'username', args.username)

    if args.password:
        config.set('login', 'password', args.password)

    if args.source:
        config.set('source', 'repository', args.source)

    if args.target:
        config.set('target', 'repositories', args.targets)

    # Make sure no required config values are missing
    if not config.has_option('source', 'repository'):
        sys.exit(
            "ERROR: There is no source repository specified either in the config file, or as an argument.")
    if not config.has_option('target', 'repositories'):
        sys.exit(
            "ERROR: There are no target repositories specified either in the config file, or as an argument.")

    config.set('source', 'url', f'https://api.github.com/repos/{config.get('source', 'repository')}')

    targets = json.loads(config.get("target", "repositories"))
    full_target_urls = []

    for target in targets:
        full_target_urls.append(f'https://api.github.com/repos/{target}')

    config.set('target', 'repositories', json.dumps(full_target_urls))

    return args.issues or []

def get_issues(issue_ids):
    # Argparser will prevent us from getting both issue ids and specifying issue state, so no duplicates will be added
    issues = []

    if (len(issue_ids) > 0):
        issues.extend(get_issues_by_id(config, 'source', issue_ids))
    else:
        issues.extend(get_issues_by_state(config, 'source', 'open'))

    # Sort issues based on their original `id` field
    # Confusing, but taken from http://stackoverflow.com/a/2878123/617937
    issues.sort(key=lambda x: x['number'])

    return issues


if __name__ == '__main__':

    repos = json.loads(config.get("target", "repositories"))
    issue_ids = init_config()
    issues = get_issues(issue_ids)

    for repo in repos:
        import_issues(config, issues, repo)

        project = ProjectBoard(config)
        project.create()
        project.create_columns()
        project.add_target_issues_to_backlog()
