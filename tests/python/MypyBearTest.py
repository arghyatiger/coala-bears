from queue import Queue
from textwrap import dedent

from bears.python.MypyBear import MypyBear
from tests.BearTestHelper import generate_skip_decorator
from tests.LocalBearTestHelper import LocalBearTestHelper
from coalib.settings.Section import Section
from coalib.settings.Setting import Setting
from coalib.results.Result import Result
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coala_utils.ContextManagers import prepare_file


@generate_skip_decorator(MypyBear)
class MypyBearTest(LocalBearTestHelper):

    def setUp(self):
        self.section = Section('name')
        self.queue = Queue()
        self.uut = MypyBear(self.section, self.queue)

    def test_variable(self):
        self.check_validity(self.uut,
                            ['a = 1  # type: int'], valid=True)
        self.check_validity(self.uut,
                            ["a = 'abc'  # type: int"], valid=False)

    def test_call_sum(self):
        self.check_validity(self.uut,
                            ['sum([1, 2, 3])'], valid=True)
        self.check_validity(self.uut,
                            ['sum(1, 2, 3)'], valid=False)

    def test_py2(self):
        self.check_validity(self.uut,
                            ['print(123)'], valid=True)
        self.check_validity(self.uut,
                            ['print 123'], valid=False)
        self.section.append(Setting('language', 'Python 2'))
        self.check_validity(self.uut,
                            ['print 123'], valid=True)

    def test_py2_version(self):
        self.check_validity(self.uut,
                            ['print(123)'], valid=True)
        self.check_validity(self.uut,
                            ['print 123'], valid=False)
        self.section.append(Setting('python_version', '2.7'))
        self.check_validity(self.uut,
                            ['print 123'], valid=True)

    def test_bad_language(self):
        self.section.append(Setting('language', 'Piet'))
        self.check_validity(self.uut,
                            ['1 + 1'], valid=True)
        while not self.queue.empty():
            message = self.queue.get()
            msg = ('Language needs to be "Python", "Python 2" or '
                   '"Python 3". Assuming Python 3.')
            if message.message == msg:
                break
        else:
            assert False, 'Message not found'

    def test_check_untyped_function_bodies(self):
        source = dedent("""
            def foo():
                return 1 + "abc"
        """).splitlines()
        self.check_validity(self.uut, source, valid=True)
        self.section.append(Setting('check_untyped_function_bodies', 'true'))
        self.check_validity(self.uut, source, valid=False)

    def test_allow_untyped_functions(self):
        source = dedent("""
            def foo():
                pass
        """).splitlines()
        self.check_validity(self.uut, source, valid=True)
        self.section.append(Setting('allow_untyped_functions', 'false'))
        self.check_validity(self.uut, source, valid=False)

    def test_allow_untyped_calls(self):
        source = dedent("""
            def foo():
                pass

            foo()
        """).splitlines()
        self.check_validity(self.uut, source, valid=True)
        self.section.append(Setting('allow_untyped_calls', 'false'))
        self.check_validity(self.uut, source, valid=False)

    def test_strict_optional(self):
        source = dedent("""
            from typing import Optional, List

            def read_data_file(path: Optional[str]) -> List[str]:
                with open(path) as f:  # Error
                    return f.read().split(',')
        """).splitlines()
        self.check_validity(self.uut, source, valid=True)
        self.section.append(Setting('strict_optional', 'true'))
        self.check_validity(self.uut, source, valid=False)

    def test_discarded_note(self):
        source = dedent("""
            def f() -> None:
                1 + "a"
        """).splitlines()
        prepared = prepare_file(source, filename=None, create_tempfile=True)
        with prepared as (file, fname):
            results = [
                Result.from_values(
                    message=(
                        'Unsupported operand types for + ("int" and "str")'),
                    file=fname,
                    line=3,
                    origin=self.uut,
                    severity=RESULT_SEVERITY.MAJOR,
                )
            ]
            self.check_results(self.uut, source, results=results,
                               filename=fname, create_tempfile=False)
