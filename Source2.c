int a;

void empty();

int der(); //This gives an error since redeclaration is not allowed

int fun (int c, int d){
    int z = a;
    int x = c + empty() + fun(d, a); // Ok
    x = c + empty() + fun(d, a) - der; // der is not called as function
    //if no return instruction is set, the parser gives a syntax error
    int der();
    return c - empty() + der();
}

void empty(){
    int useless = 0;
    //void functions can be defined with no return instruction
}

a = fun();
int b = empty();