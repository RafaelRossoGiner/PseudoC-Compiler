// Hola, comentario

int b = 3;
int* a, c = b;

//*a[2] = *b[3][1];

int suma(int x, int* y) {
    return x + *y;
}

c = suma(*a, 0);