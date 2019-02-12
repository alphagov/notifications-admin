#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
from app.utils import AgreementInfo

_dir_path = os.path.dirname(os.path.realpath(__file__))


with open('{}/app/domains.yml'.format(_dir_path)) as source:

    data = yaml.load(source)

    for domain, details in data.items():
        if isinstance(details, dict):
            # We’re looking at the canonical domain
            data[domain]['domains'] = [domain]

    for domain, details in data.items():
        if isinstance(details, str):
            # This is an alias, let’s add it to the canonical domain
            data[AgreementInfo(domain).canonical_domain]['domains'].append(domain)

    out_data = [
        details for domain, details in data.items()
        if isinstance(details, dict)
    ]

    print(yaml.dump(out_data))  # noqa
