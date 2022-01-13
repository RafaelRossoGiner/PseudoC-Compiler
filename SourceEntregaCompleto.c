
//Errors
int main(){
    return 0;
}

//Declarations and Assignments
int a, b[2][3][4];
int **c[3];
int main(){
    int a, b, c[4],d;
    return 0;
}

//Type checking
int a, b[2];
int* point;

int main(){
    int a;
    //a = point;
    a = *point;
    a = point[0];
    *point = a;
    point = &a;
    return 0;
}

//Arithmetic Operations
int b = 4, a = 7;
int main(){
    int c = 4 + 7;
    int d = -(3*a/-2);
    return 0;
}



//Logical/Relations Operations
int a = 5;
int main(){
    int cond = !5;
    return 1 && 7 > a;
}

//Control structures
int main(){
    int a = 2;
    if (1){
        if(a){
        }
    }else {
        if(a){
        }
        while(a+1){
        }
    }
    return 0;
}

//Functions

//int fun(int num, int* point, int** point2);

int main(){
    int* point;
    fun(*point, point, &point);
    return 0;
}

int fun(int num, int* point, int** point2){
    return num;
}

// Printf and Scanf
int a = 10;
int main() {
    int result;
    printf("Hello Wordl!");
    printf("Tell me a number between %d and %d", 1, a);
    scanf("%d", &result);
    return 0;
}