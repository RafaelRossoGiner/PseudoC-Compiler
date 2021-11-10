int a = 0;

//This instruction gives an error since a is not declared as a function
int j = 2*a-3;

printf("ey");

printf("ey, el valor de a es %d y el de j es %d", a, j);
printf("ey, el valor de a es %d y el de j es %d", a);
printf("ey, el valor de a es %d y el de j es %d", a, j, j);

// ERROR <----------------------------------------------
if (a == j) {
    int testOk = 1;
}else{
    int testOk = 0;
}

//Empty declaration
void empty();

//Declaration with parameter types
void test(int, int);

// Gives an error since test is a function and must be called as a function
//int z = test;

// Does not give an error since test is called as a function
int x = test(3, 4);

//Declaration with parameter types and symbols
int der(int f, int c, int y);

//Re-declaration of a function is not allowed
//int der();

//Definition
int fun (int g, int d) {
    int z = a;
    x = c + empty() + fun(d, a); // Ok
    x = c + empty() + fun(d+test(x,z-2), a) - der();
    printf("%d", a);
    scanf("%d");
    //if no return instruction is set, the parser gives a syntax error
    return c - empty() + der();
} // Da error aqui cuando no debería

a = z;

//This does not give an error since it is a definition of a previous declaration
void empty(){
    int useless = 0;
    scanf("%d%d", &useless, &apetecan);
    //void functions can be defined with no return instruction
}

// Esto no se debería poder hacer
a = fun();
int b = empty();