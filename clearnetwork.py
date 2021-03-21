#!/usr/bin/env python
import dbus, uuid

bus = dbus.SystemBus()
proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")

connection_paths = settings.ListConnections()

for path in connection_paths:
       con_proxy = bus.get_object("org.freedesktop.NetworkManager", path)
       settings_connection = dbus.Interface(con_proxy, "org.freedesktop.NetworkManager.Settings.Connection")
       config = settings_connection.GetSettings()
       settings_connection.Delete()
