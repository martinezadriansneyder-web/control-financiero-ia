print("Bienvenidos a la calculadora")
print("Para salir escribe 'salir'")
print("las operaciones son suma,resta,multi y divi")

resultado = 0
while True:
    if not resultado:
        n1 = input("Ingrese numero: ")
        if n1.lower() == "salir":
            break
        resultado = int(n1)
    op = input("ingresa operacion ")
    if op.lower() == "salir":
        break
    n2 = input("ingresa siguiente numero:")
    if n2.lower() == "salir":
        break
    n2 = int(n2)

    if op.lower() == "suma":
        resultado += n2
    elif op.lower() == "resta":
        resultado -= n2
    elif op.lower() == "multi":
        resultado *= n2
    elif op.lower() == "divi":
        resultado /= n2
    else:
        print("operacion no valida")
        break
    print(f"el resultado es {resultado}")
