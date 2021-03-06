import pytest
import re

from pytest_matrix import TestMatrixMixin, exceptions


def test_generate(testdir):

    # create a temporary pytest test file
    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin
    
    def my_func(a, b):    
        return a + b
    
    class TestSuite(TestMatrixMixin):
        def test_my_fn(self, arg_first, arg_second, result):
            assert my_func(arg_first, arg_second) == result

        MY_FN_FIXTURES_NAMES = ['arg_first']
        MY_FN_FIXTURES = [
            {
                'arg_first': ['val_a', 'val_b'],
            }
        ]

        @pytest.fixture
        def arg_first_val_a(self):
            return 'val_1'

        @pytest.fixture
        def arg_first_val_b(self):
            return 'val_2'

        @pytest.fixture
        def arg_second(self):
            return 'val'

        @pytest.fixture
        def result(self, arg_first, arg_second):
            return arg_first + arg_second
    """
    testdir.makepyfile(source)
    result = testdir.runpytest()

    result.assert_outcomes(passed=2)

    expected_functions = {
        'test_my_fn[arg_first_val_a]',
        'test_my_fn[arg_first_val_b]',
    }
    items = testdir.getitems(source)
    collected_tests = {f.name for f in items}

    assert expected_functions == collected_tests


def test_generate_from_marker(testdir):

    # create a temporary pytest test file
    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin
    
    
    def my_func(a, b):    
        return a + b
    
    @pytest.mark.matrix(names=['arg_first'], combs=[
            {
                'arg_first': ['val_a', 'val_b']
            }
        ])
    def test_my_fn(arg_first, arg_second, result):
        assert my_func(arg_first, arg_second) == result

    @pytest.fixture
    def arg_first_val_a():
        return 'val_1'

    @pytest.fixture
    def arg_first_val_b():
        return 'val_2'

    @pytest.fixture
    def arg_second():
        return 'val'

    @pytest.fixture
    def result(arg_first, arg_second):
        return arg_first + arg_second
    """
    testdir.makepyfile(source)
    result = testdir.runpytest()

    result.assert_outcomes(passed=2)

    expected_functions = {
        'test_my_fn[arg_first_val_a]',
        'test_my_fn[arg_first_val_b]',
    }
    items = testdir.getitems(source)
    collected_tests = {f.name for f in items}

    assert expected_functions == collected_tests




def test_missing_fixture_names():
    class Test(TestMatrixMixin):

        FN_FIXTURES = [{'x': ['x']}]

        def test_fn(self):
            pass
    assert Test.FN_FIXTURES_NAMES == ['x']


def test_missing_fixtures_definition():
    with pytest.raises(exceptions.FixturesCombinationsMissing):
        class Test(TestMatrixMixin):

            FN_FIXTURES_NAMES = ['x']

            def test_fn(self):
                pass


def test_missing_fixture_names_inherited():
    class TestMixin(TestMatrixMixin):
        IS_MIXIN = True

        def test_fn(self):
            pass

    class Test(TestMixin):
        FN_FIXTURES = [{'x': ['x']}]

    assert Test.FN_FIXTURES_NAMES == ['x']


def test_missing_fixtures_definition_inherited():
    with pytest.raises(exceptions.FixturesCombinationsMissing):
        class TestMixin(TestMatrixMixin):
            IS_MIXIN = True

            def test_fn(self):
                pass

        class Test(TestMixin):
            FN_FIXTURES_NAMES = ['x']


@pytest.mark.parametrize(argnames='names', ids=['more', 'less'],
                         argvalues=[['a', 'b', 'c'], ['a']])
def test_invalid_fixtures_keys(names):
    with pytest.raises(exceptions.InvalidFixturesCombinationsKeys):
        class Test(TestMatrixMixin):

            FN_FIXTURES_NAMES = names
            FN_FIXTURES = [
                {
                    'a': ['a'],
                    'b': ['b'],
                }
            ]

            def test_fn(self):
                pass


def test_not_generate(testdir):
    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin

    class TestMixin(TestMatrixMixin):
        IS_MIXIN = True
        FN_FIXTURES = [{'x': ['x']}]
        FN_FIXTURES_NAMES = ['x']

        def test_fn(self):
            pass

    class TestFirst(TestMixin):
        NOT_GENERATE_TESTS = ['test_fn']
        
    class TestOtherTest(TestFirst):
        FN_FIXTURES = [{'y': ['x']}]
        FN_FIXTURES_NAMES = ['y']
        
        @pytest.fixture
        def y_x(self):
            pass
    """
    testdir.makepyfile(source)
    result = testdir.runpytest()

    result.assert_outcomes(passed=2)

    items = testdir.getitems(source)
    assert {(f.name, f.cls.__name__) for f in items} == {('test_fn[y_x]', 'TestOtherTest'),
                                                         ('test_fn', "TestFirst")}


def test_skip(testdir):
    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin

    class TestMixin(TestMatrixMixin):
        IS_MIXIN = True
        FN_FIXTURES = [{'x': ['x']}]
        FN_FIXTURES_NAMES = ['x']

        def test_fn(self):
            pass

    class TestFirst(TestMixin):
        SKIP_TESTS = ['test_fn']
        
    class TestOtherTest(TestFirst):
        FN_FIXTURES = [{'y': ['x']}]
        FN_FIXTURES_NAMES = ['y']
        
        @pytest.fixture
        def y_x(self):
            pass
    """
    path = testdir.makepyfile(source)
    result = testdir.runpytest("{path}".format_map(vars()))

    result.assert_outcomes(skipped=1, passed=1)

    items = testdir.getitems(source)
    assert {(f.name, f.cls.__name__) for f in items} == {('test_fn[y_x]', 'TestOtherTest'),
                                                         ('test_fn', "TestFirst")}


@pytest.mark.parametrize(
    'variable, result', (('#1', 1), ('@1_0', '"1_0"'), ('normal_fixture', '"fixture_val"'))
)
def test_simple_fixture(testdir, variable, result):

    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin
    
    
    @pytest.fixture
    def x_attr_normal_fixture():
        return 'fixture_val'
            
    
    @pytest.mark.matrix(names=['x_attr'], combs=[
            {{
                'x_attr': ['{variable}']
            }}
        ])
    def test_my_fn(x_attr):
        assert x_attr == {result}
    

    class TestMixin(TestMatrixMixin):
        FN_FIXTURES = [{{'x_attr': ['{variable}']}}]
        FN_FIXTURES_NAMES = ['x_attr']

        def test_fn(self, x_attr):
            assert x_attr == {result}

    """.format_map(vars())
    path = testdir.makepyfile(source)
    result = testdir.runpytest(str(path))

    result.assert_outcomes(skipped=0, failed=0, passed=2)



@pytest.mark.skip('future')
@pytest.mark.parametrize(
    'variable, result', (('#1', 1),
                         ('@1_0', '"1_0"'),
                         ('$1', 2),
                         ('%1_0', '"1-0"'),
                         ('normal_fixture', '"fixture_val"'))
)
def test_simple_fixture_generator_class(testdir, variable, result):

    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin
    
    
    @pytest.fixture
    def x_attr_normal_fixture():
        return 'fixture_val'
            
    
    class TestMixin(TestMatrixMixin):
        FN_FIXTURES = [{{'x_attr': ['{variable}']}}]
        FN_FIXTURES_NAMES = ['x_attr']
        FN_FIXTURES_FACTORIES = {{
            '$': lambda x: x + 1,
            '%': lambda s: s.replace('_', '-'),
        }}

        def test_fn(self, x_attr):
            assert x_attr == {result}

    """.format_map(vars())
    path = testdir.makepyfile(source)
    result = testdir.runpytest(str(path))

    result.assert_outcomes(skipped=0, failed=0, passed=1)


@pytest.mark.skip('future')
@pytest.mark.parametrize(
    'variable, result', (('#1', 1),
                         ('@1_0', '"1_0"'),
                         ('$1', 2),
                         ('%1_0', '"1-0"'),
                         ('normal_fixture', '"fixture_val"'))
)
def test_simple_fixture_generator_function(testdir, variable, result):

    source = """
    import pytest
    from pytest_matrix import TestMatrixMixin
    
    
    @pytest.fixture
    def x_attr_normal_fixture():
        return 'fixture_val'
            
    
    @pytest.mark.matrix(
        names=['x_attr'], 
        combs=[
            {{
                'x_attr': ['{variable}']
            }}
        ],
        factories = {{
            '#': lambda x: x + 1,
            '%': lambda s: s.replace('_', '-'),
        }}
    )
    def test_my_fn(x_attr):
        assert x_attr == {result}
    

    class TestMixin(TestMatrixMixin):
        FN_FIXTURES = [{{'x_attr': ['{variable}']}}]
        FN_FIXTURES_NAMES = ['x_attr']

        def test_fn(self, x_attr):
            assert x_attr == {result}

    """.format_map(vars())
    path = testdir.makepyfile(source)
    result = testdir.runpytest(str(path))

    result.assert_outcomes(skipped=0, failed=0, passed=4)
