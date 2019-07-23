# Project Title

Download patches from gerrit regarding certain topics

## Prerequisites

* Access to the gerrit server where you push commits - settings of ssh key
* Topics are set for necessary projects in the gerrit server

## Flows of the script

1. Query the gerrit server regarding certain topics by ssh (returns a JSON of all projects)

2. Go through all projects in the result and pickup the projects which have least dependency if there are more than 1 commits regarding a project

3. Only "open" projects are taken into account (merged, abandoned projects will be ignored by default)

4. If you provide a manifest.xml of the repo project, the script ignore projects that are not specified in it

5. A final report will be generated for review which contains the access to projects (with patch numbers) that you need to download as well as a final command of downloading projects using repo

## Usage

A basic example looks like

```
./repo_download_topics.py  -s gerrit.ee.sp -t NL-2504
```

With more than one topics

```
./repo_download_topics.py  -s gerrit.ee.sp -t NL-2504,NL-2522
```

Take projects with all status (merged, abandoned) into account

```
./repo_download_topics.py  -s gerrit.ee.sp --all_status -t NL-2504,NL-2522 
```

Download projects after querying (if you execute this script in the root folder of the repo project and no guarantee for downloading, for example, you have uncommited changes locally)

```
./repo_download_topics.py  -s gerrit.ee.sp --download -t NL-2504,NL-2522
```

## Test

This script is examined in Python 2.7.15+ and Python 3.6.8
