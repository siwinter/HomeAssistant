# Version 1.3
#
# Das Skript steuert im Automodus abhängig von der Beleuchtung die Position des Beschattungsrollos.
# Bei Regen und starkem Wind wird das Rollo grundsätzlich eingefahren
#
# Die folgenden templates müssen im System definiert werden (z.B. in der configuration.yaml 
"""
cover:
  - platform: template
    covers:
      wgrol_cover:                        # from wintergarten.py
        friendly_name: "wgrol_cover"      # benötigt
        unique_id: wgrol_coverID
        device_class: shutter
        open_cover:
          service: pyscript.wgrol_open
        close_cover:
          service: pyscript.wgrol_close
        stop_cover:
          service: pyscript.wgrol_stop
        position_template: "{{ states('sensor.wgrol_position') | float(default=0) }}"
        optimistic: false

input_boolean:
  wgrol_autoswitch:                       # from wintergarten.py
    initial: off                          # zum Ein-/Ausschalten des Automatikmodus

sensor:
  - platform: template
    sensors:
      wgrol_mode:                       # from wintergarten.py
        unique_id: wgrol_modeID         # zeigt Modus (manuell, automatisch, Regen ...)
        value_template: "{{ 'init' }}"

      wgrol_position:                   # from wintergarten.py
        unique_id: wgrol_positionID     # vermutete Position des Rollos
        value_template: "{{ 50 }}"      # 50 ist der Anfangswert, der  vom Skript aktualisiert wird
        unit_of_measurement: "%"

##---------> mail_notifier wird benötigt um bei Systemausfall eingestellte Nutzer zu informieren
notify:
  - name: "mail_notifier"               # from elsewhere
    platform: smtp
    server: "xyz"
    timeout: 15
    sender: "xyz"
    encryption: starttls
    username: "xyz"
    password: "xyz"
    recipient:
      - "xyz"
      - "xyz"
    sender_name: "xyz"


"""
#
# Das Skript erzeugt
#
# - Services
#      wgrol_open
#      wgrol_close
#      wgrol_stop
#
# Das Skript benötigt  / verarbeitet
# - Sensoren 
#      binary_sensor.rain_alarm
#
# - mqtt-Nachrichten
#      cmd/wgRol/rollo {"open"|"close"}
#      cmd/wgRol/led1 {"on"|"off"|"blink"}
#
#      inf/wgRol/Hzm1 {integer-String}
#      inf/wgWet/sun {integer}
#      inf/wgRol/alarm {"ein"|"aus}
#      inf/wgRol/rollo {integer}

import os
import aiohttp

version = "1.3.1"
Testkonfiguration = True

url_wgWet = 'http://192.168.20.155/restart'
url_wgRol = 'http://192.168.20.156/restart'

c_light_time = 300      # 300 * 5sec = 15min muss es zu hell oder zu dunkel sein, ehe das Rollo bewegt wird
c_wind_time  = 900      # 15min
c_diagnostic_time = 120 # 10 min

if (Testkonfiguration == True ) :
    c_light_time = 5        # 25 sec
    c_wind_time  = 25       # 25 sec
    c_diagnostic_time = 24  #  2 min

c_move_time = 2   # 5-10 sec nach einer Bewegung wird das nächste open close erlaubt
c_lux_max = 1000  # wenn 15min ununterbrochen Lichtstärke größer ist, wird Dach geschlosse
c_lux_min = 500   # wenn 15 min ununterbrochen Lichtstärke geringer ist, wird Dach geöffnet
c_windy_min = 10
c_windy_max = 30

cmd_noCommand    = 0
cmd_openCommand  = 1
cmd_closeCommand = 2

auto_state_closed = 0
auto_state_open   = 1

rainAlarm  = 1
windAlarm  = 2
stormAlarm = 3
systemAlarm = 4
alarmTexts = ["keinAlarm", "Regen", "Wind", "Sturm", "Systemausfall"]

class coverControl :
    def __init__(self):
        if (Testkonfiguration == True ) : log.warning("wintergartenSteuerung Version %s läuft mit TESTDATEN", version)
        else: log.info("WintergartenSteuerung Version %s start", version)
        self.moving = 0                     # cover nicht in Bewegung
        self.nextCommand = cmd_noCommand    # Kommando, das während der Bewegung erzeugt wurde
        self.alarm = set()                  # Liste der akuellen Alarme (Regen, Wind, Sturm)
        self.windCounter = 0                # Reaktionszeit der Windsteuerung
        self.delayTimer = c_light_time      # Reaktionszeit der Lichtsteuerung
        self.autoMode = False               # Automatikmodus nicht eingeschaltet
        self.autoState = auto_state_open    # von der Lichsteuerung errechnete Position (open | close)
        self.checkWindMsg  = 1              # überprüft regelmäßigen Erhalt der Windwerte
        self.checkLightMsg = 1              # überprüft regelmäßigen Erhalt der Lichtwerte
        self.diagnosticTimer = c_diagnostic_time #überprüft, ob Sensorwerte regelmäßig geliefert werden

#        notify.mail_notifier(message="", title='Wintergarten Restart')

    def init(self) :
        try:
            fd = os.open("pyscript/wintergarten.data", os.O_RDWR)
            data = os.fdopen(fd, "r")
            initString = data.readline()
            log.info("read initstring: %s", initString)
            data.close()
            if (initString == "autoOn") :
                self.autoMode = True
                state.set("input_boolean.wgrol_autoswitch","on")
            else :
                self.autoMode = False
                state.set("input_boolean.wgrol_autoswitch","off")
        except:
            log.warning("no wintergarten.data")
            self.autoMode = False
            state.set("input_boolean.wgrol_autoswitch","off")
        self.print_mode()
        self.open()

# ------------------------------ moveControl ------------------------------

    def execute(self):
        log.debug("execute moving: %i",self.moving)
        if ((self.moving == 0) and (self.nextCommand != cmd_noCommand)) :
            if (self.nextCommand == cmd_closeCommand) : pyscript.wgrol_close()
            elif (self.nextCommand == cmd_openCommand) : pyscript.wgrol_open()

            else : pass
            self.moving = c_move_time
            self.nextCommand = cmd_noCommand

    def tick(self):                 # wird alle 5 Sekunden aufgerufen 
        if (self.moving > 0) :
            self.moving = self.moving -1                              # Wenn  moving heruntergezählt ist
            if (self.nextCommand != cmd_noCommand) :
                self.execute()   # Können neue Kommandos ausgeführt werden

        self.diagnosticTimer = self.diagnosticTimer -1
        if (self.diagnosticTimer == 0) :
            self.diagnosticTimer = c_diagnostic_time
            self.checkSystem()


    def open(self):
        log.info("open")
        self.nextCommand = cmd_openCommand
        self.execute()

    def close(self) :
        log.info("close")
        self.nextCommand = cmd_closeCommand
        self.execute()

    def set_position(self, p) :
        log.debug("set_position %s", p)
        sensor.wgrol_position = p
        self.moving = c_move_time

# ------------------------------ lightControl ------------------------------

    def print_mode(self):
        outTxt = "manuell"
        ledCmd = "off"
        if (self.autoMode == True) :
            outTxt = "automatisch"
            ledCmd = "on"
        if (rainAlarm in self.alarm)   : outTxt = "Regen"
        if (windAlarm in self.alarm)   : outTxt = "Wind"
        if (stormAlarm in self.alarm)  : outTxt = "Sturm"
        if (systemAlarm in self.alarm) : outTxt = "System Ausfall"
        if (self.alarm) : ledCmd = "blink"

        state.set('sensor.wgrol_mode',outTxt)
        mqtt.publish(topic='cmd/wgRol/led1', payload=ledCmd)

    def set_autoMode(self, m) :
        initString = ""
        if (m == "on") :
            log.info("set_automode True")
            self.autoMode = True
            initString = "autoOn"
            if (self.autoState == auto_state_open) : self.open()
            elif (self.autoState == auto_state_closed) : self.close()
        else :
            log.info("set_automode False")
            self.autoMode = False
            initString = "autoOff"
        try:
            fd = os.open("pyscript/wintergarten.data", os.O_RDWR|os.O_CREAT|os.O_TRUNC)
            data = os.fdopen(fd, "wt")
            data.write(initString)
            data.close()
        except:
           log.error("could not save data")

        self.print_mode()

    def set_autoState(self, state) :
        log.info("set_autoState %s", state)
        self.delayTimer = c_light_time
        if (state == "close"):
            self.autoState = auto_state_closed
        else:
            self.autoState = auto_state_open
        if ((self.autoMode == True) and (not self.alarm)):
            if (self.autoState == auto_state_open) : self.open()
            else: self.close() 

    def processLight(self,lux) :
        log.debug("processLight %i mit timer %i", lux, self.delayTimer - 1)
        self.checkLightMsg = 0
        if (self.autoState == auto_state_open) :  # cover is open
            if lux > c_lux_max :                    # Hellphase
                self.delayTimer = self.delayTimer - 1
                if (self.delayTimer == 0) : self.set_autoState("close")
            else :
                self.delayTimer = c_light_time
        else :                                    # cover is closed
            if lux < c_lux_min :                    # Dunkelphase
                self.delayTimer = self.delayTimer - 1
                if (self.delayTimer == 0) : self.set_autoState("open")
            else :
                self.delayTimer = c_light_time

# ------------------------------ alarmControl ------------------------------

    def set_alarm(self,a):
        log.info("set_alarm %s",alarmTexts[a])
        if (not self.alarm) : self.open()
        self.alarm.add(a)
        self.print_mode()

    def reset_alarm(self,a):
        log.info("reset_alarm %s",alarmTexts[a])
        self.set_autoState("open")    # restart Lichtsteuerung
        self.alarm.discard(a)
        self.print_mode()

    def processWind(self, wind) :
        log.debug("processWind %i mit counter %i", wind, self.windCounter)
        self.checkWindMsg = 0
        if (not (windAlarm in self.alarm)):
            if (wind > c_windy_max) :
                self.windCounter = self.windCounter + 1
            elif (wind < c_windy_min) :
                self.windCounter = 0
            if (self.windCounter == 3) :
                self.windCounter = c_wind_time
                log.info('windalarm on')
                self.set_alarm(windAlarm)
        else :
            if (wind < c_windy_min) :
                self.windCounter = self.windCounter - 1
            else :
                self.windCounter = c_wind_time
            if (self.windCounter <= 0) :
                log.info('reset windalarm')
                self.reset_alarm(windAlarm)

    def checkSystem(self) :
        log.debug("checkSystem: wind %i light %i", self.checkWindMsg, self.checkLightMsg)
        outTxt = ""
        if (self.checkWindMsg == 1) :
            outTxt = outTxt + "\nWindmesser ist ausgefallen"
        if (self.checkWindMsg in [2,3,5,10]) :
            try:
                async with aiohttp.ClientSession() as session:
                async with session.get(url_wgRol) as resp:
                    resp.raise_for_status() # Löst einen Fehler bei schlechten HTTP-Statuscodes aus (z.B. 404, 500)
            except Exception as e:
                outTxt = outTxt + + "\nRestart Windmesser nicht möglich\n" + str(e)
            log.info("wgRol reseted")
        if (self.checkWindMsg == 3) :
            if (windAlarm in self.alarm) :
                self.alarm.discard(windAlarm)
                self.windCounter = 0
                sensor.wgrol_position = "50"
                outTxt = outTxt + "\nWindalarm zurückgesetzt"
        if (self.checkWindMsg == 144) : self.checkWindMsg =  0

        if (self.checkLightMsg == 1) :
            outTxt = outTxt + "\nLichtsensor ist ausgefallen"
        if (self.checkLightMsg == 3) :
            try:
                async with aiohttp.ClientSession() as session:
                async with session.get(url_wgWet) as resp:
                    resp.raise_for_status() # Löst einen Fehler bei schlechten HTTP-Statuscodes aus (z.B. 404, 500)
            except Exception as e:
                outTxt = outTxt + + "\nRestart Lichtsensor nicht möglich\n" + str(e)
        if (self.checkLightMsg == 144) : self.checkLightMsg =  0

        if (outTxt != ""):
            log.warning(outTxt)
            try:
                mailTxt = "Bei der Wintergartensteuerung ist eine Störung aufgetreten" + outTxt
                notify.mail_notifier(message=mailTxt, title='Wintergarten Fehler') 
            except:
                log.warning("error mail not sent")
        if ((self.checkWindMsg != 0) or (self.checkLightMsg != 0)) :
            self.set_alarm(systemAlarm)
        else :
            self.reset_alarm(systemAlarm)

        self.checkWindMsg  = self.checkWindMsg + 1
        self.checkLightMsg = self.checkLightMsg +1

myController = coverControl()
# ------------------------------ Triggers ------------------------------

@mqtt_trigger("inf/wgRol/Hzm1")
def windSensor(topic, payload) :
    log.debug("windSensor: %s", payload)
    try: iValue = int(payload)
    except:
        log.warning('invalid windvalue (Hzm1)')
        iValue = 0
    myController.processWind(iValue)

@mqtt_trigger('inf/wgWet/sun')
def lightSensor(topic, payload) :
    try: iValue = int(payload)
    except:
        log.warning('invalid lux (inf/wet/sun)')
        iValue = 0
    myController.processLight(iValue)

@state_trigger('binary_sensor.rain_alarm')
def set_rainAlarm() :
    log.debug("set_rainAlarm: %s", binary_sensor.rain_alarm)
    if (binary_sensor.rain_alarm == 'on') : myController.set_alarm(rainAlarm)
    else : myController.reset_alarm(rainAlarm)

@state_trigger('input_boolean.wgrol_autoswitch')
def set_autoSwich() :
    log.debug("set_autoSwitch: %s", input_boolean.wgrol_autoswitch)
    myController.set_autoMode(input_boolean.wgrol_autoswitch)

@mqtt_trigger('inf/wgRol/alarm')        # stormAlarm from ESP wgRol
def set_stormAlarm(topic, payload) :
    log.debug("stormAlarm %s", payload)
    if (payload == 'ein') : myController.set_alarm(stormAlarm)
    elif (payload == 'aus') : myController.reset_alarm(stormAlarm)
    else : log.warning('invalid alarm state')

@mqtt_trigger('inf/wgRol/rollo')        # position from ESP wgRol
def set_position(topic, payload) :
    log.debug("position %s", payload)
    try: iValue = int(payload)
    except:
        log.warning('invalid rollo position (inf/wgRol/rollo)')
        iValue = 0
    iValue = (iValue - 100) * (-1)
    myController.set_position(iValue)

@time_trigger("period(now, 5sec)") 
def ticker():
    myController.tick()

@time_trigger("startup")
def init_coverControler():
    myController.init()

# ------------------------------ Services ------------------------------

moveDirection = "init"

@service()
def wgrol_open():
    log.debug("wgrol_open")
    global moveDirection
    moveDirection = 'open'
    mqtt.publish(topic = 'cmd/wgRol/rollo', payload = 'open')

@service()
def wgrol_close():
    log.debug("wgrol_close")
    global moveDirection
    moveDirection = 'close'
    mqtt.publish(topic = 'cmd/wgRol/rollo', payload = 'close')

@service()
def wgrol_stop():
    log.debug("wgrol_stop")
    global moveDirection
    if ((myController.moving > 0) and (moveDirection != 'init')):
        mqtt.publish(topic = 'cmd/wgRol/rollo', payload = moveDirection)
        moveDirection = 'init'

