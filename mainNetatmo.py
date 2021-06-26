#!/usr/bin/env python3
"""
Polyglot v2 node server Netatmo Weather Station status
This project is based on the "udi-owm-poly" code from Bob Paauwe (https://github.com/bpaauwe/udi-owm-poly/)
and uses the "lnetatmo" library from Philippe Larduinat (https://github.com/philippelt/netatmo-api-python)
Copyright (C) 2021 Daniel Caldentey
"""
CLOUD = False
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
    CLOUD = True
from os import name
from platform import node
from ssl import match_hostname
import sys
import json
import lnetatmo
#import requests

LOGGER = polyinterface.LOGGER

def round_half_up(num, decimals = 0):
    temp_dec = 10 ** decimals
    result = num * temp_dec
    result = result + 0.5
    result = int(result)
    result = result / temp_dec
    return result

def get_temperature(temp_value):
    try:
        temp_value = temp_value / 5
        temp_value = temp_value * 9
        temp_value = temp_value + 32
        temp_value = round_half_up(temp_value,1)
        return temp_value
    except:
        LOGGER.info('Failed to convert temperature')
    return 0

def get_pressure(pressure_value):
    try:
        pressure_value = pressure_value * 0.02953
        pressure_value = round_half_up(pressure_value,2)
        return pressure_value
    except:
        LOGGER.info('Failed to convert temperature')
    return 0


class Controller(polyinterface.Controller):
    id = 'Netatmo'
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Netatmo Weather Station'
        self.address = 'netatmo_ws'
        self.primary = self.address
        self.configured = False
        self.myConfig = {}
        self.username = ''
        self.password = ''
        self.clientId = ''
        self.clientSecret = ''
        self.connected = False
        self.session = None
        self.weatherStation = None
        self.lastData = None

        self.poly.onConfig(self.process_config)

    # Process changes to customParameters
    def process_config(self, config):
        if 'customParams' in config:
            # Check if anything we care about was changed...
            if config['customParams'] != self.myConfig:
                changed = False

                if 'Username' in self.myConfig:
                    if self.myConfig['Username'] != config['customParams']['Username']:
                        changed = True
                elif 'Username' in config['customParams']:
                    if config['customParams']['Username'] != "":
                        changed = True

                if 'Password' in self.myConfig:
                    if self.myConfig['Password'] != config['customParams']['Password']:
                        changed = True
                elif 'Password' in config['customParams']:
                    if config['customParams']['Password'] != "":
                        changed = True

                if 'ClientID' in self.myConfig:
                    if self.myConfig['ClientID'] != config['customParams']['ClientID']:
                        changed = True
                elif 'ClientID' in config['customParams']:
                    if config['customParams']['ClientID'] != "":
                        changed = True

                if 'ClientSecret' in self.myConfig:
                    if self.myConfig['ClientSecret'] != config['customParams']['ClientSecret']:
                        changed = True
                elif 'ClientSecret' in config['customParams']:
                    if config['customParams']['ClientSecret'] != "":
                        changed = True

                self.myConfig = config['customParams']
                if changed:
                    self.username = config['customParams']['Username']
                    self.password = config['customParams']['Password']
                    self.clientId = config['customParams']['ClientID']
                    self.clientSecret = config['customParams']['ClientSecret']
                    self.configured = True
                    self.removeNoticesAll()
                    self.discover()

    def start(self):
        LOGGER.info('Starting node server')
        self.check_params()
        self.session = lnetatmo.ClientAuth(clientId=self.clientId, clientSecret=self.clientSecret, username=self.username, password=self.password)
        #self.session = lnetatmo.ClientAuth()
        self.discover()
        LOGGER.info('Node server started')

    def longPoll(self):
        pass

    def shortPoll(self):
        try:
            self.weatherStation = lnetatmo.WeatherStationData(self.session)
        except:
            LOGGER.info('Authentication from library failed - Restarting NodeServer')
            self.poly.restart()

        self.lastData = self.weatherStation.lastData()
        for node in self.nodes:
            if self.nodes[node].id != 'Netatmo':
                self.nodes[node].weatherStation = self.weatherStation
                self.nodes[node].lastData = self.lastData
                self.nodes[node].get_status(False)

    def query(self):
        LOGGER.info('QUERY Controller')
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        # Discover the list of available modules and create the right node
        # for each.
        LOGGER.info("In Discovery...")
        if not self.configured:
            LOGGER.info('Skipping connection because we aren\'t configured yet.')
            return

        try:
            self.weatherStation = lnetatmo.WeatherStationData(self.session)
            self.lastData = self.weatherStation.lastData()
            LOGGER.info('Weather Station Name = ' + self.weatherStation.default_home)
            i = 0
            nodeAddress = ''
            for moduleName in self.lastData.keys():
                LOGGER.info('Module name = ' + moduleName)
                if 'Noise' in self.lastData[moduleName]:
                    #Master Module
                    nodeAddress = 'netwsmain'
                    weatherStation_node = mainModuleNode(self, self.address, nodeAddress,moduleName)
                    LOGGER.info('Master Module')
                elif 'CO2' in self.lastData[moduleName]:
                    #Indoor Module
                    nodeAddress = 'netwsin' + str(i)
                    weatherStation_node = indoorModuleNode(self, self.address, nodeAddress,moduleName)
                    LOGGER.info('Indoor Module')
                    i = i + 1
                elif 'Temperature' in self.lastData[moduleName]:
                    #Outside Module
                    nodeAddress = 'netwsout'
                    weatherStation_node = outdoorModuleNode(self, self.address, nodeAddress,moduleName)
                    LOGGER.info('Outside Module')
                elif 'WindStrength' in self.lastData[moduleName]:
                    #Wind Module
                    nodeAddress = 'netwswind'
                    weatherStation_node = windModuleNode(self, self.address, nodeAddress,moduleName)
                    LOGGER.info('Wind Module')
                elif 'Rain' in self.lastData[moduleName]:
                    #Rain Module
                    nodeAddress = 'netwsrain'
                    weatherStation_node = rainModuleNode(self, self.address, nodeAddress,moduleName)
                    LOGGER.info('Rain Module')
                else:
                    LOGGER.info('Unidentified Module')

                weatherStation_node.lastData = self.lastData
                weatherStation_node.name = moduleName
                self.addNode(weatherStation_node)
                self.nodes[nodeAddress].get_status(True)

        except:
            LOGGER.error('Authentication failed or no modules found.')
            

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')
        try:
            self.session.logout()
        except:
            LOGGER.debug('session logout failed')

    def update_profile(self, command):
        LOGGER.info('UPDATE PROFILE Controller')
        st = self.poly.installprofile()
        return st

    def check_params(self):
        LOGGER.info('CHECK PARAMS Controller')
        self.configured = True

        if 'Username' in self.polyConfig['customParams']:
            self.username = self.polyConfig['customParams']['Username']

        if 'Password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['Password']

        if 'ClientID' in self.polyConfig['customParams']:
            self.clientId = self.polyConfig['customParams']['ClientID']

        if 'ClientSecret' in self.polyConfig['customParams']:
            self.clientSecret = self.polyConfig['customParams']['ClientSecret']

        self.addCustomParam( {
            'Username': self.username,
            'Password': self.password,
            'ClientID' : self.clientId,
            'ClientSecret' :self.clientSecret
            })

        if self.username == '' or self.password == '' or self.clientId == '' or self.clientSecret == '':
            self.configured = False

        self.removeNoticesAll()

    def remove_notices_all(self, command):
        LOGGER.info('REMOVE NOTICES Controller')
        self.removeNoticesAll()

    def query_all(self, command):
        LOGGER.info('Query All')
        self.shortPoll()

    commands = {
            'DISCOVER': discover,
            'UPDATE_PROFILE': update_profile,
            'REMOVE_NOTICES_ALL': remove_notices_all,
            'QUERY_ALL': query_all
            }

    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},   # node server status
            ]

class mainModuleNode(polyinterface.Node):
    id = 'main_netatmo'
    name = ''
    lastData = None
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},   # status
            {'driver': 'GV0', 'value': 0, 'uom': 17},   # temperature fahrenheit
            {'driver': 'GV1', 'value': 0, 'uom': 54},   # CO2
            {'driver': 'GV2', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'GV3', 'value': 0, 'uom': 12},   # noise
            {'driver': 'GV4', 'value': 0, 'uom': 23},   # pressure
            {'driver': 'GV5', 'value': 0, 'uom': 23},   # absolute pressure
            {'driver': 'GV6', 'value': 0, 'uom': 17},   # min temp
            {'driver': 'GV7', 'value': 0, 'uom': 17},   # max temp
            {'driver': 'GV8', 'value': 0, 'uom': 25},   # temp trend
            {'driver': 'GV9', 'value': 0, 'uom': 25},   # pressure trend
            {'driver': 'GV10', 'value': 0, 'uom': 56},   # when
            {'driver': 'GV11', 'value': 0, 'uom': 56},   # wifi status
            ]

    def temp_trend(self, json):
        try:
            nodeStat = json['temp_trend']
            if nodeStat == 'stable':
                return 0
            elif nodeStat == 'up':
                return 1
            else:
                return 2
        except:
            LOGGER.info('failed to parse mower status type.')
        return 99

    def pressure_trend(self, json):
        try:
            nodeStat = json['pressure_trend']
            if nodeStat == 'stable':
                return 0
            elif nodeStat == 'up':
                return 1
            else:
                return 2
        except:
            LOGGER.info('failed to parse mower status type.')
        return 99

    def get_status(self, first):
        LOGGER.info('GET STATUS Main Module')
        try:
            LOGGER.info('Get Staus - MainModule 1')
            json = self.lastData[self.name]
            LOGGER.debug(json)

            n_tempTrend = self.temp_trend(json)
            n_pressureTrend = self.pressure_trend(json)
            n_temperature = json['Temperature']
            n_temperature = get_temperature(n_temperature)
            n_minTemp = json['min_temp']
            n_minTemp = get_temperature(n_minTemp)
            n_maxTemp = json['max_temp']
            n_maxTemp = get_temperature(n_maxTemp)
            n_pressure = json['Pressure']
            n_pressure = get_pressure(n_pressure)
            n_absolutePressure = json['AbsolutePressure']
            n_absolutePressure = get_pressure(n_absolutePressure)
            try:
                n_status = 1
                n_CO2 = json['CO2']
                n_humidity = json['Humidity']
                n_noise = json['Noise']
                n_when = json['When']
                n_when = n_when / 10
                n_wifiStatus = json['wifi_status']
                LOGGER.info('GET STATUS - TRY All')

                try:
                    LOGGER.info('Writting Drivers - START')
                    self.setDriver('ST', n_status, report=True, force=first)
                    LOGGER.info('Temperature :')
                    LOGGER.info(n_temperature)
                    self.setDriver('GV0', n_temperature, report=True, force=first)
                    self.setDriver('GV1', n_CO2, report=True, force=first)
                    self.setDriver('GV2', n_humidity, report=True, force=first)
                    self.setDriver('GV3', n_noise, report=True, force=first)
                    self.setDriver('GV4', n_pressure, report=True, force=first)
                    self.setDriver('GV5', n_absolutePressure, report=True, force=first)
                    self.setDriver('GV6', n_minTemp, report=True, force=first)
                    self.setDriver('GV7', n_maxTemp, report=True, force=first)
                    self.setDriver('GV8', n_tempTrend, report=True, force=first)
                    self.setDriver('GV9', n_pressureTrend, report=True, force=first)
                    self.setDriver('GV10', n_when, report=True, force=first)
                    self.setDriver('GV11', n_wifiStatus, report=True, force=first)
                    LOGGER.info('Writting Drivers - END')
                except:
                    LOGGER.error('Failed to update node status')
            except:
                LOGGER.error('Failed to parse mower status JSON')

        except Exception as ex:
            LOGGER.info('In exception handler, no data for this node')
            LOGGER.debug('Skipping status: ' + str(ex.args[0]))
            return False
        return True

class indoorModuleNode(polyinterface.Node):
    id = 'in_netatmo'
    name = ''
    lastData = None
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},   # status
            {'driver': 'GV0', 'value': 0, 'uom': 17},   # temperature fahrenheit
            {'driver': 'GV1', 'value': 0, 'uom': 54},   # CO2
            {'driver': 'GV2', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'GV3', 'value': 0, 'uom': 17},   # min temp
            {'driver': 'GV4', 'value': 0, 'uom': 17},   # max temp
            {'driver': 'GV5', 'value': 0, 'uom': 25},   # temp trend
            {'driver': 'GV6', 'value': 0, 'uom': 56},   # when
            {'driver': 'GV7', 'value': 0, 'uom': 51},   # battery percent
            {'driver': 'GV8', 'value': 0, 'uom': 56},   # rf status
            ]

    def temp_trend(self, json):
        try:
            name = json['temp_trend']
            if name == 'stable':
                return 0
            elif name == 'up':
                return 1
            else:
                return 2
        except:
            LOGGER.info('failed to parse mower status type.')
        return 99

    def get_status(self, first):
        LOGGER.info('GET STATUS Indoor Module')
        try:
            json = self.lastData[self.name]
            LOGGER.debug(json)

            n_tempTrend = self.temp_trend(json)
            n_temperature = json['Temperature']
            n_temperature = get_temperature(n_temperature)
            n_minTemp = json['min_temp']
            n_minTemp = get_temperature(n_minTemp)
            n_maxTemp = json['max_temp']
            n_maxTemp = get_temperature(n_maxTemp)

            try:
                n_status = 1
                n_CO2 = json['CO2']
                n_humidity = json['Humidity']
                n_when = json['When']
                n_when = n_when / 10
                n_batteryPercent = json['battery_percent']
                n_rfStatus = json['rf_status']

                try:
                    self.setDriver('ST', n_status, report=True, force=first)
                    self.setDriver('GV0', n_temperature, report=True, force=first)
                    self.setDriver('GV1', n_CO2, report=True, force=first)
                    self.setDriver('GV2', n_humidity, report=True, force=first)
                    self.setDriver('GV3', n_minTemp, report=True, force=first)
                    self.setDriver('GV4', n_maxTemp, report=True, force=first)
                    self.setDriver('GV5', n_tempTrend, report=True, force=first)
                    self.setDriver('GV6', n_when, report=True, force=first)
                    self.setDriver('GV7', n_batteryPercent, report=True, force=first)
                    self.setDriver('GV8', n_rfStatus, report=True, force=first)
                except:
                    LOGGER.error('Failed to update node status')
            except:
                LOGGER.error('Failed to parse mower status JSON')

        except Exception as ex:
            LOGGER.info('In exception handler, node data not found')
            LOGGER.debug('Skipping status: ' + str(ex.args[0]))
            return False
        return True

class outdoorModuleNode(polyinterface.Node):
    id = 'out_netatmo'
    name = ''
    lastData = None
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},   # status
            {'driver': 'GV0', 'value': 0, 'uom': 17},   # temperature fahrenheit
            {'driver': 'GV1', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'GV2', 'value': 0, 'uom': 17},   # min temp
            {'driver': 'GV3', 'value': 0, 'uom': 17},   # max temp
            {'driver': 'GV4', 'value': 0, 'uom': 25},   # temp trend
            {'driver': 'GV5', 'value': 0, 'uom': 56},   # when
            {'driver': 'GV6', 'value': 0, 'uom': 51},   # battery percent
            {'driver': 'GV7', 'value': 0, 'uom': 56},   # rf status
            ]

    def temp_trend(self, json):
        try:
            name = json['temp_trend']
            if name == 'stable':
                return 0
            elif name == 'up':
                return 1
            else:
                return 2
        except:
            LOGGER.info('failed to parse mower status type.')
        return 99

    def get_status(self, first):
        LOGGER.info('GET STATUS Outdoor Module')
        try:
            json = self.lastData[self.name]
            LOGGER.debug(json)

            n_tempTrend = self.temp_trend(json)
            n_temperature = json['Temperature']
            n_temperature = get_temperature(n_temperature)
            n_minTemp = json['min_temp']
            n_minTemp = get_temperature(n_minTemp)
            n_maxTemp = json['max_temp']
            n_maxTemp = get_temperature(n_maxTemp)

            try:
                n_status = 1
                n_humidity = json['Humidity']
                n_when = json['When']
                n_when = n_when / 10
                n_batteryPercent = json['battery_percent']
                n_rfStatus = json['rf_status']

                try:
                    self.setDriver('ST', n_status, report=True, force=first)
                    self.setDriver('GV0', n_temperature, report=True, force=first)
                    self.setDriver('GV1', n_humidity, report=True, force=first)
                    self.setDriver('GV2', n_minTemp, report=True, force=first)
                    self.setDriver('GV3', n_maxTemp, report=True, force=first)
                    self.setDriver('GV4', n_tempTrend, report=True, force=first)
                    self.setDriver('GV5', n_when, report=True, force=first)
                    self.setDriver('GV6', n_batteryPercent, report=True, force=first)
                    self.setDriver('GV7', n_rfStatus, report=True, force=first)
                except:
                    LOGGER.error('Failed to update node status')
            except:
                LOGGER.error('Failed to parse mower status JSON')

        except Exception as ex:
            LOGGER.info('In exception handler, node data not found')
            LOGGER.debug('Skipping status: ' + str(ex.args[0]))
            return False
        return True

class windModuleNode(polyinterface.Node):
    id = 'wind_netatmo'
    name = ''
    lastData = None
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},   # status
            {'driver': 'GV0', 'value': 0, 'uom': 48},   # wind strength
            {'driver': 'GV1', 'value': 0, 'uom': 76},   # wind angle
            {'driver': 'GV2', 'value': 0, 'uom': 48},   # gust strength
            {'driver': 'GV3', 'value': 0, 'uom': 76},   # gust angle
            {'driver': 'GV4', 'value': 0, 'uom': 48},   # max wind strength
            {'driver': 'GV5', 'value': 0, 'uom': 76},   # max wind angle
            {'driver': 'GV6', 'value': 0, 'uom': 56},   # when
            {'driver': 'GV7', 'value': 0, 'uom': 51},   # battery percent
            {'driver': 'GV8', 'value': 0, 'uom': 56},   # rf status
            ]

    def get_status(self, first):
        LOGGER.info('GET STATUS Wind Module')
        try:
            json = self.lastData[self.name]
            LOGGER.debug(json)

            try:
                n_status = 1
                n_windStrength = json['WindStrength']
                n_windAngle = json['WindAngle']
                n_gustStrength = json['GustStrength']
                n_gustAngle = json['GustAngle']
                n_maxWindStrength = json['max_wind_str']
                n_maxWindAngle = json['max_wind_angle']
                n_when = json['When']
                n_when = n_when / 10
                n_batteryPercent = json['battery_percent']
                n_rfStatus = json['rf_status']

                try:
                    self.setDriver('ST', n_status, report=True, force=first)
                    self.setDriver('GV0', n_windStrength, report=True, force=first)
                    self.setDriver('GV1', n_windAngle, report=True, force=first)
                    self.setDriver('GV2', n_gustStrength, report=True, force=first)
                    self.setDriver('GV3', n_gustAngle, report=True, force=first)
                    self.setDriver('GV4', n_maxWindStrength, report=True, force=first)
                    self.setDriver('GV5', n_maxWindAngle, report=True, force=first)
                    self.setDriver('GV6', n_when, report=True, force=first)
                    self.setDriver('GV7', n_batteryPercent, report=True, force=first)
                    self.setDriver('GV8', n_rfStatus, report=True, force=first)
                except:
                    LOGGER.error('Failed to update node status')
            except:
                LOGGER.error('Failed to parse mower status JSON')

        except Exception as ex:
            LOGGER.info('In exception handler, node data not found')
            LOGGER.debug('Skipping status: ' + str(ex.args[0]))
            return False
        return True

class rainModuleNode(polyinterface.Node):
    id = 'rain_netatmo'
    name = ''
    lastData = None
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 2},   # status
            {'driver': 'GV0', 'value': 0, 'uom': 23},   # rain
            {'driver': 'GV1', 'value': 0, 'uom': 23},   # sum rain 1h
            {'driver': 'GV2', 'value': 0, 'uom': 23},   # sum rain 24h
            {'driver': 'GV3', 'value': 0, 'uom': 56},   # when
            {'driver': 'GV4', 'value': 0, 'uom': 51},   # battery percent
            {'driver': 'GV5', 'value': 0, 'uom': 56},   # rf status
            ]

    def get_status(self, first):
        LOGGER.info('GET STATUS Rain Module')
        try:
            json = self.lastData[self.name]
            LOGGER.debug(json)

            try:
                n_status = 1
                n_rain = json['Rain']
                n_rain1h = json['sum_rain_1']
                n_rain24h = json['sum_rain_24']
                n_when = json['When']
                n_when = n_when / 10
                n_batteryPercent = json['battery_percent']
                n_rfStatus = json['rf_status']

                try:
                    self.setDriver('ST', n_status, report=True, force=first)
                    self.setDriver('GV0', n_rain, report=True, force=first)
                    self.setDriver('GV1', n_rain1h, report=True, force=first)
                    self.setDriver('GV2', n_rain24h, report=True, force=first)
                    self.setDriver('GV3', n_when, report=True, force=first)
                    self.setDriver('GV4', n_batteryPercent, report=True, force=first)
                    self.setDriver('GV5', n_rfStatus, report=True, force=first)
                except:
                    LOGGER.error('Failed to update node status')
            except:
                LOGGER.error('Failed to parse mower status JSON')

        except Exception as ex:
            LOGGER.info('In exception handler, node data not found')
            LOGGER.debug('Skipping status: ' + str(ex.args[0]))
            return False
        return True


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Netatmo')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

