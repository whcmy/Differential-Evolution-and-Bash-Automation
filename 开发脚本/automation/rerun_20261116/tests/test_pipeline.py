"""Pipeline integrity checks. Author: 殷明骏."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_batch import validate_batch


class PipelineChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)/'batch'
        shutil.copytree(ROOT/'tests/smoke_all30', self.directory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_complete_batch(self):
        with contextlib.redirect_stdout(io.StringIO()):
            validate_batch(self.directory)

    def test_tampered_summary_rejected(self):
        path = self.directory/'summary_report.txt'
        lines = path.read_text().splitlines()
        lines[2] = lines[2].rsplit(' ', 1)[0]+' 0.00000000000000000e+00'
        path.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(AssertionError):
            validate_batch(self.directory)

    def test_missing_function_rejected(self):
        (self.directory/'np50/DUAL/F30_run01.json').unlink()
        with self.assertRaises(AssertionError):
            validate_batch(self.directory)

    def test_changed_solution_rejected(self):
        path = self.directory/'np50/DUAL/F01_run01.json'
        row = json.loads(path.read_text()); row['x'][0] = 999
        path.write_text(json.dumps(row))
        with self.assertRaises(AssertionError):
            validate_batch(self.directory)

    def test_stale_output_rejected(self):
        p = subprocess.run([str(ROOT/'run_experiments.sh'), '--output', str(self.directory)], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(b'new directory', p.stderr)

    def test_invalid_inputs_rejected(self):
        for arguments in (['--budget', '149'], ['--workers', '0'], ['--seed', '-1'],
                          ['--budget', '1.5'], ['--unknown'], ['--seed']):
            with self.subTest(arguments=arguments):
                p = subprocess.run([str(ROOT/'run_experiments.sh'), *arguments], capture_output=True)
                self.assertEqual(p.returncode, 2)

    def test_manual_process_chain_has_no_cron(self):
        spec = importlib.util.spec_from_file_location('scheduler', ROOT/'cron/scheduler.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertFalse(any(Path(r['command'].split()[0]).name == 'cron'
                             for r in module.ancestors() if r['command']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
