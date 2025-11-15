"""
Unit tests for Object Runtime

Test-Driven Development: These tests are written FIRST, before implementation.
They define the expected behavior of the integrated Object Runtime.

Object Runtime:
- Loads endpoints
- Injects logger and state manager
- Executes methods
- Logs all operations
- Versions code changes
- Provides introspection
"""

import pytest
import tempfile
import shutil
from pathlib import Path


class TestObjectRuntimeBasics:
    """Test basic object runtime functionality"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_load_object(self):
        """Should load an endpoint as an object"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)

        # Load the hello endpoint
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        assert obj is not None
        assert obj.object_id == 'hello'

    def test_execute_object_method(self):
        """Should execute object methods"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        # Execute GET method
        result = obj.execute('GET', {})

        assert result['status'] == 'ok'
        assert 'Hello' in result['message']

    def test_object_logs_to_itself(self):
        """Should automatically log all method executions"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        # Execute method
        obj.execute('GET', {'user_id': 'user-123'})

        # Check logs
        logs = obj.get_logs()
        assert len(logs) >= 1

        # Should have logged the execution (check INFO level logs)
        info_logs = [log for log in logs if log['level'] == 'INFO']
        assert len(info_logs) >= 1

        execution_log = info_logs[0]
        assert execution_log['method'] == 'GET'
        assert execution_log['user_id'] == 'user-123'

    def test_object_has_state(self):
        """Should provide state management to objects"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)

        # Load counter endpoint (uses state)
        obj = runtime.load_object('examples/basics/counter.py')

        # Execute GET (increments counter)
        result1 = obj.execute('GET', {})
        result2 = obj.execute('GET', {})
        result3 = obj.execute('GET', {})

        # Counter should increment
        assert result1['count'] == 1
        assert result2['count'] == 2
        assert result3['count'] == 3

    def test_object_state_persists(self):
        """Should persist state across reloads"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('examples/basics/counter.py')

        # Increment counter
        obj.execute('GET', {})
        obj.execute('GET', {})

        # Reload object (simulate restart)
        obj2 = runtime.load_object('examples/basics/counter.py')
        result = obj2.execute('GET', {})

        # Should continue from where we left off
        assert result['count'] == 3


class TestObjectVersioning:
    """Test automatic versioning of object code"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_save_version_on_modification(self):
        """Should automatically version code when modified"""
        from object_primitive_core.object_runtime import ObjectRuntime
        import shutil

        # Copy hello.py to temp dir
        hello_src = Path('tests/fixtures/endpoints/hello.py')
        hello_temp = self.temp_dir / 'hello.py'
        shutil.copy(hello_src, hello_temp)

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object(str(hello_temp))

        # Modify the object's code
        new_code = """
def GET(request):
    return {'status': 'ok', 'message': 'Modified!'}

__endpoint__ = {'name': 'hello', 'version': '2.0.0'}
"""
        obj.update_code(new_code, author='test_user', message='Updated hello')

        # Should have created a version
        history = obj.get_version_history()
        assert len(history) >= 1

    def test_rollback_to_previous_version(self):
        """Should be able to rollback to previous version"""
        from object_primitive_core.object_runtime import ObjectRuntime
        import shutil as sh

        # Copy hello.py to temp dir
        hello_src = Path('tests/fixtures/endpoints/hello.py')
        hello_temp = self.temp_dir / 'hello.py'
        sh.copy(hello_src, hello_temp)

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object(str(hello_temp))

        # Execute original
        result1 = obj.execute('GET', {})
        original_message = result1['message']

        # Modify code
        new_code = """
def GET(request):
    return {'status': 'ok', 'message': 'MODIFIED VERSION'}

__endpoint__ = {'name': 'hello', 'version': '2.0.0'}
"""
        obj.update_code(new_code, author='test', message='Modification')

        # Verify modification worked
        result2 = obj.execute('GET', {})
        assert result2['message'] == 'MODIFIED VERSION'

        # Rollback to version 1
        obj.rollback_to_version(1, author='test', message='Rollback')

        # Should execute original code
        result3 = obj.execute('GET', {})
        assert result3['message'] == original_message


class TestObjectIntrospection:
    """Test object introspection capabilities"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_object_metadata(self):
        """Should provide object metadata"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        metadata = obj.get_metadata()

        assert metadata['name'] == 'hello'
        assert 'description' in metadata
        assert 'version' in metadata

    def test_get_object_source_code(self):
        """Should return object's source code"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        source = obj.get_source_code()

        assert 'def GET(request):' in source
        assert '__endpoint__' in source

    def test_get_object_logs(self):
        """Should return object's logs"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('tests/fixtures/endpoints/hello.py')

        # Execute to generate logs
        obj.execute('GET', {'user_id': 'user-123'})
        obj.execute('POST', {'name': 'Alice'})

        logs = obj.get_logs()

        assert len(logs) >= 2
        assert any(log['method'] == 'GET' for log in logs)
        assert any(log['method'] == 'POST' for log in logs)

    def test_get_object_state(self):
        """Should return object's current state"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)
        obj = runtime.load_object('examples/basics/counter.py')

        # Increment counter
        obj.execute('GET', {})
        obj.execute('GET', {})

        state = obj.get_state()

        assert 'count' in state
        assert state['count'] == 2


class TestObjectIsolation:
    """Test that objects are properly isolated"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_objects_have_separate_logs(self):
        """Should keep logs separate for different objects"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)

        obj1 = runtime.load_object('tests/fixtures/endpoints/hello.py')
        obj2 = runtime.load_object('tests/fixtures/endpoints/calculator.py')

        # Execute both
        obj1.execute('GET', {})
        obj2.execute('POST', {'operation': 'add', 'a': 1, 'b': 2})

        # Logs should be separate
        logs1 = obj1.get_logs()
        logs2 = obj2.get_logs()

        assert len(logs1) >= 1
        assert len(logs2) >= 1
        assert logs1[0] != logs2[0]  # Different logs

    def test_objects_have_separate_state(self):
        """Should keep state separate for different counter instances"""
        from object_primitive_core.object_runtime import ObjectRuntime

        runtime = ObjectRuntime(base_dir=self.temp_dir)

        # Load counter twice (simulate two different counter endpoints)
        # We'll need to copy the file with different names
        import shutil as sh
        counter_src = Path('examples/basics/counter.py')
        counter1 = self.temp_dir / 'counter1.py'
        counter2 = self.temp_dir / 'counter2.py'

        sh.copy(counter_src, counter1)
        sh.copy(counter_src, counter2)

        obj1 = runtime.load_object(str(counter1))
        obj2 = runtime.load_object(str(counter2))

        # Increment obj1 three times
        obj1.execute('GET', {})
        obj1.execute('GET', {})
        obj1.execute('GET', {})

        # Increment obj2 once
        obj2.execute('GET', {})

        # Should have different counts
        state1 = obj1.get_state()
        state2 = obj2.get_state()

        assert state1['count'] == 3
        assert state2['count'] == 1
