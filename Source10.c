// Hola, comentario

int suma(int x, int *y) {
    printf("ey %d", 3);
    return x + *y;
}

int suma2(int x2, int *y2) {
    printf("ey %d", 3);
    // Los tipos no son compatibles, da error la suma
    return x2 + y2;
}

int* a;
int **b[3][5];
int result = suma(*a, *b[2][3]);
suma(result, &result);