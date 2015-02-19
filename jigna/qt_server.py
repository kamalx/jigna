#
# Enthought product code
#
# (C) Copyright 2013 Enthought, Inc., Austin, TX
# All right reserved.
#

""" Qt implementations of the Jigna Server and Bridge. """


# Standard library.
import json
from os.path import abspath, dirname, join

# Enthought library.
from traits.api import Any, Str, Instance
from traits.trait_notifiers import set_ui_handler

# Jigna library.
from jigna.core.qwebview import ProxyWebView
from jigna.core.wsgi import FileLoader
from jigna.server import Bridge, Server
from jigna.qt import QtWebKit, QtCore
from jigna.utils.gui import ui_handler


class QtBridge(Bridge):
    """ Qt (via QWebkit) bridge implementation. """

    #### 'Bridge' protocol ####################################################

    def send_event(self, event):
        """ Send an event. """

        try:
            jsonized_event = json.dumps(event)
        except TypeError:
            return

        if self.webview is None:
            raise RuntimeError("WebView does not exist")

        else:
            # This looks weird but this is how we fake an event being 'received'
            # on the client side when using the Qt bridge!
            self.webview.execute_js(
                'jigna.client.bridge.handle_event(%r);' % jsonized_event
            )

        return

    #### 'QtBridge' protocol ##################################################

    #: The 'WebViewContainer' that contains the QtWebKit malarky.
    webview = Any


class QtServer(Server):
    """ Qt (via QWebkit) server implementation. """

    #### 'Server' protocol ####################################################

    def __init__(self, **traits):
        """ Initialize the Qt server. This simply configures the widget to serve
        the Python model.
        """

        super(QtServer, self).__init__(**traits)


        self.webview.setHtml(self.html, QtCore.QUrl.fromLocalFile(self.base_url))
        self._enable_qwidget_embedding()

        # This statement makes sure that when we dispatch traits events on the
        # 'ui' thread, it passes on those events through the Qt layer.
        set_ui_handler(ui_handler)

        return

    #: The trait change dispatch mechanism to use when traits change.
    trait_change_dispatch = Str('ui')

    ### 'QtServer' protocol ##################################################

    #: The `ProxyWebView` object which specifies rules about how to handle
    #: different requests etc.
    webview = Instance(ProxyWebView)
    def _webview_default(self):
        return ProxyWebView(
            python_namespace = 'qt_bridge',
            callbacks        = [('handle_request', self.handle_request)],
            debug            = True,
            root_paths       = {
                'jigna': FileLoader(
                    root = join(abspath(dirname(__file__)), 'js', 'dist')
                )
            }
        )

    #### Private protocol #####################################################

    _bridge = Instance(QtBridge)
    def __bridge_default(self):
        return QtBridge(webview=self.webview)

    _plugin_factory = Instance('QtWebPluginFactory')

    def _enable_qwidget_embedding(self):
        """ Allow generic qwidgets to be embedded in the generated QWebView.
        """
        global_settings = QtWebKit.QWebSettings.globalSettings()
        global_settings.setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)

        self._plugin_factory = QtWebPluginFactory(context=self.context)
        self.webview.page().setPluginFactory(self._plugin_factory)


class QtWebPluginFactory(QtWebKit.QWebPluginFactory):

    MIME_TYPE = 'application/x-qwidget'

    def __init__(self, context):
        self.context = context
        super(self.__class__, self).__init__()

    def plugins(self):
        plugin = QtWebKit.QWebPluginFactory.Plugin()
        plugin.name = 'QWidget'
        mimeType = QtWebKit.QWebPluginFactory.MimeType()
        mimeType.name = self.MIME_TYPE
        plugin.mimeTypes = [mimeType]

        return [plugin]

    def create(self, mimeType, url, argNames, argVals):
        """ Return the QWidget to be embedded.
        """
        if mimeType != self.MIME_TYPE:
            return

        args = dict(zip(argNames, argVals))
        widget_factory = eval(args.get('widget-factory'), self.context)

        return widget_factory()

#### EOF ######################################################################
