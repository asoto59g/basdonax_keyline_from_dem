def classFactory(iface):
    from .plugin import BasdonaxKeylinePlugin
    return BasdonaxKeylinePlugin(iface)