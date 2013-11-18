# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import shutil

import six

from ..benchmarks import Benchmarks
from ..config import Config
from ..console import console
from ..graph import Graph
from ..results import Results
from .. import util


class Publish(object):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser("publish", help="Publish results")

        parser.set_defaults(func=cls.run_from_args)

    @classmethod
    def run_from_args(cls, args):
        conf = Config.from_file(args.config)
        return cls.run(conf=conf)

    @classmethod
    def run(cls, conf):
        params = {}
        graphs = {}
        date_to_hash = {}
        machines = {}
        benchmark_names = set()

        if os.path.exists(conf.html_dir):
            shutil.rmtree(conf.html_dir)

        benchmarks = Benchmarks(conf.benchmark_dir)

        template_dir = os.path.join(
            os.path.dirname(__file__), '..', 'www')
        shutil.copytree(template_dir, conf.html_dir)

        dir_contents = []
        for root, dirs, files in os.walk(conf.results_dir):
            for filename in files:
                base, ext = os.path.splitext(filename)
                if ext == '.json':
                    dir_contents.append(os.path.join(root, filename))

        with console.group("Loading results", "green"):
            for path in dir_contents:
                filename = os.path.basename(path)
                if filename == 'machine.json':
                    d = util.load_json(path)
                    machines[d['machine']] = d
                    continue

                results = Results.load(path)

                date_to_hash[results.date] = results.commit_hash

                for key, val in six.iteritems(results.params):
                    params.setdefault(key, set())
                    params[key].add(val)

        with console.group("Loading graph data", "green"):
            console.set_nitems(len(dir_contents))
            for path in dir_contents:
                filename = os.path.basename(path)
                console.step(filename)

                if filename == 'machine.json':
                    continue

                results = Results.load(path)

                for key, val in six.iteritems(results.results):
                    for param in six.iterkeys(params):
                        if param not in results.params:
                            params[param].add(None)

                    benchmark_names.add(key)
                    graph = Graph(key, results.params, params)
                    if graph.path in graphs:
                        graph = graphs[graph.path]
                    else:
                        graphs[graph.path] = graph
                    graph.add_data_point(results.date, val)

        with console.group("Generating graphs", "green"):
            for graph in six.itervalues(graphs):
                graph.save(conf.html_dir)

        with console.group("Writing index", "green"):
            benchmark_map = {}
            for name in benchmark_names:
                benchmark_map[name] = benchmarks.get_code(name)
            for key, val in six.iteritems(params):
                val = list(val)
                val.sort()
                params[key] = val
            util.write_json(os.path.join(conf.html_dir, "index.json"), {
                'project': conf.project,
                'project_url': conf.project_url,
                'show_commit_url': conf.show_commit_url,
                'date_to_hash': date_to_hash,
                'params': params,
                'benchmark_names': benchmark_map,
                'machines': machines
            })
