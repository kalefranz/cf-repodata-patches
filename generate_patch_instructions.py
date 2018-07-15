# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from os.path import dirname, join, isdir
import sys

import requests


def _extract_and_remove_vc_feature(record):
    features = record.get('features', '').split()
    vc_features = tuple(f for f in features if f.startswith('vc'))
    if not vc_features:
        return None
    non_vc_features = tuple(f for f in features if f not in vc_features)
    vc_version = int(vc_features[0][2:])  # throw away all but the first
    if non_vc_features:
        record['features'] = ' '.join(non_vc_features)
    else:
        del record['features']
    return vc_version


def _patch_repodata(repodata, subdir):
    instructions = {
        "patch_instructions_version": 1,
        "packages": {},
        "revoke": [],
        "remove": [],
    }
    if subdir.startswith("win-"):
        for fn, record in repodata["packages"].items():
            if record['name'] == 'python':
                old_record = record.copy()
                record.pop('track_features', None)
                if not any(d.startswith('vc') for d in record['depends']):
                    dep = {
                        '2.6': 'vc 9.*',
                        '2.7': 'vc 9.*',
                        '3.3': 'vc 10.*',
                        '3.4': 'vc 10.*',
                        '3.5': 'vc 14.*',
                        '3.6': 'vc 14.*',
                        '3.7': 'vc 14.*',
                    }[record['version'][:3]]
                    record['depends'].append(dep)
                if old_record != record:
                    instructions["packages"][fn] = record
            elif 'vc' in record.get('features', ''):
                old_record = record.copy()
                vc_version = _extract_and_remove_vc_feature(record)
                if not any(d.startswith('vc') for d in record['depends']):
                    record['depends'].append('vc %d.*' % vc_version)
                if old_record != record:
                    instructions["packages"][fn] = record
    return instructions


def main():
    channel_alias = "https://conda-web.anaconda.org"
    channel_names = (
        "conda-forge",
        # "conda-forge/label/archive",
    )
    subdirs = (
        "linux-64",
        "linux-ppc64le",
        "linux-armv7l",
        "win-64",
        "osx-64",
        "noarch",
    )
    for channel_name in channel_names:
        for subdir in subdirs:
            repodata_url = "/".join((channel_alias, channel_name, subdir, "repodata.json"))
            response = requests.get(repodata_url)
            response.raise_for_status()
            patch_instructions = _patch_repodata(response.json(), subdir)
            patch_instructions_path = join(dirname(__file__), channel_name, subdir,
                                           "patch_instructions.json")
            if not isdir(dirname(patch_instructions_path)):
                os.makedirs(dirname(patch_instructions_path))
            with open(patch_instructions_path, 'w') as fh:
                json.dump(patch_instructions, fh, indent=2, sort_keys=True, separators=(',', ': '))
    return 0


if __name__ == "__main__":
    sys.exit(main())

