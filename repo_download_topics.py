#!/usr/bin/env python

import argparse
import sys
import subprocess
import json
import re
import mmap


def is_child(patch, patch_list):
    if "neededBy" not in patch:
        # the patch is not needed by any patches, which means the patch is on top of any patches
        return 1

    if 'neededBy' not in patch_list[patch['project']]:
        # the patch in the buffer is not needed by any patches
        return 0

    for commit in patch['dependsOn']:
        # if the patch is needed by an existing one, replace the existing one with the incoming patch
        if len([d for d in patch_list[patch['project']]["neededBy"] if d['number'] == commit['number']]) > 0:
            return 1

    return 0


def get_patch_from_topic(topic_query_json, manifest_file, prefix_truncation, is_get_open_only=True):
    patches = topic_query_json.splitlines()
    patch_list = dict()  # index by project name

    try:
        with open(manifest_file, 'r') as f:
            xml_content = f.read()
    except IOError as e:
        print("Manifest is not found: {}".format(manifest_file))
        xml_content = None

    for line in patches:
        try:
            patch = json.loads(line)
            if "project" in patch and "currentPatchSet" in patch:
                # Check and truncate project prefix
                original_project = patch["project"]
                if patch["project"].startswith(prefix_truncation):
                    truncated_project = patch["project"][len(prefix_truncation):]
                    print("Prefix '{}' found in project '{}'. Truncated to '{}'".format(prefix_truncation, patch["project"], truncated_project))
                    patch["project"] = truncated_project

                # After truncating the prefix, match with manifest.xml
                if xml_content is not None and patch['project'] not in xml_content:
                    # Skip this project because it is not specified in manifest.xml of repo
                    print(f"Project '{patch['project']}' (from original '{original_project}') not found in manifest, skipping.")
                    continue

                if is_get_open_only and patch["status"] != "NEW":
                    # Skip merged and abandoned patches
                    continue

                if patch["project"] in patch_list:
                    number = patch_list[patch['project']]['number']
                    if is_child(patch, patch_list):
                        patch_list[patch["project"]] = patch
                else:
                    patch_list[patch["project"]] = patch

        except:
            pass

    return patch_list


def download_topics(args):
    topic_list = re.split(',', args.topic)
    topic_list = list(dict.fromkeys(topic_list))  # Remove duplications

    s = ""
    for topic in topic_list:
        command = ['ssh', '-p', str(args.port), args.server, args.remote, 'query', '--format=JSON', '--dependencies', '--current-patch-set', 'topic:' + topic]
        print("Querying '{}', '{}'".format(topic, " ".join(command)))
        try:
            commits = subprocess.check_output(command).decode('utf-8')
            if 'project' not in commits:
                print("Warning: no patches for topic '{}'".format(topic))
            else:
                s = s + commits

        except subprocess.CalledProcessError as grepexc:
            print("Error occurred while executing command: '{}'".format(" ".join(command)))
            print("Error code {}".format(grepexc.returncode))
            sys.exit(1)

    patches = get_patch_from_topic(s, args.manifest, args.prefix_truncation, not args.all_status)
    if len(patches) == 0:
        print("No open patches related to {}".format(args.topic))
        sys.exit(0)

    command = ""
    print("[Projects related to {}]".format(args.topic))
    for i, project in enumerate(patches, start=1):
        truncated_project = patches[project]['project']  # Use the truncated project name
        command = command + f"repo download {truncated_project} {patches[project]['number']}/{patches[project]['currentPatchSet']['number']};"
        print("[{}]\t{}\t{} {}/{}\t".format(i, patches[project]['status'], truncated_project, patches[project]['number'], patches[project]['currentPatchSet']['number']))

    print("[Download command]")
    print(command)

    if args.download:
        print("[Downloading patches]")
        for project in patches:
            truncated_project = patches[project]['project']  # Use the truncated project name
            subprocess.call(["repo", "download", truncated_project, patches[project]['number'] + "/" + patches[project]['currentPatchSet']['number']])


def check_arg(args=None):
    parser = argparse.ArgumentParser(description='repo download topics')
    parser.add_argument('-t', '--topic', help='You can assign multiple topics by putting a comma between them\nex: T-1234,T-5678', required=True)
    parser.add_argument('-s', '--server', help='Gerrit server', required=True)
    parser.add_argument('-r', '--remote', help='Git remote name', default="gerrit")
    parser.add_argument('-p', '--port', help='SSH port', default=29418)
    parser.add_argument('-m', '--manifest', help='Manifest XML of the (repo) project', default=".repo/manifest.xml")
    parser.add_argument('--download', help='Download patches after querying', dest='download', action='store_true')
    parser.add_argument('--all_status', help='Also download abandoned and merged patches', dest='all_status', action='store_true')
    parser.add_argument('--prefix_truncation', help='Prefix to truncate from project name', default="")  # Add new argument for prefix truncation
    return parser.parse_args(args)


if __name__ == '__main__':
    download_topics(check_arg(sys.argv[1:]))
