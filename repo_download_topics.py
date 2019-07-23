#!/usr/bin/env python

import argparse
import sys
import subprocess
import json
import re
import mmap


def is_child(patch, patch_list):
    if "neededBy" not in patch:
        # the patch is not needed by any pacthes, which means the patch is on top of any patches
        return 1

    if 'neededBy' not in patch_list[patch['project']]:
	# the patch in the buffer is not needed by any patches
        return 0

    for commit in patch['dependsOn']:
	# if the patch is needed by a existing one, replace the existing one with the incoming patch
        if len([d for d in patch_list[patch['project']]["neededBy"] if d['number'] == commit['number']]) > 0:
            return 1

    return 0

def get_patch_from_topic(topic_query_json, manifest_file, is_get_open_only=True):
	patches = topic_query_json.splitlines()
	patch_list = dict()  # index by project name

	try:
		with open(manifest_file, 'r') as f:
			xml_content = f.read()
	except IOError as e:
		print("manifest is not found: {}".format(manifest_file))
		xml_content = None

	for line in patches:
		try:
			patch = json.loads(line)
			if "project" in patch and "currentPatchSet" in patch:
				if xml_content is not None and patch['project'] not in xml_content:
					# skip this project because it is not specified in manifest.xml of repo
					continue

				if is_get_open_only and patch["status"] != "NEW":
					# skip merged and abandoned patches
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
	topic_list = list(dict.fromkeys(topic_list))  # remove duplications

	s = ""
	for topic in topic_list:
		command = ['ssh', '-p', str(args.port), args.server, args.remote, 'query', '--format=JSON', '--dependencies', '--current-patch-set', 'topic:' + topic]
		print("querying '{}', '{}'".format(topic, " ".join(command)))
		try:
			commits = subprocess.check_output(command).decode('utf-8')
			if 'project' not in commits:
				print("warning: no patches for topic '{}'".format(topic))
			else:
				s = s + commits

		except subprocess.CalledProcessError as grepexc:
			print("error occured while excuting command: '{}'".format(" ".join(command)))
			print("error code {}".format(grepexc.returncode))
			sys.exit(1)

	patches = get_patch_from_topic(s, args.manifest ,not args.all_status)
	if len(patches) == 0:
		print("no open patches related to {}".format(args.topic))
		sys.exit(0)

	command = ""
	print("[projects related to {}]".format(args.topic))
	for i, project in enumerate(patches, start=1):
		command = command + "repo download " + project + " " + patches[project]['number'] + "/" + patches[project]['currentPatchSet']['number'] + ";"
		print("[{}]\t{}\t{} {}/{}\t".format(i, patches[project]['status'], project, patches[project]['number'], patches[project]['currentPatchSet']['number']))

	print("[download command]")
	print(command)

	if args.download:
		print("[downloading patches]")
		for project in patches:
			subprocess.call(["repo", "download", project, patches[project]['number'] + "/" + patches[project]['currentPatchSet']['number']])


def check_arg(args=None):
	parser = argparse.ArgumentParser(description='repo download topics')
	parser.add_argument('-t', '--topic', help='you can assign multiple topics by putting comma between them\nex: T-1234,T-5678', required=True)
	parser.add_argument('-s', '--server', help='gerrit server', required=True)
	parser.add_argument('-r', '--remote', help='git remote name', default="gerrit")
	parser.add_argument('-p', '--port', help='ssh port', default=29418)
	parser.add_argument('-m', '--manifest', help='manifest xml of the (repo) project', default=".repo/manifest.xml")
	parser.add_argument('--download', help='download patches after querying', dest='download', action='store_true')
	parser.add_argument('--all_status', help='also download abandoned and merged patches', dest='all_status', action='store_true')
	return parser.parse_args(args)

if __name__ == '__main__':
    download_topics(check_arg(sys.argv[1:]))
