// Hola, comentario
int copy, copy2, copy3;
//x:8, y:12
//table {x:8, y:12}
int suma(int x , int *y) {
    int local; //local:-4
    printf("ey %d", 3);
    return x + *y;
}
//table = None
int global;

int* a;
int **b[3][5];
int result = suma(*a, *b[2][3]);
suma(result, &result);