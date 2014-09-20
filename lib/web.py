## Copyright 2014 ngld <ngld@tproxy.de>
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

from .qt import QtCore, QtWebKit


class WebBridge(QtCore.QObject):

    @QtCore.Slot(result=str)
    def getVersion(self):
        return '1.0'


class BrowserCtrl(object):
    _view = None
    _bridge = None

    def __init__(self, webView):
        self._view = webView
        self._bridge = WebBridge()

        settings = webView.settings()
        # settings.setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)  # May be necessary for YouTube videos...
        settings.setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
        settings.setAttribute(QtWebKit.QWebSettings.OfflineWebApplicationCacheEnabled, True)

        frame = webView.page().mainFrame()
        frame.javaScriptWindowObjectCleared.connect(self.insertBridge)

        webView.load(QtCore.QUrl('./html/welcome.html'))

    def insertBridge(self):
        frame = self._view.page().mainFrame()
        frame.addToJavaScriptWindowObject('fs2mod', self._bridge)
