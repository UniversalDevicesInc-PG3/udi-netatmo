
# Netatmo Weather Station NodeServer

This is the Netatmo Weather Station NodeServer for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V3](https://github.com/Einstein42/udi-polyglotv2)
(c) 2021 Daniel Caldentey
MIT license.

This node server is intended to interact with the Netatmo Weather Station. It can track the status of all modules connected to a single Weather Station.[Netatmo](https://www.netatmo.com/en-us/weather) You will need account access to your Netatmo via the Netatmo Developer API, and create an App on their developer site to get a Client ID and a Client Secret 

Currently, only one Weather Station is supported.

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Configure the node server with your account username and password.

### Node Settings
The settings for this node are:

#### Short Poll
   * Query Weather Station status. The default is 10 minutes as the server only updates every 10 minutes.
#### Long Poll
   * Not used

#### Username
   * Your Netatmo account username

#### Password
   * Your Netatmo account password

#### Client ID
   * Your Netatmo App Client ID

#### Client Secret
   * Your Netatmo App Client Secret


## Requirements

A Netatmo weather station

# Release Notes

- 1.0.0 06/21/2021
   - Initial version published to github
- 1.1.0 06/26/2021
   - Added "Query All" Command to NodeServer
