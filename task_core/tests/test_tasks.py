"""unit tests of tasks"""
import stevedore.exception
import unittest
import yaml
from unittest import mock
from task_core import tasks


DUMMY_PRINT_TASK_DATA = """
id: print
driver: print
message: "message from service a"
"""

DUMMY_SERVICE_TASK_DATA = """
id: run
action: run
provides:
  - service-a.run
requires:
  - service-a.init
jobs:
  - echo: "service a run"
"""

DUMMY_DIRECTOR_SERVICE_TASK_DATA = """
id: setup
action: run
provides:
  - chronyd.init
requires:
  - base.init
jobs:
  - RUN: dnf -y install chrony crudini
  - RUN: systemctl start chronyd
  - RUN: systemctl enable chronyd
"""


class TestTaskManager(unittest.TestCase):
    """Test TaskManager object"""

    def test_get_instance(self):
        """test instance"""
        obj = tasks.TaskManager.instance()
        self.assertEqual(tasks.TaskManager._instance, obj)
        self.assertRaises(RuntimeError, tasks.TaskManager)

    def test_get_driver(self):
        """test stevedore driver"""
        obj = tasks.TaskManager.instance()
        self.assertTrue(obj.get_driver("service"), tasks.ServiceTask)
        self.assertTrue(obj.get_driver("director_service"), tasks.DirectorServiceTask)
        self.assertTrue(obj.get_driver("print"), tasks.PrintTask)
        self.assertRaises(stevedore.exception.NoMatches, obj.get_driver, "doesnotexist")


class TestServiceTask(unittest.TestCase):
    """test ServiceTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_SERVICE_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "run")
        self.assertEqual(obj.action, "run")
        self.assertEqual(obj.jobs, [{"echo": "service a run"}])

    @mock.patch("time.sleep")
    def test_execute(self, mock_sleep):
        """test execute"""
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)

    @mock.patch("time.sleep")
    def test_execute_bad_job(self, mock_sleep):
        """test execute with bad job definition"""
        self.data["jobs"] = [{"bad": "job"}]
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)


class TestDirectorServiceTask(unittest.TestCase):
    """test DirectorServiceTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_DIRECTOR_SERVICE_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.PrintTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "setup")
        self.assertEqual(obj.action, "run")
        self.assertEqual(obj.jobs, self.data["jobs"])

    @mock.patch("director.mixin.Mixin")
    def test_execute(self, mock_mixin):
        """test execute"""
        obj = tasks.DirectorServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)

    @mock.patch("director.mixin.Mixin")
    def test_execute_fail(self, mock_mixin):
        """test execute"""
        mixin_obj = mock.MagicMock()
        mock_mixin.return_value = mixin_obj
        mixin_obj.exec_orchestrations.return_value = [b"foo"]
        mixin_obj.poll_job.return_value = (False, "meh")
        obj = tasks.DirectorServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertFalse(result[0].status)
        mixin_obj.exec_orchestrations.assert_called_once_with(
            user_exec=mock.ANY,
            orchestrations=self.data.get("jobs"),
            defined_targets=["host-a", "host-b"],
            raw_return=True,
        )
        mixin_obj.poll_job.assert_called_once_with(job_id="foo")


class TestPrintTask(unittest.TestCase):
    """test PrintTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_PRINT_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.PrintTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "print")
        self.assertEqual(obj.action, None)
        self.assertEqual(obj.jobs, [])
        self.assertEqual(obj.message, "message from service a")

    def test_execute(self):
        """test execute"""
        obj = tasks.PrintTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(result[0].data, {})