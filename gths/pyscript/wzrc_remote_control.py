#############################################################
#
# Services zur Ausführung von RC-Kommandos
# - wzrc_rc_switch : 433 MHz Sender (Steckdosen)
# - wzrc_nec_infrared : IR-Fernbedienung (LED-Stripe, LG TV)
#
#############################################################

#-------------- schaltet Beleuchtung im Wohnzimmer ----
@service
def wzrc_rc_switch(protocol=None, code=None):
    if (protocol == "1") :
        if (code == "1377617") :    #  A on
            switch.turn_on(entity_id = "switch.wzlight_a_2")
            log.debug("A on")
        elif (code == "1377620") :  #  A off
            switch.turn_off(entity_id = "switch.wzlight_a_2")
            log.debug("A off")
        elif (code == "1380689") :  #  B on
            log.debug("B on")
            switch.turn_on(entity_id = "switch.wzlight_c_3")
        elif (code == "1380692") :  #  B off 
            log.debug("B off")
            switch.turn_off(entity_id = "switch.wzlight_c_3")
        elif (code == "1381457") :  #  C on
            log.debug("C on")
            switch.turn_on(entity_id = "switch.wzlight_c_3")
        elif (code == "1381460") :  #  C off
            log.debug("C off")
            switch.wzlight_c_3 = "off"
            switch.turn_off(entity_id = "switch.wzlight_c_3")
        elif (code == "1381649") :  #  D on
            log.debug("D on")
        elif (code == "1381652") :  #  D off
            log.debug("D off")
        else :
#            log.warning("rc parameter %s %s",protocol, code)
            pass

@service
def wzrc_nec_infrared(address=None, command=None):
    if (address == "65280") :      # LED-Steuerung
        if (command == "61965") :    # Heller
            pass
        elif (command == "60945") :  # Dunkler 
            pass
        elif (command == "62985") :  # off 
            pass
        elif (command == "64005") :  # on 
            pass
        elif (command == "62220") :  # R 
            pass
        elif (command == "61200") :  # G 
            pass
        elif (command == "63240") :  #  B
            pass
        elif (command == "64260") :  #  W
            pass
        elif (command == "45645") :  #  R1
            pass
        elif (command == "44625") :  #  G1 
            pass
        elif (command == "46665") :  #  B1
            pass
        elif (command == "47685") :  #  Flash
            pass
        elif (command == "45900") :  #  R2
            pass
        elif (command == "44880") :  #  G2
            pass
        elif (command == "46920") :  #  B2
            pass
        elif (command == "47940") :  #  Strobe
            pass
        elif (command == "61455") :  #  R3 
            pass
        elif (command == "60435") :  #  G3
            pass
        elif (command == "62475") :  #  B3
            pass
        elif (command == "63495") :  #  Fade
            pass
        elif (command == "61710") :  #  R4
            pass
        elif (command == "60690") :  #  G4
            pass
        elif (command == "62730") :  #  B4
            pass
        elif (command == "63750") :  #  Smooth
            pass
        else : log.warning("unknown IP-Code: %s", command) 

    elif (address == "64260") :       # TV
        if (command =="63240") :     # on/off
            pass
        elif(command =="60945") :     # 1
            pass
        elif (command == "60690") :  #  2
            pass
        elif (command == "60435") :  #  3
            pass
        elif (command == "60180") :  #  4
            pass
        elif (command == "59925") :  #  5 
            pass
        elif (command == "59670") :  #  6
            pass
        elif (command == "59415") :  #  7
            pass
        elif (command == "59160") :  #  8
            pass
        elif (command == "58905") :  #  9
            pass
        elif (command == "61200") :  #  0
            pass
        else : log.warning("unknown TV-Code: %s", command) 

    else : log.warning("wzlight_1 %s %s",address, command)

