from threading import Thread
import time
import sys
import unittest
from unittest import skip

try:
    from tornado.ioloop import IOLoop
except ImportError:
    raise unittest.SkipTest("Tornado not installed")

try:
    from selenium import webdriver
except ImportError:
    raise unittest.SkipTest("selenium not installed")

# Local imports.
from jigna.utils.web import get_free_port
from test_jigna_qt import TestJignaQt, Person, body_html


def patch_sys_modules():
    backup = sys.modules.copy()
    for name in list(sys.modules.keys()):
        if 'PySide' in name or 'PyQt' in name:
            del sys.modules[name]

    return backup

def restore_sys_modules(backup):
    sys.modules = backup

def assert_no_qt_in_sys_modules():
    for name in list(sys.modules.keys()):
        if 'PySide' in name or 'PyQt' in name:
            raise AssertionError("Qt import found: %s."%name)


class TestJignaWebSync(TestJignaQt):
    @classmethod
    def setUpClass(cls, async=False):

        cls._backup_modules = patch_sys_modules()

        from jigna.template import Template
        from jigna.web_app import WebApp
        ioloop = IOLoop.instance()
        fred = Person(name='Fred', age=42)
        template = Template(body_html=body_html, async=async)
        port = get_free_port()
        app = WebApp(template=template, context={'model':fred})
        app.listen(port)

        # Start the tornado server in a different thread so that we can write
        # test statements here in the main loop
        t = Thread(target=ioloop.start)
        t.setDaemon(True)
        t.start()

        browser = webdriver.Firefox()
        browser.get('http://localhost:%d'%port)
        cls.app = app
        cls.fred = fred
        cls.browser = browser

    @classmethod
    def tearDownClass(cls):
        from tornado.ioloop import IOLoop
        cls.browser.quit()
        IOLoop.instance().stop()
        time.sleep(1)

        # Smells a bit but doing this here ensures that none of the tested
        # cases imports Qt.
        assert_no_qt_in_sys_modules()

        restore_sys_modules(cls._backup_modules)

    def setUp(self):
        cls = self.__class__
        self.app = cls.app
        self.browser = cls.browser
        self.fred = cls.fred
        self.fred.spouse = None
        self.fred.fruits = []
        self.fred.friends = []
        # Wait for the model to be setup before running the tests.
        self.get_attribute('jigna.models.model.name', None)

    def execute_js(self, js):
        return self.browser.execute_script(js)

    def reset_user_var(self):
        self.execute_js("jigna.user = undefined;")

    def get_attribute(self, js, expect):
        self.reset_user_var()
        get_js = """jigna.wait_for(\'%s\').done(function(result)
                                {jigna.user = result;})"""%js
        self.execute_js(get_js)

        check_js = "return jigna.user;"
        result = self.execute_js(check_js)
        count = 0
        while result is None and expect is not None and count < 10:
            time.sleep(0.1)
            result = self.execute_js(check_js)
            count += 1
        self.reset_user_var()
        return result

    def assertJSEqual(self, js, value):
        result = self.get_attribute(js, value)
        if isinstance(value, (list, tuple)):
            msg = "Lengths different: expected %d, got %d" % \
                (len(value), len(result))
            self.assertEqual(len(value), len(result), msg)
            for index in range(len(value)):
                expect = value[index]
                got = result[index]
                if got != expect:
                    got = self.get_attribute(js+"[%d]"%index, expect)
                msg = "%s[%s] != %s, got %s"%(js, index, expect, got)
                self.assertEqual(expect, got, msg)
        else:
            msg = "%s != %s, got %s"%(js, value, result)
            self.assertEqual(value, result, msg)

    def test_instance_trait(self):
        # Overridden to work with the web backend.
        self.assertJSEqual("jigna.models.model.spouse", None)
        wilma = Person(name='Wilma', age=40)
        self.fred.spouse = wilma
        self.assertJSEqual("jigna.models.model.spouse.name", 'Wilma')
        self.assertJSEqual("jigna.models.model.spouse.age", 40)

        # Set in the JS side.
        self.execute_js("jigna.models.model.spouse.name = 'Wilmaji'")
        self.execute_js("jigna.models.model.spouse.age = 41")
        self.assertEqual(wilma.name, "Wilmaji")
        self.assertEqual(wilma.age, 41)

    def test_reload_works_correctly(self):
        # Given
        fred = self.fred
        fred.fruits = ["peach", "pear"]
        dino = Person(name="Dino", age=10)
        fred.friends = [dino]
        fred.phonebook = {'joe' : 123, 'joan' : 345}
        wilma = Person(name='Wilma', age=40)
        fred.spouse = wilma

        # When
        self.execute_js("window.location.reload();")
        time.sleep(0.5)

        # Then
        self.assertJSEqual("jigna.models.model.name", fred.name)
        self.assertJSEqual("jigna.models.model.friends[0].name", "Dino")
        self.assertJSEqual("jigna.models.model.friends[0].age", 10)
        self.assertJSEqual("jigna.models.model.phonebook.joe", 123)
        self.assertJSEqual("jigna.models.model.phonebook.joan", 345)
        self.assertJSEqual("jigna.models.model.phonebook", fred.phonebook)
        self.assertJSEqual("jigna.models.model.fruits", fred.fruits)
        self.assertJSEqual("jigna.models.model.spouse.name", 'Wilma')
        self.assertJSEqual("jigna.models.model.spouse.age", 40)

# Delete this so running just this file does not run all the tests.
del TestJignaQt

if __name__ == "__main__":
    unittest.main()

#### EOF ######################################################################
