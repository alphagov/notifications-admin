#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
from itertools import chain
from operator import itemgetter
from sys import argv
from app.utils import AgreementInfo

_dir_path = os.path.dirname(os.path.realpath(__file__))


if len(argv) < 2:
    raise TypeError('Must specify `orgs` or `domains` as the first argument to this script')


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

    if argv[1] == 'orgs':
        print(yaml.dump(out_data))  # noqa
    elif argv[1] == 'domains':
        print(  # noqa
            sorted(
                set(
                    chain.from_iterable(
                        map(
                            itemgetter('domains'), out_data
                        )
                    )
                )
            )
        )
    else:
        raise TypeError('Must specify `orgs` or `domains` as the first argument to this script')
