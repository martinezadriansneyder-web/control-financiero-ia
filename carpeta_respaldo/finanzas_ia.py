import csv
import os
from datetime import datetime

ARCHIVO = "gastos.csv"


# Crear archivo si no existe
def crear_archivo():
    if not os.path.exists(ARCHIVO):
        with open(ARCHIVO, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Fecha", "Monto", "Categoria", "Descripcion"])


# Agregar gasto
def agregar_gasto():
    monto = input("Monto: ")
    categoria = input("Categoria: ")
    descripcion = input("Descripcion: ")

    fecha = datetime.now().strftime("%Y-%m-%d")

    with open(ARCHIVO, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([fecha, monto, categoria, descripcion])

    print("✅ Gasto guardado\n")


# Ver total gastos
def ver_total():
    total = 0

    with open(ARCHIVO, mode="r") as file:
        reader = csv.DictReader(file)
        for fila in reader:
            total += float(fila["Monto"])

    print(f"💰 Total gastado: ${total}\n")


# Ver total por categoria
def ver_por_categoria():
    resumen = {}

    with open(ARCHIVO, mode="r") as file:
        reader = csv.DictReader(file)
        for fila in reader:
            categoria = fila["Categoria"]
            monto = float(fila["Monto"])

            if categoria in resumen:
                resumen[categoria] += monto
            else:
                resumen[categoria] = monto

    print("\n📊 Gastos por categoria:")
    for categoria, total in resumen.items():
        print(f"{categoria}: ${total}")
    print()


# Ver total del mes actual
def ver_mes_actual():
    mes_actual = datetime.now().strftime("%Y-%m")
    total = 0

    with open(ARCHIVO, mode="r") as file:
        reader = csv.DictReader(file)
        for fila in reader:
            if fila["Fecha"].startswith(mes_actual):
                total += float(fila["Monto"])

    print(f"\n📅 Total gastado este mes: ${total}\n")


# NUEVO — Exportar reporte mensual
def exportar_reporte_mes():
    mes_actual = datetime.now().strftime("%Y-%m")
    nombre_reporte = f"reporte_{mes_actual}.csv"

    with open(ARCHIVO, mode="r") as file:
        reader = csv.DictReader(file)
        filas_mes = [
            fila for fila in reader if fila["Fecha"].startswith(mes_actual)]

    if not filas_mes:
        print("⚠️ No hay gastos este mes\n")
        return

    with open(nombre_reporte, mode="w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["Fecha", "Monto", "Categoria", "Descripcion"])
        writer.writeheader()
        writer.writerows(filas_mes)

    print(f"📁 Reporte creado: {nombre_reporte}\n")


# Menú principal
def menu():
    crear_archivo()

    while True:
        print("==== CONTROL FINANCIERO ====")
        print("1 Agregar gasto")
        print("2 Ver total gastos")
        print("3 Ver total por categoria")
        print("4 Ver total del mes actual")
        print("5 Exportar reporte mensual")
        print("6 Salir")

        opcion = input("Elige una opcion: ")

        if opcion == "1":
            agregar_gasto()
        elif opcion == "2":
            ver_total()
        elif opcion == "3":
            ver_por_categoria()
        elif opcion == "4":
            ver_mes_actual()
        elif opcion == "5":
            exportar_reporte_mes()
        elif opcion == "6":
            print("Adios 👋")
            break
        else:
            print("Opcion invalida\n")


menu()
