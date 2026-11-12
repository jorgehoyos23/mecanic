"""Fotos reales de los repuestos de demostración (Wikimedia Commons, licencias libres).

Cada entrada: SKU -> (url de la imagen, crédito del autor y licencia, página de la fuente).
"""
_T = "https://thumb.wikimedia.org/wikipedia/commons/thumb"
_C = "https://commons.wikimedia.org/wiki/File:"

FOTOS = {
    "ACE-5W30-1L": (f"{_T}/3/3a/Motor_oil_bottles_variousbrands.jpg/500px-Motor_oil_bottles_variousbrands.jpg",
                    "Frankieleon · CC BY 2.0", f"{_C}Motor_oil_bottles_variousbrands.jpg"),
    "FIL-ACE-001": (f"{_T}/5/52/Bosch_Oil_Filter.JPG/500px-Bosch_Oil_Filter.JPG",
                    "Schumi4ever · CC BY-SA 4.0", f"{_C}Bosch_Oil_Filter.JPG"),
    "FIL-AIR-001": (f"{_T}/1/13/Cool-Air-intake.jpg/500px-Cool-Air-intake.jpg",
                    "Gearheadgirl · CC BY 3.0", f"{_C}Cool-Air-intake.jpg"),
    "PAS-DEL-001": (f"{_T}/9/92/Brake_pad.jpg/500px-Brake_pad.jpg",
                    "A7N8X · CC BY-SA 3.0", f"{_C}Brake_pad.jpg"),
    "DIS-DEL-001": (f"{_T}/c/c4/Ventilated_2-Piece_Floating_Disc_Curved_Drilled_%26_Slotted_Brake_Rotor.jpg/"
                    "500px-Ventilated_2-Piece_Floating_Disc_Curved_Drilled_%26_Slotted_Brake_Rotor.jpg",
                    "Atharv Chandel · CC BY 4.0",
                    f"{_C}Ventilated_2-Piece_Floating_Disc_Curved_Drilled_%26_Slotted_Brake_Rotor.jpg"),
    "LIQ-FRE-DOT4": (f"{_T}/6/6f/L%C3%ADquido_para_frenos_Bardahl_DOT_3%2C_1000cc.jpg/"
                     "500px-L%C3%ADquido_para_frenos_Bardahl_DOT_3%2C_1000cc.jpg",
                     "Just a Man · CC BY 4.0", f"{_C}L%C3%ADquido_para_frenos_Bardahl_DOT_3%2C_1000cc.jpg"),
    "BAT-12V-60A": (f"{_T}/e/ee/Photo-CarBattery.jpg/500px-Photo-CarBattery.jpg",
                    "Shaddack · Dominio público", f"{_C}Photo-CarBattery.jpg"),
    "BUJ-IRI-001": (f"{_T}/b/b9/Spark_plug.jpg/500px-Spark_plug.jpg",
                    "Dominio público", f"{_C}Spark_plug.jpg"),
    "COR-DIS-001": (f"{_T}/e/e1/Timing_belt_RB30E.jpg/500px-Timing_belt_RB30E.jpg",
                    "RB30DE · Dominio público", f"{_C}Timing_belt_RB30E.jpg"),
    "AMO-DEL-001": (f"{_T}/6/6d/Close-up_of_a_car_mechanic_holding_a_shock_absorber.jpg/"
                    "500px-Close-up_of_a_car_mechanic_holding_a_shock_absorber.jpg",
                    "Shixart1985 · CC BY 2.0", f"{_C}Close-up_of_a_car_mechanic_holding_a_shock_absorber.jpg"),
}

# Fotos de demostración usadas antes; si un repuesto aún tiene una de estas, se actualiza a la nueva.
ANTERIORES = {f"{_T}/2/23/Motor_oil.JPG/500px-Motor_oil.JPG"}
