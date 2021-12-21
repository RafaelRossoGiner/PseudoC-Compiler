// Hola, comentario

int a;

noDeclarado = 7; // Da error
/*
Comentario de bloque
*/

int suma(int x , int *y) {
    int local; //local:-4
    printf("ey %d", 3);
    return x + *y;
}

int global;

int* a;

int **b[3][5];
int result = suma(*a, *b[2][3]);
suma(result, &result);