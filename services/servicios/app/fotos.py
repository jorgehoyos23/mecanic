"""Fotos reales de los servicios de demostración (Wikimedia Commons, licencias libres).

Cada entrada: nombre del servicio -> (url de la imagen, crédito del autor y licencia, página de la fuente).
"""
_T = "https://thumb.wikimedia.org/wikipedia/commons/thumb"
_C = "https://commons.wikimedia.org/wiki/File:"


def _f(path: str, name: str, credit: str) -> tuple[str, str, str]:
    return f"{_T}/{path}/{name}/500px-{name}", credit, f"{_C}{name}"


FOTOS = {
    "Cambio de aceite y filtro": _f("e/e2", "Car_mechanic_checking_oil_levels.jpg", "Shixart1985 · CC BY 2.0"),
    "Mantenimiento preventivo 10.000 km": _f(
        "d/d7", "Mechanic_works_on_car_engine_performing_routine_maintenance_and_inspections_on_vehicle_parts.jpg",
        "Shixart1985 · CC BY 2.0"),
    "Alineación y balanceo": _f("e/e2", "Modern_car_wheel_balancing_machine_tool_at_tire_service.jpg",
                                "Shixart1985 · CC BY 2.0"),
    "Revisión y cambio de frenos": _f(
        "6/61", "Rusty_brake_disc_and_caliper_shown_on_a_vehicle_parked_on_gravel_near_a_road.jpg",
        "Shixart1985 · CC BY 2.0"),
    "Reparación de motor": _f("f/f8", "Senior_man_repairing_car_engine_in_sunny_outdoor_setting.jpg",
                              "Shixart1985 · CC BY 2.0"),
    "Sistema eléctrico y batería": _f("9/91", "Auto_mechanic_checking_old_car_battery_voltage.jpg",
                                      "Shixart1985 · CC BY 2.0"),
    "Diagnóstico general por escáner": _f("5/5d", "Man_holding_Obd2_jack_for_car_software_diagnostic.jpg",
                                          "Nenad Stojkovic · CC BY 2.0"),
}
