# datei: config/pyscript/rainradar.py
# Version 2.0
# 2023.07 : new design of webesite
#
# Wertet Webseite von www.wetter.com aus, um aktuelle und erwartete Niederschläge zu ermitteln.
# Wenn es icht regnet, werden nur dienächste
# Wenn sich das Design der Seite ändert, muss die Auswertung angepasst werden.
#
# Benutzte Entites
#
# binary_sensor.rain_alarm : speichert die Regensituation
#

"""
binary_sensor:
  - platform: template
    sensors:
      rain_alarm:                          # from rainradar.py
        unique_id: rain_alarmID
        value_template: "{{ 'off' }}"

"""

version = "2.1"
Testkonfiguration = False

import aiohttp
import time
import os  # s.w.

location = '/deutschland/niederkruechten/kapelle/DE3205889.html'
#location = '/deutschland/hattersheim-am-main/hattersheim/DE0004242.html'


if (Testkonfiguration == True ) : log.warning("rainradar Version %s läuft mit TESTDATEN", version)
else: log.info("rainradar Version %s start", version)


@time_trigger("period(now + 17sec, 5min)")    # Update every 5 min
def update_web_sensor():

    url = 'https://www.wetter.com' + location + '#niederschlag'

    txt = ""

    try:
        if (Testkonfiguration == True ) :
            log.debug("get Data from testfile pyscript/web.data")
            fd = os.open("pyscript/web.data", os.O_RDWR)
            data = os.fdopen(fd, "r")
            txt = data.read()
            data.close()
        else :
            log.debug("get Data from %s", url)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status() # Löst einen Fehler bei schlechten HTTP-Statuscodes aus (z.B. 404, 500)
                    txt = resp.text()

        i = txt.find("rainnowcast-timeline")                    # suche Regentabelle
        if ( i != -1 ) :
            if (rainAlarm == "on") : checkEnd = 9                # 45 min von jetzt
            else : checkEnd = 4                                  # 20 min von jetzt

            while True:                                         # Tabelle in Liste überführen
                i = txt.find("title",i )
                if (i == -1) :
                    rainAlarm = "off" 
                    break # Teilstring nicht mehr gefunden
                else :
                    i = i + 7         # Anfang des Regenwertes
                    i_end = txt.find("\"",i )
                    rainValue = txt[i:i_end]
                    log.debug(rainValue)
                    if (rainValue != "kein Niederschlag") : 
                        rainAlarm = "on"
                        break
                checkEnd = checkEnd -1
                log.debug("checkEnd = %i", checkEnd)
                if(checkEnd <= 0) :
                    log.debug("no active rain-value found within checked time")
                    rainAlarm = "off"
                    break
        else:
            rainAlarm = "off"
            log.debug("no rain-table found")

        try :
            r = state.get('binary_sensor.rain_alarm')   #check if binary_sensor exists
            state.set("binary_sensor.rain_alarm", rainAlarm)
            log.info("set rainAlarm  : %s", rainAlarm)

        except :
            log.warning("binary_sensor.rain_alarm doesn't exist")

    except Exception as e:
        log.error(f"Fehler beim Abrufen/Aktualisieren der Webseite {e}")

