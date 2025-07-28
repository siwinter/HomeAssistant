# Von Sonnenaufgang bis Mitternacht wird dayEnergy ektualisiert, wenn der 
# Sensorwert größer geworden ist.
# Um Mitternacht wird totalEnergie erhöht und dayEnergy wird auf Null gesetzt 
# Von Mitternacht bis Sonnenaufgang bleibt dayEnergy auf Null gesetzt
#
import os

# state.persist('pyscript.pvAnlageTotalEnergy',default_value=0.0)
# state.persist('pyscript.pvAnlageYearEnergy',default_value=0.0)
# state.persist('pyscript.pvAnlageMonthEnergy',default_value=0.0)

state.set('sensor.PV_Einnahmen', 0.0)
state.set('sensor.PV_Ernte', 0.0)

class pv :

    def restore_savedEnergy(self):
        fd = os.open("pyscript/pv_anlage.data", os.O_RDWR|os.O_CREAT)
        data = os.fdopen(fd, "r")
        self.savedEnergy = float(data.readline())
        data.close()
        log.info('restore: savedE is ' + str(self.savedEnergy))

    def save_totalEnergy(self):
        log.info('save_totalEnergy: totalE: ' + str(self.totalEnergy))
        fd = os.open("pyscript/pv_anlage.data", os.O_RDWR|os.O_CREAT)
        data = os.fdopen(fd, "wt")
        data.write(str(self.totalEnergy))
        data.close()
        self.savedEnergy = self.totalEnergy

    def set_sensors(self):
        log.info('set_sensors: savedE ' + str(self.savedEnergy))
        sensor.PV_Ernte = self.totalEnergy
        i1 = int(self.totalEnergy * self.kwh_price) // 10
        sensor.PV_Einnahmen = float(i1) /100

    def __init__(self):
        log.debug('init')
        self.startup()

    def startup(self):
        log.info('startup')
        self.daytime = 0    #0=day, 1=afterMidnight
        self.dayEnergy = 0.0
        self.restore_savedEnergy()
        self.totalIncome = 0.0
        self.kwh_price = 0.33

    def set_daytime(self,d):
        self.daytime = d
        log.info('set_daytime: savedE: ' + str(self.savedEnergy) + ' dayE: ' + str(self.dayEnergy))
        if d == 1 :
            self.totalEnergy = self.savedEnergy + self.dayEnergy
            self.dayEnergy = 0.0
            self.save_totalEnergy()
            state.set('sensor.dtu_ac_tagesenergie', 0)

    def update(self, e):
        if (self.daytime == 0) :
            if e > self.dayEnergy :
                self.dayEnergy = e
        log.info('update: savedE: ' + str(self.savedEnergy) + ' dayE: ' + str(self.dayEnergy))
        self.totalEnergy  = self.savedEnergy + self.dayEnergy
        self.set_sensors()

myPV = pv()

@time_trigger("period(now + 1m, 15min)")    # Update every 15 min
def periodical():
    e = float(state.get('sensor.dtu_ac_tagesenergie'))
    log.info('periodical dtu : ' + str(e))
    myPV.update(e)


@state_trigger('sun.sun')           # Sunrise
def sunchange():
    if (state.get('sun.sun') == 'above_horizon') :
        log.info('sunrise')
        myPV.set_daytime(0)

@time_trigger('cron(1 0 * * * )')    # Midnight + 1 min
def midnight():
    log.info('midnight')
    myPV.set_daytime(1)

@time_trigger                       # once on startup or reload
def run_on_startup_or_reload():
    log.info('startup')
    myPV.startup()

@state_trigger("input_boolean.pvhelp == 'on'")
def preset():
    log.info('preset')
    myPV.preset_saved_energy("129372.0")
    myPV.update(float(state.get('sensor.dtu_ac_tagesenergie')))

