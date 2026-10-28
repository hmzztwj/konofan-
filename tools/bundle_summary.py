# -*- coding: utf-8 -*-
"""Summarise bundles.csv: object type counts, bundle count, container path patterns, sample names."""
import csv, collections, re, os

p = r'F:\python_work\逆向\tools\out\bundles.csv'
types = collections.Counter()
files = set()
cabs = set()
deps = collections.Counter()
containers = collections.Counter()
cont_ext = collections.Counter()
names_by_type = collections.defaultdict(list)
sizes = {}

with open(p, encoding='utf-8-sig') as fh:
    r = csv.DictReader(fh)
    for row in r:
        files.add(row['file'])
        sizes[row['file']] = int(row['size'])
        if row['cab']:
            cabs.add(row['cab'])
        if row['deps']:
            for d in row['deps'].split(';'):
                deps[d] += 1
        t = row['type']
        if t == 'CONTAINER':
            containers[row['name']] += 1
            ext = os.path.splitext(row['name'])[1].lower() or '<none>'
            cont_ext[ext] += 1
        else:
            types[t] += 1
            if len(names_by_type[t]) < 8 and row['name']:
                names_by_type[t].append(row['name'])

print('bundles:', len(files), 'total size MB: %.1f' % (sum(sizes.values()) / 1048576))
print('cab names:', len(cabs), list(cabs)[:3])
print('\n== object types ==')
for t, n in types.most_common(40):
    print('%7d  %-22s e.g. %s' % (n, t, names_by_type[t][:4]))
print('\n== container extensions ==')
for e, n in cont_ext.most_common(20):
    print('%7d  %s' % (n, e))
print('\n== sample container paths ==')
for c, n in list(containers.items())[:25]:
    print('  ', c)
print('\n== deps sample ==')
for d, n in deps.most_common(10):
    print('%5d %s' % (n, d))
