"""Create an isolated SYNTHETIC-only workspace for browser tests and CI."""
import argparse
import json
from pathlib import Path
import shutil


def prepare(output: Path) -> None:
    if output.exists():
        raise ValueError('Choose a new fixture directory; previous experiments are preserved.')
    root=Path(__file__).resolve().parents[1]
    demo=output/'data/demo'
    demo.mkdir(parents=True)
    for name in ('observations.csv','manifest.json'):
        shutil.copyfile(root/'data/demo'/name,demo/name)
    if not (root/'frontend/dist/index.html').exists():
        raise ValueError('Build the frontend before preparing the browser fixture.')
    shutil.copytree(root/'frontend/dist',output/'frontend/dist')
    folder=output/'experiments/ci-synthetic-1000'
    folder.mkdir(parents=True)
    (folder/'configuration.json').write_text(json.dumps(dict(
        fixture_label='SYNTHETIC TEST ONLY — no actual financial observations',
        source=dict(kind='synthetic',generator=dict(node_count=1000,edge_count=4000,seed=17)),
        expected_graph={'fixture_identity':'ci-synthetic-1000'})),encoding='utf-8')
    print('Synthetic-only fixture ready:',output.resolve())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    prepare(parser.parse_args().output)
