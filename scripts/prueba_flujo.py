"""Prueba de extremo a extremo del flujo completo a través del API Gateway.

Uso (con la plataforma levantada):  python scripts/prueba_flujo.py [http://localhost:8080]
Solo usa la librería estándar de Python.
"""
import json
import random
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")


def api(method, svc, path, body=None, token=None, expect=None):
    req = urllib.request.Request(f"{BASE}/api/{svc}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, data = r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        status, data = e.code, json.loads(e.read() or b"null")
    if expect and status != expect:
        raise AssertionError(f"{method} {svc}{path}: se esperaba {expect} y llegó {status} -> {data}")
    if not expect and status >= 400:
        raise AssertionError(f"{method} {svc}{path} -> {status}: {data}")
    return data


def step(msg):
    print(f"  ✔ {msg}")


def main():
    print(f"Probando flujo completo contra {BASE}\n")
    n = random.randint(1000, 9999)

    # 1. Cliente se registra y registra su vehículo
    reg = api("POST", "auth", "/register", {"full_name": f"Cliente Prueba {n}", "email": f"cliente{n}@correo.com",
                                            "password": "secreto1", "phone": "3000000000"})
    tc = reg["access_token"]
    step(f"Cliente registrado: {reg['user']['email']}")
    veh = api("POST", "clientes", "/vehicles", {"plate": f"TST{n}", "brand": "Mazda", "model": "3", "year": 2019,
                                                "color": "Rojo", "mileage": 45000}, tc)
    step(f"Vehículo registrado: {veh['plate']}")
    api("POST", "clientes", "/vehicles", {"plate": f"TST{n}", "brand": "Kia", "model": "Rio", "year": 2019}, tc, expect=409)
    step("Placa duplicada rechazada (409)")

    # 2. Solicita un servicio de reparación
    catalog = api("GET", "servicios", "/catalog")
    frenos = next(s for s in catalog if "frenos" in s["name"].lower())
    order = api("POST", "ordenes", "/orders", {"vehicle_id": veh["id"], "service_id": frenos["id"], "kind": "REPARACION",
                                               "description": "Chirrido al frenar y pedal esponjoso", "mileage": 45200}, tc)
    oid = order["id"]
    step(f"Orden creada {order['code']} en estado {order['status']}")

    # 3. Administrador asigna un mecánico
    ta = api("POST", "auth", "/login", {"email": "admin@taller.com", "password": "admin123"})["access_token"]
    mechs = api("GET", "mecanicos", "/mechanics?active=true", token=ta)
    carlos = next(m for m in mechs if m["email"] == "mecanico@taller.com")
    order = api("POST", "ordenes", f"/orders/{oid}/assign", {"mechanic_id": carlos["id"]}, ta)
    assert order["status"] == "EN_DIAGNOSTICO"
    step(f"Mecánico asignado: {order['mechanic_name']} → {order['status']}")

    # 4. Mecánico diagnostica y cotiza (mano de obra + repuestos del inventario)
    tm = api("POST", "auth", "/login", {"email": "mecanico@taller.com", "password": "mecanico123"})["access_token"]
    assert any(o["id"] == oid for o in api("GET", "ordenes", "/orders", token=tm))
    parts = api("GET", "inventario", "/parts?q=PAS-DEL", token=tm)
    pastillas = parts[0]
    detail = api("POST", "ordenes", f"/orders/{oid}/diagnosis", {
        "diagnosis": "Pastillas delanteras desgastadas al 90%. Se recomienda cambio y purga del sistema.",
        "items": [{"kind": "MANO_OBRA", "description": "Cambio de pastillas y purga", "quantity": 1, "unit_price": 80000},
                  {"kind": "REPUESTO", "part_id": pastillas["id"], "quantity": 1}]}, tm)
    assert detail["status"] == "COTIZADA" and detail["quote"]["total"] == 80000 + pastillas["unit_price"]
    step(f"Diagnóstico registrado; cotización por ${detail['quote']['total']:,.0f}")

    # 5. Cliente consulta diagnóstico y aprueba → se descuenta inventario
    detail = api("GET", "ordenes", f"/orders/{oid}", token=tc)
    assert detail["diagnosis"] and detail["quote"]["status"] == "PENDIENTE"
    detail = api("POST", "ordenes", f"/orders/{oid}/quote-decision", {"approved": True}, tc)
    assert detail["status"] == "APROBADA"
    stock_after = api("GET", "inventario", f"/parts/{pastillas['id']}", token=ta)["stock"]
    assert stock_after == pastillas["stock"] - 1, (stock_after, pastillas["stock"])
    step(f"Cotización aprobada; stock de pastillas {pastillas['stock']} → {stock_after}")

    # 6. Reparación: avance, finalizar (genera factura)
    api("POST", "ordenes", f"/orders/{oid}/status", {"status": "EN_REPARACION"}, tm)
    api("POST", "ordenes", f"/orders/{oid}/notes", {"note": "Pastillas instaladas, purgando el sistema."}, tm)
    api("POST", "ordenes", f"/orders/{oid}/status", {"status": "ENTREGADA"}, ta, expect=409)
    detail = api("POST", "ordenes", f"/orders/{oid}/status", {"status": "FINALIZADA", "note": "Listo."}, tm)
    inv = detail["invoice"]
    assert detail["status"] == "FINALIZADA" and inv["status"] == "PENDIENTE"
    step(f"Orden finalizada; factura {inv['number']} por ${inv['total']:,.0f} (IVA incluido)")

    # 7. Entrega bloqueada hasta el pago; el cliente paga
    api("POST", "ordenes", f"/orders/{oid}/status", {"status": "ENTREGADA"}, ta, expect=409)
    step("Entrega sin pago rechazada (409)")
    paid = api("POST", "facturacion", f"/invoices/{inv['id']}/pay", {"method": "TARJETA"}, tc)
    assert paid["status"] == "PAGADA"
    step(f"Factura pagada (ref. {paid['payments'][0]['reference']})")
    detail = api("POST", "ordenes", f"/orders/{oid}/status", {"status": "ENTREGADA"}, ta)
    assert detail["status"] == "ENTREGADA"
    step(f"Vehículo entregado. Bitácora con {len(detail['events'])} eventos")

    # 8. Notificaciones y controles de acceso
    notes = api("GET", "notificaciones", "/notifications/me", token=tc)
    step(f"El cliente recibió {len(notes)} notificaciones:")
    for x in reversed(notes):
        print(f"       · {x['title']}")
    other = api("POST", "auth", "/register", {"full_name": "Otro Cliente", "email": f"otro{n}@correo.com",
                                              "password": "secreto1"})["access_token"]
    api("GET", "ordenes", f"/orders/{oid}", token=other, expect=403)
    api("GET", "ordenes", "/orders", expect=401)
    step("Otro cliente no puede ver la orden (403) y sin token se rechaza (401)")

    # 9. Cancelación con devolución de stock
    o2 = api("POST", "ordenes", "/orders", {"vehicle_id": veh["id"], "kind": "MANTENIMIENTO",
                                            "description": "Cambio de aceite"}, tc)["id"]
    api("POST", "ordenes", f"/orders/{o2}/assign", {"mechanic_id": carlos["id"]}, ta)
    aceite = api("GET", "inventario", "/parts?q=ACE-5W30", token=ta)[0]
    api("POST", "ordenes", f"/orders/{o2}/diagnosis", {"diagnosis": "Aceite degradado", "items": [
        {"kind": "REPUESTO", "part_id": aceite["id"], "quantity": 4}]}, tm)
    api("POST", "ordenes", f"/orders/{o2}/quote-decision", {"approved": True}, tc)
    assert api("GET", "inventario", f"/parts/{aceite['id']}", token=ta)["stock"] == aceite["stock"] - 4
    api("POST", "ordenes", f"/orders/{o2}/status", {"status": "CANCELADA", "note": "Cliente desiste"}, tc, expect=409)
    api("POST", "ordenes", f"/orders/{o2}/status", {"status": "CANCELADA", "note": "Cliente desiste"}, ta)
    assert api("GET", "inventario", f"/parts/{aceite['id']}", token=ta)["stock"] == aceite["stock"]
    step("Orden aprobada cancelada por admin: los 4 L de aceite volvieron al inventario")

    print("\nTodas las pruebas pasaron ✅")


if __name__ == "__main__":
    main()
