n1 = input("ingresar primer numero")
n2 = input("ingresar segundo numero")

n1 = int(n1)
n2 = int(n2)

print(n1 + n2)

suma = n1 + n2
resta = n1 - n2
multi = n1 * n2
div = n1 / n2


mensaje = f"""para los numeros {n1} y {n2},
el resultado de la suma es {suma}
el resultado de la resta es {resta}
el resultado de la multiplicacion es {multi}
el resultado de la divison es {div}
"""
print(mensaje)
