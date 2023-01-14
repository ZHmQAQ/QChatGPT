# 插件管理模块
import logging
import importlib
import pkgutil
import sys

import pkg.utils.context as context

__plugins__ = {}
"""
插件列表

示例:
{
    "example": {
        "name": "example",
        "description": "example",
        "version": "0.0.1",
        "author": "RockChinQ",
        "class": <class 'plugins.example.ExamplePlugin'>,
        "hooks": {
            "person_message": [
                <function ExamplePlugin.person_message at 0x0000020E1D1B8D38>
            ]
        },
        "instance": None
    }
}"""


def walk_plugin_path(module, prefix=''):
    """遍历插件路径"""
    for item in pkgutil.iter_modules(module.__path__):
        if item.ispkg:
            walk_plugin_path(__import__(module.__name__ + '.' + item.name, fromlist=['']), prefix + item.name + '.')
        else:
            logging.info('加载模块: {}'.format(prefix + item.name))

            importlib.import_module(module.__name__ + '.' + item.name)


def load_plugins():
    """ 加载插件 """
    logging.info("加载插件")
    PluginHost()
    walk_plugin_path(__import__('plugins'))

    logging.debug(__plugins__)


def initialize_plugins():
    """ 初始化插件 """
    logging.info("初始化插件")
    for plugin in __plugins__.values():
        try:
            plugin['instance'] = plugin["class"]()
        except:
            logging.error("插件{}初始化时发生错误: {}".format(plugin['name'], sys.exc_info()))


def unload_plugins():
    """ 卸载插件 """
    for plugin in __plugins__.values():
        if plugin['instance'] is not None:
            if not hasattr(plugin['instance'], '__del__'):
                logging.warning("插件{}没有定义析构函数".format(plugin['name']))
            else:
                try:
                    plugin['instance'].__del__()
                    logging.info("卸载插件: {}".format(plugin['name']))
                except:
                    logging.error("插件{}卸载时发生错误: {}".format(plugin['name'], sys.exc_info()))


class EventContext:
    """ 事件上下文 """
    eid = 0

    name = ""

    __prevent_default__ = False
    """ 是否阻止默认行为 """

    __prevent_postorder__ = False
    """ 是否阻止后续插件的执行 """

    def prevent_default(self):
        """阻止默认行为"""
        self.__prevent_default__ = True

    def prevent_postorder(self):
        """阻止后续插件执行"""
        self.__prevent_postorder__ = True

    def is_prevented_default(self):
        return self.__prevent_default__

    def is_prevented_postorder(self):
        return self.__prevent_postorder__

    def __init__(self, name: str):
        self.name = name
        self.eid = EventContext.eid
        EventContext.eid += 1


def emit(event_name: str, **kwargs) -> EventContext:
    """ 触发事件 """
    import pkg.utils.context as context
    return context.get_plugin_host().emit(event_name, **kwargs)


class PluginHost:
    """插件宿主"""

    def __init__(self):
        context.set_plugin_host(self)

    def get_runtime_context(self) -> context:
        """获取运行时上下文"""
        return context

    def get_bot(self):
        """获取机器人对象"""
        return context.get_qqbot_manager().bot

    def notify_admin(self, message):
        """通知管理员"""
        context.get_qqbot_manager().notify_admin(message)

    def emit(self, event_name: str, **kwargs) -> EventContext:
        """ 触发事件 """
        event_context = EventContext(event_name)
        for plugin in __plugins__.values():
            for hook in plugin['hooks'].get(event_name, []):
                try:
                    kwargs['host'] = context.get_plugin_host()
                    kwargs['event'] = event_context
                    hook(plugin['instance'], **kwargs)

                    if event_context.is_prevented_default():
                        logging.debug("插件 {} 要求阻止事件{}的默认行为".format(plugin['name'], event_name))

                    if event_context.is_prevented_postorder():
                        logging.debug("插件 {} 阻止了后序插件的执行".format(plugin['name']))
                        break

                except:
                    logging.error("插件{}触发事件{}时发生错误: {}".format(plugin['name'], event_name, sys.exc_info()))

        return event_context
