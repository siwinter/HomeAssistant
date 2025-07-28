# Testumgebung für wintergarten.py
# 
# - Erzeugt MQTT-Meldungen vom vom Wind und Lichtsensor
# - Simmuliert das Verhalten des ESPs
# - Simmuliert Regenalarm
#
# Benötigt die folgende Konfiguration  
'''
input_boolean:
  t_wgrol_set_rain:                       #from test_wintergarten.py
  t_wgrol_set_storm:                      #from test_wintergarten.py

input_number:
  t_wgrol_position:                     #from test_wintergarten.py
    name: "t_wgrol_position"            # zeigt welchen Positionswert der 
    min: 0                              # ESP liefern würde
    max: 100
    step: 1
    unit_of_measurement: "%"
    mode: slider # Oder "box

  t_wgrol_sun:
    name: "t_wgrol_sun"                 #from test_wintergarten.py
    min: -1                             # Zur Einstellung der Lichtstärke
    max: 50
    step: 1
    mode: slider

  t_wgrol_wind:                         #from test_wintergarten.py
    name: "t_wgrol_wind"                # Zur Einstellung der Windgeschwindigkeit
    min: -1
    max: 50
    step: 1
    mode: slider

binary_sensor:
  - platform: template
    sensors:
      rain_alarm:                          # from rainradar.py
        unique_id: rain_alarmID
        value_template: "{{ 'off' }}"


'''
scenario_1 = """
>>> Start scenario_1
>>> Test1 : Regenalarm
close,  #open Rollo
setSun,40
pause,10
setAuto,on
pause,5
setRain,on
pause,10
setRain,off 
pause,10
>>> Testende scenario_1
"""
class autoTest :

    def __init__(self):
        log.info("wintergarten autoTest")
        self.testRunning = True
        self.pauseCounter = 0
        self.zeilenNr = 0
        self.startTest()

    def startTest(self):
        self.zeilen = scenario_1.splitlines()

    def nextTestStep(self):
        if (self.pauseCounter > 0) :
            self.pauseCounter = self.pauseCounter - 1
            return
        if(self.testRunning == True) :
            if (self.zeilenNr >= len(self.zeilen)) : return
            zeile  = self.zeilen[self.zeilenNr]
            log.info("nextStep:  %s",zeile)
            self.zeilenNr = self.zeilenNr + 1
            komponenten = zeile.split(",")
            if (len(komponenten)<1) : return

            if (komponenten[0] == "pause") :
                self.pauseCounter = int(komponenten[1])
            elif (komponenten[0] == "open") :
                pyscript.wgrol_open()
            elif (komponenten[0] == "close") :
                pyscript.wgrol_close()
            elif (komponenten[0] == "stop") :
                pyscript.wgrol_stop()
            elif (komponenten[0] == "setAuto") :
                input_boolean.wgrol_autoswitch = komponenten[1]
            elif (komponenten[0] == "setWind") :
                input_number.t_wgrol_wind = komponenten[1]
            elif (komponenten[0] == "setStorm") :
                input_boolean.wgrol_autoswitch = komponenten[1]
            elif (komponenten[0] == "setSun") :
                input_number.t_wgrol_sun = komponenten[1] + ".0"
            elif (komponenten[0] == "setRain") :
                input_boolean.t_wgrol_set_rain = komponenten[1]
            else : log.debug("unknown Command")

myAutotester = autoTest()


#===============================================================================

wind = -1
sun  = -1

@time_trigger("period(now, 1sec)")
def wgrolTest_ticker():
    if (wind >= 0) :
        log.debug("wgrolTest_publishWind : %i",wind)
        mqtt.publish(topic = "inf/wgRol/Hzm1", payload = str(wind))
#        log.debug("wgrolTest_publishWind %s", str(wind))

    myAutotester.nextTestStep()


@time_trigger("period(now, 5sec)")
def wgrolTest_publishSun():
    if (sun >= 0) :  
        log.debug("publish sun = %s", sun)
        mqtt.publish(topic = "inf/wgWet/sun", payload = str(sun))
#        log.debug("wgrolTest_publishSun %s", str(wind))


@state_trigger('input_number.t_wgrol_wind')
def wgrolTest_setWind():
    log.debug("wgrolTest_setWind")
    global wind
    strV = state.get("input_number.t_wgrol_wind")
    wind = int(strV[0:len(strV)-2])

@state_trigger('input_number.t_wgrol_sun')
def wgrolTest_setSun():
    log.debug("wgrolTest_setSun")
    global sun
    strV = state.get("input_number.t_wgrol_sun")
    sun = int(strV[0:len(strV)-2])
    if (sun > 0) : sun = sun *100


moving = 0
closing = True
position = 0

@time_trigger("period(now, 2sec)")
def wgrolTest_moveTimer():
    global moving
    global position

    if (moving != 0) :
        log.debug("wgrolTest_moveTimer: %i", position)
        moving = moving - 1
        if (closing == True):
            position = position + 20
            if  (position > 100) : position = 100
        else:
            position = position - 20
            if  (position < 0) : position = 0
        input_number.t_wgrol_position = position
        mqtt.publish(topic = 'inf/wgRol/rollo', payload = str(position))


@mqtt_trigger('cmd/wgRol/rollo')
def wgrolTest_moveRol(topic, payload):
    global moving
    global closing
    log.debug("wgroTest_moveRol")
    if (moving > 0) : moving = 0
    else : moving = 5
    if (payload == 'close') : closing = True
    else : closing = False

@state_trigger('input_boolean.t_wgrol_set_rain')
def wgrolTest_setRain():
    log.debug("wgrolTest_setRain %s", input_boolean.t_wgrol_set_rain)
    if (input_boolean.t_wgrol_set_rain == "on"): state.set("binary_sensor.rain_alarm","on")
    else : state.set("binary_sensor.rain_alarm","off")

@state_trigger('input_boolean.t_wgrol_set_storm')
def wgrolTest_setStorm():
    log.debug("t_wgrol_setStorm %s", input_boolean.t_wgrol_set_storm)
    if (input_boolean.t_wgrol_set_storm == "on"): mqtt.publish(topic = "inf/wgRol/alarm", payload = "ein")
    else : mqtt.publish(topic = "inf/wgRol/alarm", payload = "aus")

